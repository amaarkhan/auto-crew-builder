from flask import Flask, render_template, request, jsonify, send_file
import os
import subprocess
import time
import tempfile
import shutil
import zipfile
import google.generativeai as genai
from dotenv import load_dotenv
import yaml
import threading
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Global variable to store generation status
generation_status = {}

# AI Models configuration
AI_MODELS = {
    'gemini': {
        'name': 'Google Gemini',
        'models': [
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-1.0-pro'
        ],
        'api_key_env': 'GEMINI_API_KEY'
    },
    'openai': {
        'name': 'OpenAI GPT',
        'models': [
            'gpt-4',
            'gpt-4-turbo',
            'gpt-3.5-turbo'
        ],
        'api_key_env': 'OPENAI_API_KEY'
    },
    'anthropic': {
        'name': 'Anthropic Claude',
        'models': [
            'claude-3-opus',
            'claude-3-sonnet',
            'claude-3-haiku'
        ],
        'api_key_env': 'ANTHROPIC_API_KEY'
    }
}

def run_command_output(cmd_list):
    """Run a shell command and get its output."""
    result = subprocess.run(cmd_list, capture_output=True, text=True, shell=True, timeout=300)
    if result.returncode != 0:
        raise Exception(f"Error running command: {' '.join(cmd_list)}\n{result.stderr}")
    return result.stdout.strip()

def run_command_interactive(cmd_list):
    """Run a shell command interactively with timeout."""
    try:
        process = subprocess.Popen(cmd_list, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        stdout, stderr = process.communicate(timeout=300)
        if process.returncode != 0 and stderr:
            raise Exception(f"Command failed: {stderr}")
        return stdout
    except subprocess.TimeoutExpired:
        process.kill()
        raise Exception("Command timed out after 5 minutes")

def validate_yaml(yaml_text, fallback):
    """Ensure the YAML is valid; fallback to safe version if not."""
    try:
        data = yaml.safe_load(yaml_text)
        if isinstance(data, dict):
            for agent_name, agent_config in data.items():
                if isinstance(agent_config, dict) and 'tools' in agent_config:
                    del agent_config['tools']
        cleaned_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)
        return cleaned_yaml
    except yaml.YAMLError:
        return fallback

