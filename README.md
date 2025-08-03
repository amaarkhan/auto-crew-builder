# CrewAI Project Generator

A modern web-based tool for generating complete CrewAI projects with intelligent multi-agent configurations. This application provides both a beautiful Flask web interface and a command-line interface for creating production-ready CrewAI projects.

## 🌟 Features

### Web Interface (`app.py`)

<img width="1904" height="910" alt="Screenshot 2025-08-03 132414" src="https://github.com/user-attachments/assets/5d016882-c0b9-4ffa-b437-c73414c56f1e" />

<img width="1870" height="881" alt="Screenshot 2025-08-03 132409" src="https://github.com/user-attachments/assets/8f888ad9-b336-4a8d-ab29-a06377470263" />


- **Beautiful Modern UI** - Responsive web interface with gradient backgrounds and glassmorphism design
- **Multiple AI Providers** - Support for Google Gemini, OpenAI GPT, and Anthropic Claude models
- **Real-time Progress Tracking** - Live updates during project generation with progress bars
- **One-Click Download** - Generate and download complete CrewAI projects as ZIP files
- **AI Model Selection** - Choose from different AI models for YAML configuration generation
- **Session Management** - Handle multiple concurrent project generations

### Command Line Interface (`q1.py`)
- **Fast CLI Generation** - Quick project setup from terminal
- **Direct CrewAI Integration** - Uses official CrewAI commands for project scaffolding
- **Smart Fallbacks** - Intelligent domain-specific fallbacks when AI generation fails
- **YAML Validation** - Ensures generated configurations are valid

### Generated Project Features
- **Complete Project Structure** - Full CrewAI project with proper directory layout
- **Modern CrewAI Format** - Uses latest CrewAI decorators and project structure
- **Custom Tools Support** - Includes custom tool templates
- **Testing Framework** - Built-in test structure and commands
- **Package Management** - Complete pyproject.toml with dependencies
- **Environment Setup** - Pre-configured .env files for API keys

## 🛠️ Installation

### Prerequisites
- Python 3.10+ (required for CrewAI compatibility)
- `uv` package manager (recommended) or `pip`

### Dependencies Installation
```bash
pip install flask python-dotenv google-generativeai pyyaml
```

### API Keys Setup
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## 🚀 Usage

### Web Interface
1. Start the Flask application:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. Fill out the form:
   - **Task Description**: Describe what you want your CrewAI to accomplish
   - **AI Provider**: Choose between Gemini, OpenAI, or Anthropic
   - **Model Selection**: Pick specific model variant
   - **Generate**: Click to start project generation

4. **Download**: Once complete, download your ready-to-use CrewAI project

### Command Line Interface
```bash
python q1.py
```
Follow the interactive prompts to generate your project directly.

## 📁 Generated Project Structure

```
your_project_name/
├── README.md                          # Project documentation
├── pyproject.toml                     # Project configuration & dependencies
├── .env                              # Environment variables (API keys)
├── .gitignore                        # Git ignore patterns
├── src/
│   └── your_project_name/
│       ├── __init__.py
│       ├── main.py                   # Entry point with run/train/test commands
│       ├── crew.py                   # Main crew class with agents & tasks
│       ├── config/
│       │   ├── __init__.py
│       │   ├── agents.yaml           # AI-generated agent configurations
│       │   └── tasks.yaml            # AI-generated task definitions
│       └── tools/
│           ├── __init__.py
│           └── custom_tool.py        # Custom tool template
├── tests/                            # Test directory
├── knowledge/                        # Knowledge base directory
└── report.md                         # Generated output file
```

## ⚙️ Configuration

### AI Models Supported

#### Google Gemini
- `gemini-1.5-flash` (Default - Fast and efficient)
- `gemini-1.5-pro` (Advanced reasoning)
- `gemini-1.0-pro` (Stable version)

#### OpenAI GPT
- `gpt-4` (Most capable)
- `gpt-4-turbo` (Faster GPT-4)
- `gpt-3.5-turbo` (Cost-effective)

#### Anthropic Claude
- `claude-3-opus` (Most intelligent)
- `claude-3-sonnet` (Balanced performance)
- `claude-3-haiku` (Fastest)

### Project Templates

The generator intelligently creates domain-specific agents and tasks based on your prompt:

- **Email/Communication**: Content analyzer + Email composer
- **Research**: Researcher + Analyst
- **Development**: Developer + Tester
- **Marketing**: Marketer + Strategist
- **Data Science**: Data scientist + Analyst
- **Content Creation**: Content creator + Editor

