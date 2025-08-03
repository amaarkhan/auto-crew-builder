import os
import subprocess
import time
import google.generativeai as genai
from dotenv import load_dotenv
import yaml

# Load environment variables from .env file (if exists)
load_dotenv()

def run_command_interactive(cmd_list):
    """Run a shell command interactively."""
    process = subprocess.Popen(cmd_list, stdin=None, stdout=None, stderr=None)
    process.communicate()

def run_command_output(cmd_list):
    """Run a shell command and get its output."""
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error running command: {' '.join(cmd_list)}\n{result.stderr}")
        exit(1)
    return result.stdout.strip()

def validate_yaml(yaml_text, fallback):
    """Ensure the YAML is valid; fallback to safe version if not."""
    try:
        data = yaml.safe_load(yaml_text)
        # Remove any tools sections from agents if present
        if isinstance(data, dict):
            for agent_name, agent_config in data.items():
                if isinstance(agent_config, dict) and 'tools' in agent_config:
                    del agent_config['tools']
        # Convert back to YAML string
        cleaned_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)
        return cleaned_yaml
    except yaml.YAMLError:
        print("⚠️ Invalid YAML generated. Using fallback.")
        return fallback

def generate_yaml_from_prompt(prompt, current_year):
    model = genai.GenerativeModel("gemini-1.5-flash")
    topic = prompt.strip()

    # Dynamic fallback generation if AI response is invalid
    def generate_dynamic_fallback():
        # Determine domain-specific components based on topic keywords
        domain_keywords = {
            'email': ('content_analyzer', 'email_composer', 'analyze_content_task', 'compose_email_task'),
            'research': ('researcher', 'analyst', 'research_task', 'analysis_task'),
            'development': ('developer', 'tester', 'development_task', 'testing_task'),
            'marketing': ('marketer', 'strategist', 'market_analysis_task', 'strategy_task'),
            'data': ('data_scientist', 'analyst', 'data_collection_task', 'data_analysis_task'),
            'content': ('content_creator', 'editor', 'content_creation_task', 'editing_task')
        }
        
        # Find matching domain or use generic
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

    # Single comprehensive prompt to generate both files with consistent agent names
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

    print("🤖 Generating both agents.yaml and tasks.yaml configurations...")
    response = model.generate_content(comprehensive_prompt)
    full_response = response.text.strip()
    
    # Remove markdown formatting if present
    if "```yaml" in full_response:
        full_response = full_response.split("```yaml")[1].split("```")[0].strip()
    elif "```" in full_response:
        full_response = full_response.split("```")[1].strip()

    # Split the response into agents and tasks
    try:
        parts = full_response.split("--- tasks.yaml ---")
        if len(parts) == 2:
            agents_yaml = parts[0].replace("--- agents.yaml ---", "").strip()
            tasks_yaml = parts[1].strip()
        else:
            # Fallback parsing
            agents_start = full_response.find("agent")
            tasks_start = full_response.find("task")
            if agents_start != -1 and tasks_start != -1 and agents_start < tasks_start:
                # Find the split point
                lines = full_response.split('\n')
                split_index = 0
                for i, line in enumerate(lines):
                    if line.strip().endswith(':') and 'task' in line.lower():
                        split_index = i
                        break
                
                agents_yaml = '\n'.join(lines[:split_index]).strip()
                tasks_yaml = '\n'.join(lines[split_index:]).strip()
            else:
                raise ValueError("Could not parse response")
    except:
        print("⚠️ Failed to parse AI response. Using fallback...")
        agents_yaml, tasks_yaml = generate_dynamic_fallback()

    # Validate YAML and use dynamic fallback if needed
    try:
        agents_data = yaml.safe_load(agents_yaml)
        tasks_data = yaml.safe_load(tasks_yaml)
        
        # Check if agent names in tasks match agents
        if agents_data and tasks_data:
            agent_names = set(agents_data.keys())
            task_agent_names = set()
            for task_config in tasks_data.values():
                if isinstance(task_config, dict) and 'agent' in task_config:
                    task_agent_names.add(task_config['agent'])
            
            if not task_agent_names.issubset(agent_names):
                print(f"⚠️ Agent name mismatch detected. Using fallback...")
                agents_yaml, tasks_yaml = generate_dynamic_fallback()
            else:
                print("✅ Generated valid YAML configurations with consistent agent names")
    except yaml.YAMLError as e:
        print(f"⚠️ Invalid YAML generated ({e}). Using dynamic fallback...")
        agents_yaml, tasks_yaml = generate_dynamic_fallback()

    # Clean up any tools sections
    agents_yaml = validate_yaml(agents_yaml, generate_dynamic_fallback()[0])
    tasks_yaml = validate_yaml(tasks_yaml, generate_dynamic_fallback()[1])

    return agents_yaml, tasks_yaml


def main():
    user_prompt = input("📝 What task should your Crew AI perform? (e.g. 'Market research on electric vehicles')\n> ")
    project_name = user_prompt.lower().replace(" ", "_").replace("-", "_")

    print("\n🔧 Installing CrewAI (if not already installed)...")
    run_command_output(["uv", "tool", "install", "crewai"])

    print(f"\n🚀 Creating CrewAI project: '{project_name}'...")
    run_command_interactive(["crewai", "create", "crew", project_name])

    print("⏳ Generating file structure...")
    time.sleep(3)

    # Load the Gemini API key
    project_env_path = os.path.join(project_name, ".env")
    if os.path.exists(project_env_path):
        load_dotenv(project_env_path)
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            print("✅ Loaded Gemini API key from .env")
        else:
            print("❌ GEMINI_API_KEY not found in .env")
            return
    else:
        print("❌ .env file not found in project directory")
        return

    config_dir = os.path.join(project_name, "src", project_name, "config")
    os.makedirs(config_dir, exist_ok=True)

    print("🤖 Generating 'agents.yaml' and 'tasks.yaml' using Gemini AI...")
    agents_yaml, tasks_yaml = generate_yaml_from_prompt(user_prompt, time.localtime().tm_year)

    agents_path = os.path.join(config_dir, "agents.yaml")
    tasks_path = os.path.join(config_dir, "tasks.yaml")

    with open(agents_path, "w", encoding="utf-8") as f:
        f.write(agents_yaml)
    with open(tasks_path, "w", encoding="utf-8") as f:
        f.write(tasks_yaml)

    print(f"\n✅ Project '{project_name}' setup complete!")
    print(f"📄 All files generated and updated:")
    print(f"   - {agents_path}")
    print(f"   - {tasks_path}")

if __name__ == "__main__":
    main()