def generate_yaml_from_prompt(prompt, current_year, ai_provider='gemini', model_name='gemini-1.5-flash'):
    """Generate YAML configurations using specified AI provider and model."""
    
    topic = prompt.strip()
    
    def generate_dynamic_fallback():
        domain_keywords = {
            'email': ('content_analyzer', 'email_composer', 'analyze_content_task', 'compose_email_task'),
            'research': ('researcher', 'analyst', 'research_task', 'analysis_task'),
            'development': ('developer', 'tester', 'development_task', 'testing_task'),
            'marketing': ('marketer', 'strategist', 'market_analysis_task', 'strategy_task'),
            'data': ('data_scientist', 'analyst', 'data_collection_task', 'data_analysis_task'),
            'content': ('content_creator', 'editor', 'content_creation_task', 'editing_task')
        }
        
        agent1_name, agent2_name, task1_name, task2_name = 'content_analyzer', 'email_composer', 'analyze_content_task', 'compose_email_task'
        
        for keyword, names in domain_keywords.items():
            if keyword in topic.lower():
                agent1_name, agent2_name, task1_name, task2_name = names
                break
        
        fallback_agents = f"""{agent1_name}:
  role: >
    {topic} Content Analyzer
  goal: >
    Analyze and extract key information from provided content related to {topic}
  backstory: >
    You are a skilled content analyst specializing in {topic}. Your expertise allows you to 
    quickly identify important details, context, and requirements from various types of content
    to facilitate effective communication and deliverable creation.
  verbose: true
  allow_delegation: true

{agent2_name}:
  role: >
    {topic} Content Creator
  goal: >
    Create professional, well-structured content based on analyzed information for {topic}
  backstory: >
    You are an expert content creator with extensive experience in {topic}. You excel at 
    transforming analyzed information into polished, professional deliverables that meet 
    specific requirements and maintain high quality standards.
  verbose: true
  allow_delegation: false"""

        fallback_tasks = f"""{task1_name}:
  description: >
    Analyze the provided topic: "{{topic}}" and all user-provided information.
    Extract and understand ALL available inputs including any of these common variables:
    {{recipient_name}}, {{subject}}, {{sender_name}}, {{additional_context}}, 
    {{project_details}}, {{requirements}}, {{target_audience}}, {{research_scope}},
    {{product_service}}, {{content_type}}, {{key_points}}, or any other user inputs.
    
    Identify the purpose, requirements, and approach needed for creating the deliverable.
    Pay special attention to personalization details provided by the user.
    Current year: {{current_year}}
  expected_output: >
    A comprehensive analysis that identifies all user-provided information and creates
    a clear plan for using this information in the final deliverable. Must include
    specific recommendations for incorporating user inputs into the output.
  agent: {agent1_name}

{task2_name}:
  description: >
    Create the final deliverable for "{{topic}}" using the analysis from the previous task.
    
    CRITICAL: Use ALL available user-provided information from inputs. This may include:
    - {{recipient_name}} (use as recipient/addressee)
    - {{subject}} (use as subject line/title)  
    - {{sender_name}} (use as sender/author)
    - {{additional_context}} (incorporate into main content)
    - {{project_details}} (use for project specifications)
    - {{requirements}} (ensure all requirements are met)
    - {{target_audience}} (tailor content appropriately)
    - {{research_scope}} (focus research accordingly)
    - {{product_service}} (feature in content)
    - {{content_type}} (format output correctly)
    - {{key_points}} (include these points)
    - Any other user inputs provided
    
    The output MUST be personalized with the actual user data, not generic examples.
    Current year: {{current_year}}
  expected_output: >
    A complete, professional deliverable that incorporates ALL user-provided information.
    The output must be personalized with actual user inputs (names, subjects, context, etc.)
    and ready for immediate use. No generic placeholders or example content allowed.
  agent: {agent2_name}"""
        
        return fallback_agents, fallback_tasks
    
    # For now, we'll use Gemini for all providers as the base implementation
    # This can be extended to support other providers in the future
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Warning: GEMINI_API_KEY not found, using fallback generation")
        return generate_dynamic_fallback()
    
    try:
        # Import genai only when needed to speed up startup
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Use the selected model if it's a Gemini model, otherwise fallback to flash
        if ai_provider == 'gemini' and model_name.startswith('gemini'):
            model = genai.GenerativeModel(model_name)
        else:
            model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Failed to configure AI model: {str(e)}, using fallback")
        return generate_dynamic_fallback()
    
    topic = prompt.strip()

    def generate_dynamic_fallback():
        domain_keywords = {
            'email': ('content_analyzer', 'email_composer', 'analyze_content_task', 'compose_email_task'),
            'research': ('researcher', 'analyst', 'research_task', 'analysis_task'),
            'development': ('developer', 'tester', 'development_task', 'testing_task'),
            'marketing': ('marketer', 'strategist', 'market_analysis_task', 'strategy_task'),
            'data': ('data_scientist', 'analyst', 'data_collection_task', 'data_analysis_task'),
            'content': ('content_creator', 'editor', 'content_creation_task', 'editing_task')
        }
        
        agent1_name, agent2_name, task1_name, task2_name = 'content_analyzer', 'email_composer', 'analyze_content_task', 'compose_email_task'
        
        for keyword, names in domain_keywords.items():
            if keyword in topic.lower():
                agent1_name, agent2_name, task1_name, task2_name = names
                break
        
        fallback_agents = f"""{agent1_name}:
  role: >
    {topic} Content Analyzer
  goal: >
    Analyze and extract key information from provided content related to {topic}
  backstory: >
    You are a skilled content analyst specializing in {topic}. Your expertise allows you to 
    quickly identify important details, context, and requirements from various types of content
    to facilitate effective communication and deliverable creation.
  verbose: true
  allow_delegation: true

{agent2_name}:
  role: >
    {topic} Content Creator
  goal: >
    Create professional, well-structured content based on analyzed information for {topic}
  backstory: >
    You are an expert content creator with extensive experience in {topic}. You excel at 
    transforming analyzed information into polished, professional deliverables that meet 
    specific requirements and maintain high quality standards.
  verbose: true
  allow_delegation: false"""

        fallback_tasks = f"""{task1_name}:
  description: >
    Analyze the provided topic: "{{topic}}" and all user-provided information.
    Extract and understand ALL available inputs including any of these common variables:
    {{recipient_name}}, {{subject}}, {{sender_name}}, {{additional_context}}, 
    {{project_details}}, {{requirements}}, {{target_audience}}, {{research_scope}},
    {{product_service}}, {{content_type}}, {{key_points}}, or any other user inputs.
    
    Identify the purpose, requirements, and approach needed for creating the deliverable.
    Pay special attention to personalization details provided by the user.
    Current year: {{current_year}}
  expected_output: >
    A comprehensive analysis that identifies all user-provided information and creates
    a clear plan for using this information in the final deliverable. Must include
    specific recommendations for incorporating user inputs into the output.
  agent: {agent1_name}

{task2_name}:
  description: >
    Create the final deliverable for "{{topic}}" using the analysis from the previous task.
    
    CRITICAL: Use ALL available user-provided information from inputs. This may include:
    - {{recipient_name}} (use as recipient/addressee)
    - {{subject}} (use as subject line/title)  
    - {{sender_name}} (use as sender/author)
    - {{additional_context}} (incorporate into main content)
    - {{project_details}} (use for project specifications)
    - {{requirements}} (ensure all requirements are met)
    - {{target_audience}} (tailor content appropriately)
    - {{research_scope}} (focus research accordingly)
    - {{product_service}} (feature in content)
    - {{content_type}} (format output correctly)
    - {{key_points}} (include these points)
    - Any other user inputs provided
    
    The output MUST be personalized with the actual user data, not generic examples.
    Current year: {{current_year}}
  expected_output: >
    A complete, professional deliverable that incorporates ALL user-provided information.
    The output must be personalized with actual user inputs (names, subjects, context, etc.)
    and ready for immediate use. No generic placeholders or example content allowed.
  agent: {agent2_name}"""
        
        return fallback_agents, fallback_tasks

    comprehensive_prompt = f"""
You are an expert CrewAI configuration generator. Create both agents.yaml and tasks.yaml files for the project: "{topic}"

REQUIREMENTS:
1. Generate 2 agents with consistent naming between files
2. Agent names should be descriptive and topic-specific (snake_case)
3. Generate 2 tasks that use these exact agent names
4. Tasks should build upon each other sequentially
5. DO NOT include tools in agents - tools are handled separately
6. Tasks should use user-provided information from inputs, not just the topic

GENERATE BOTH FILES WITH CONSISTENT AGENT NAMES:

--- agents.yaml ---
agent_name_1:
  role: >
    [Specific role for {topic}]
  goal: >
    [Measurable goal related to {topic}]
  backstory: >
    [Detailed backstory showing expertise in {topic}]
  verbose: true
  allow_delegation: true

agent_name_2:
  role: >
    [Different specific role for {topic}]
  goal: >
    [Different measurable goal for {topic}]
  backstory: >
    [Different expertise backstory for {topic}]
  verbose: true
  allow_delegation: false

--- tasks.yaml ---
task_name_1:
  description: >
    Analyze the topic "{topic}" and all user-provided information.
    Extract and understand ALL available inputs including any variables like:
    {{recipient_name}}, {{subject}}, {{sender_name}}, {{additional_context}}, 
    {{project_details}}, {{requirements}}, {{target_audience}}, or any other user inputs.
    
    Create a comprehensive plan for using this information in the final deliverable.
    Current year: {{current_year}}
  expected_output: >
    A detailed analysis that identifies all user inputs and creates a plan for
    incorporating them into the final deliverable. No generic content allowed.
  agent: agent_name_1

task_name_2:
  description: >
    Create the final deliverable for "{topic}" using ALL user-provided information.
    
    MANDATORY: Use actual user inputs from variables like {{recipient_name}}, {{subject}}, 
    {{sender_name}}, {{additional_context}}, {{project_details}}, {{requirements}}, 
    {{target_audience}}, or any other provided inputs.
    
    The output MUST be personalized with real user data, not examples or placeholders.
    Current year: {{current_year}}
  expected_output: >
    A complete deliverable that uses ALL user-provided information with actual names,
    subjects, context, and details. Must be personalized and ready for immediate use.
  agent: agent_name_2

IMPORTANT: Use the EXACT SAME agent names in both files. Use descriptive names like 'content_analyzer' and 'content_creator'.
CRITICAL: Tasks MUST use ALL available template variables from user inputs. Include variables like {{recipient_name}}, {{subject}}, {{sender_name}}, {{additional_context}}, {{project_details}}, {{requirements}}, {{target_audience}} etc.
CRITICAL: Tasks MUST incorporate actual user-provided information and produce personalized outputs, not generic examples.
CRITICAL: The final deliverable MUST use real user data (names, subjects, context) provided in the inputs dictionary.

Current year: {current_year}
Topic: "{topic}"
"""

    try:
        response = model.generate_content(comprehensive_prompt)
        full_response = response.text.strip()
        
        # Remove markdown formatting if present
        if "```yaml" in full_response:
            full_response = full_response.split("```yaml")[1].split("```")[0].strip()
        elif "```" in full_response:
            full_response = full_response.split("```")[1].strip()

        # Split the response into agents and tasks
        parts = full_response.split("--- tasks.yaml ---")
        if len(parts) == 2:
            agents_yaml = parts[0].replace("--- agents.yaml ---", "").strip()
            tasks_yaml = parts[1].strip()
        else:
            agents_yaml, tasks_yaml = generate_dynamic_fallback()

        # Validate YAML
        try:
            agents_data = yaml.safe_load(agents_yaml)
            tasks_data = yaml.safe_load(tasks_yaml)
            
            if agents_data and tasks_data:
                agent_names = set(agents_data.keys())
                task_agent_names = set()
                for task_config in tasks_data.values():
                    if isinstance(task_config, dict) and 'agent' in task_config:
                        task_agent_names.add(task_config['agent'])
                
                if not task_agent_names.issubset(agent_names):
                    agents_yaml, tasks_yaml = generate_dynamic_fallback()
        except yaml.YAMLError:
            agents_yaml, tasks_yaml = generate_dynamic_fallback()

        # Clean up any tools sections
        agents_yaml = validate_yaml(agents_yaml, generate_dynamic_fallback()[0])
        tasks_yaml = validate_yaml(tasks_yaml, generate_dynamic_fallback()[1])

        return agents_yaml, tasks_yaml
    
    except Exception as e:
        print(f"Error generating YAML: {e}")
        return generate_dynamic_fallback()