## 🔧 Running Generated Projects

### Setup
```bash
cd your_project_name
pip install uv
crewai install
```

### Add API Keys
Edit the `.env` file and add your API keys:
```env
OPENAI_API_KEY=your_actual_api_key
GEMINI_API_KEY=your_actual_api_key
```

### Run Commands
```bash
# Run the crew
crewai run

# Train the crew
crewai train 5 training_results.json

# Replay specific task
crewai replay task_id

# Test the crew
crewai test 3 gpt-4
```

## 🧩 Key Components

### Backend (`app.py`)
- **Flask Web Framework**: Serves the web interface
- **Asynchronous Generation**: Non-blocking project creation
- **Session Management**: Handles multiple concurrent generations
- **ZIP File Creation**: Packages complete projects for download
- **AI Integration**: Connects with multiple AI providers

### Frontend (`templates/index.html`)
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Updates**: Live progress tracking via AJAX
- **Modern UI/UX**: Gradient backgrounds, glassmorphism effects
- **Interactive Elements**: Dynamic AI provider and model selection

### CLI Tool (`q1.py`)
- **Direct CrewAI Integration**: Uses official CrewAI scaffolding
- **Smart Fallbacks**: Domain-specific templates when AI fails
- **YAML Validation**: Ensures configuration correctness
- **Fast Generation**: Optimized for quick project setup

## 🎯 Use Cases

### Business Applications
- **Market Research**: Generate crews for competitive analysis
- **Content Marketing**: Create content generation and optimization teams
- **Customer Support**: Build automated support and FAQ systems
- **Data Analysis**: Set up data processing and reporting crews

### Development Projects
- **Code Review**: Automated code analysis and improvement suggestions
- **Documentation**: Generate and maintain project documentation
- **Testing**: Create comprehensive testing and QA workflows
- **DevOps**: Automate deployment and monitoring processes

### Creative Projects
- **Writing Teams**: Collaborative content creation workflows
- **Design Process**: Multi-agent design review and iteration
- **Social Media**: Automated content creation and scheduling
- **Research**: Academic and professional research workflows

## 🔍 Troubleshooting

### Common Issues

#### Generation Timeout
- **Symptom**: Project generation takes too long
- **Solution**: Use simpler, more specific prompts; check internet connection

#### Missing Files in Downloaded ZIP
- **Symptom**: Generated project missing some standard CrewAI files
- **Solution**: The web interface creates a simplified structure; use CLI for full CrewAI scaffolding

#### API Key Errors
- **Symptom**: "API key not found" or authentication errors
- **Solution**: Verify API keys are correctly set in `.env` file

#### Invalid YAML Generated
- **Symptom**: Project fails to run due to configuration errors
- **Solution**: The system automatically falls back to working templates

### Performance Tips
- Use Gemini Flash model for fastest generation
- Keep prompts concise but descriptive
- Ensure stable internet connection for AI API calls

## 🔄 Differences: Web vs CLI

| Feature | Web Interface | CLI Tool |
|---------|---------------|----------|
| **Project Structure** | Simplified, custom structure | Full CrewAI scaffolding |
| **Speed** | Slower (complete rebuild) | Faster (uses CrewAI CLI) |
| **UI/UX** | Beautiful web interface | Terminal-based |
| **AI Options** | Multiple providers/models | Gemini only |
| **Download** | ZIP file | Direct folder creation |
| **Concurrent Use** | Multiple sessions | Single session |
| **Dependencies** | Manual creation | Official CrewAI structure |

## 📈 Future Enhancements

- [ ] Support for more AI providers (Cohere, Mistral)
- [ ] Custom tool integration during generation
- [ ] Project templates library
- [ ] Git repository initialization
- [ ] Docker containerization support
- [ ] Advanced configuration options
- [ ] Project sharing and collaboration features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source. Feel free to use, modify, and distribute as needed.

## 🆘 Support

For issues, questions, or feature requests:
1. Check the troubleshooting section above
2. Review CrewAI documentation: https://docs.crewai.com
3. Create an issue in the project repository

## 🔗 Related Links

- [CrewAI Official Documentation](https://docs.crewai.com)
- [CrewAI GitHub Repository](https://github.com/joaomdmoura/crewai)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Google Gemini API](https://ai.google.dev/)
- [OpenAI API](https://platform.openai.com/docs)
- [Anthropic Claude API](https://docs.anthropic.com/)