def generate_project_async(session_id, prompt, ai_provider, model_name):
    """Generate CrewAI project asynchronously."""
    try:
        generation_status[session_id] = {
            'status': 'starting',
            'message': 'Initializing project generation...',
            'progress': 5
        }
        
        project_name = prompt.lower().replace(" ", "_").replace("-", "_")
        
        # Create temporary directory for this session
        temp_dir = tempfile.mkdtemp(prefix=f"crewai_{session_id}_")
        project_path = os.path.join(temp_dir, project_name)
        
        generation_status[session_id] = {
            'status': 'creating_structure',
            'message': 'Creating complete project structure...',
            'progress': 15
        }
        
        # Create complete project structure
        src_dir = os.path.join(project_path, "src", project_name)
        config_dir = os.path.join(src_dir, "config")
        tools_dir = os.path.join(src_dir, "tools")
        tests_dir = os.path.join(project_path, "tests")
        knowledge_dir = os.path.join(project_path, "knowledge")
        
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(tools_dir, exist_ok=True)
        os.makedirs(tests_dir, exist_ok=True)
        os.makedirs(knowledge_dir, exist_ok=True)
        
        generation_status[session_id] = {
            'status': 'creating_config',
            'message': 'Creating project configuration...',
            'progress': 25
        }
        
        # Create pyproject.toml
        pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "{project_name} using crewAI"
authors = [{{ name = "Your Name", email = "you@example.com" }}]
requires-python = ">=3.10,<3.14"
dependencies = [
    "crewai[tools]>=0.140.0,<1.0.0"
]

[project.scripts]
{project_name} = "{project_name}.main:run"
run_crew = "{project_name}.main:run"
train = "{project_name}.main:train"
replay = "{project_name}.main:replay"
test = "{project_name}.main:test"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.crewai]
type = "crew"
'''
        
        with open(os.path.join(project_path, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write(pyproject_content)
        
        # Create README.md
        readme_content = f'''# {project_name.replace('_', ' ').title()} Crew

Welcome to the {project_name.replace('_', ' ').title()} Crew project, powered by [crewAI](https://crewai.com). This template is designed to help you set up a multi-agent AI system with ease, leveraging the powerful and flexible framework provided by crewAI. Our goal is to enable your agents to collaborate effectively on complex tasks, maximizing their collective intelligence and capabilities.

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:

```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```

### Customizing

**Add your `OPENAI_API_KEY` into the `.env` file**

- Modify `src/{project_name}/config/agents.yaml` to define your agents
- Modify `src/{project_name}/config/tasks.yaml` to define your tasks
- Modify `src/{project_name}/crew.py` to add your own logic, tools and specific args
- Modify `src/{project_name}/main.py` to add custom inputs for your agents and tasks

## Running the Project

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

```bash
$ crewai run
```

This command initializes the {project_name} Crew, assembling the agents and assigning them tasks as defined in your configuration.

This example, unmodified, will run the create a `report.md` file with the output of a research on LLMs in the root folder.

## Understanding Your Crew

The {project_name} Crew is composed of multiple AI agents, each with unique roles, goals, and tools. These agents collaborate on a series of tasks, defined in `config/tasks.yaml`, leveraging their collective skills to achieve complex objectives. The `config/agents.yaml` file outlines the capabilities and configurations of each agent in your crew.

## Support

For support, questions, or feedback regarding the {project_name.replace('_', ' ').title()} Crew or crewAI.
- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
'''
        
        with open(os.path.join(project_path, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        # Create .env file
        with open(os.path.join(project_path, ".env"), "w", encoding="utf-8") as f:
            f.write("# Add your API keys here\nOPENAI_API_KEY=your_api_key_here\nGEMINI_API_KEY=your_api_key_here\nANTHROPIC_API_KEY=your_api_key_here\n")
        
        generation_status[session_id] = {
            'status': 'creating_crew',
            'message': 'Creating crew class...',
            'progress': 35
        }
        
        # Create crew.py file (modern CrewAI format)
        crew_py_content = f'''from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class {project_name.replace('_', ' ').title().replace(' ', '')}():
    """{project_name.replace('_', ' ').title()} crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'], # type: ignore[index]
            verbose=True
        )

    @agent
    def reporting_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['reporting_analyst'], # type: ignore[index]
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'], # type: ignore[index]
        )

    @task
    def reporting_task(self) -> Task:
        return Task(
            config=self.tasks_config['reporting_task'], # type: ignore[index]
            output_file='report.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the {project_name.replace('_', ' ').title()} crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
'''
        
        with open(os.path.join(src_dir, "crew.py"), "w", encoding="utf-8") as f:
            f.write(crew_py_content)
        
        generation_status[session_id] = {
            'status': 'creating_main',
            'message': 'Creating main execution file...',
            'progress': 45
        }
        
        # Create main.py file (modern CrewAI format)
        main_py_content = f'''#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from {project_name}.crew import {project_name.replace('_', ' ').title().replace(' ', '')}

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    """
    Run the crew.
    """
    inputs = {{
        'topic': '{prompt}',
        'current_year': str(datetime.now().year)
    }}
    
    try:
        {project_name.replace('_', ' ').title().replace(' ', '')}().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {{e}}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {{
        "topic": "{prompt}",
        'current_year': str(datetime.now().year)
    }}
    try:
        {project_name.replace('_', ' ').title().replace(' ', '')}().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {{e}}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        {project_name.replace('_', ' ').title().replace(' ', '')}().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {{e}}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {{
        "topic": "{prompt}",
        "current_year": str(datetime.now().year)
    }}
    
    try:
        {project_name.replace('_', ' ').title().replace(' ', '')}().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {{e}}")
'''
        
        with open(os.path.join(src_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(main_py_content)
        
        generation_status[session_id] = {
            'status': 'creating_tools',
            'message': 'Creating tools and utilities...',
            'progress': 55
        }
        
        # Create custom_tool.py
        custom_tool_content = '''from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class MyCustomToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    argument: str = Field(..., description="Description of the argument.")

class MyCustomTool(BaseTool):
    name: str = "Name of my tool"
    description: str = (
        "Clear description for what this tool is useful for, your agent will need this information to use it."
    )
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, argument: str) -> str:
        # Implementation goes here
        return "this is an example of a tool output, ignore it and move along."
'''
        
        # Create __init__.py files for Python packages
        with open(os.path.join(src_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("")
        
        with open(os.path.join(config_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("")
            
        with open(os.path.join(tools_dir, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("")
        
        generation_status[session_id] = {
            'status': 'generating_ai',
            'message': 'Generating AI configurations...',
            'progress': 65
        }
        
        # Generate YAML files using AI
        agents_yaml, tasks_yaml = generate_yaml_from_prompt(prompt, time.localtime().tm_year, ai_provider, model_name)
        
        generation_status[session_id] = {
            'status': 'writing_config',
            'message': 'Writing configuration files...',
            'progress': 75
        }
        
        # Write YAML files
        agents_path = os.path.join(config_dir, "agents.yaml")
        tasks_path = os.path.join(config_dir, "tasks.yaml")
        
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write(agents_yaml)
        with open(tasks_path, "w", encoding="utf-8") as f:
            f.write(tasks_yaml)
        
        generation_status[session_id] = {
            'status': 'finalizing',
            'message': 'Creating additional project files...',
            'progress': 85
        }
        
        # Create .gitignore
        gitignore_content = """__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.env
.venv/
pip-log.txt
pip-delete-this-directory.txt
.DS_Store
*.log
dist/
build/
*.egg-info/
"""
        
        with open(os.path.join(project_path, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(gitignore_content)
        
        generation_status[session_id] = {
            'status': 'zipping',
            'message': 'Creating download package...',
            'progress': 95
        }
        
        # Create ZIP file
        zip_path = os.path.join(temp_dir, f"{project_name}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arc_name)
        
        generation_status[session_id] = {
            'status': 'completed',
            'message': 'Project generation completed!',
            'progress': 100,
            'zip_path': zip_path,
            'project_name': project_name
        }
        
    except Exception as e:
        generation_status[session_id] = {
            'status': 'error',
            'message': f'Error: {str(e)}',
            'progress': 0
        }

@app.route('/')
def index():
    return render_template('index.html', ai_models=AI_MODELS)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    ai_provider = data.get('ai_provider', 'gemini')
    model_name = data.get('model_name', 'gemini-1.5-flash')
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    # Generate unique session ID
    import uuid
    session_id = str(uuid.uuid4())
    
    # Start generation in background thread
    thread = threading.Thread(
        target=generate_project_async,
        args=(session_id, prompt, ai_provider, model_name)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'session_id': session_id})

@app.route('/status/<session_id>')
def get_status(session_id):
    status = generation_status.get(session_id, {'status': 'not_found', 'message': 'Session not found'})
    return jsonify(status)

@app.route('/download/<session_id>')
def download(session_id):
    status = generation_status.get(session_id, {})
    
    if status.get('status') != 'completed':
        return jsonify({'error': 'Project not ready for download'}), 400
    
    zip_path = status.get('zip_path')
    project_name = status.get('project_name', 'crewai_project')
    
    if not zip_path or not os.path.exists(zip_path):
        return jsonify({'error': 'Download file not found'}), 404
    
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f"{project_name}.zip",
        mimetype='application/zip'
    )

@app.route('/api/models/<provider>')
def get_models(provider):
    """Get available models for a specific AI provider."""
    if provider in AI_MODELS:
        return jsonify(AI_MODELS[provider]['models'])
    return jsonify([])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
