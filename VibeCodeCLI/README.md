# AI Coding Agent - Development Guide

## Project Structure for AI Development

This project is structured to support scalable AI development with modular
features, comprehensive monitoring, and robust configuration management.

### Architecture Overview

```
ai-coding-agent/
├── core/                    # Core agent functionality
├── ui/                      # User interface components  
├── features/                # Modular AI features
├── config/                  # Configuration management
├── scripts/                 # Development utilities
├── tests/                   # Test suite
└── docs/                    # Documentation
```

## Getting Started

### 1. Development Setup

Run the development setup script:

```bash
python scripts/setup_dev.py
```

This will:

- Create the project structure
- Set up virtual environment
- Install dependencies
- Create configuration files
- Set up pre-commit hooks

### 2. Configuration

1. Copy `.env.example` to `.env`
2. Add your API keys:
   ```
   LLM_API_KEY=your_api_key_here
   OPENAI_API_KEY=your_openai_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

### 3. Running the Application

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Run the textual agent
python ui/textual_agent.py
```

## Feature Development

### Creating a New Feature

1. Create a new file in `features/your_feature/`
2. Inherit from `BaseFeature`:

```python
from features import BaseFeature

class YourFeature(BaseFeature):
    def __init__(self):
        super().__init__("your_feature", "1.0.0")
    
    async def initialize(self, agent_context):
        # Initialize your feature
        return True
    
    async def execute(self, request):
        # Feature implementation
        return {"result": "success"}
    
    def get_capabilities(self):
        return ["capability1", "capability2"]
```

3. Register the feature:

```python
from features import feature_manager
from your_feature import YourFeature

feature_manager.register_feature(YourFeature())
```

### Available Features

#### Code Analysis Feature

- **Location**: `features/code_analysis/`
- **Capabilities**:
  - Dependency analysis
  - Complexity metrics
  - Security scanning
  - Code quality assessment

**Usage**:

```python
result = await feature_manager.execute_feature("code_analysis", {
    "type": "all",  # or "dependencies", "complexity", "security", "quality"
    "files": project_files,
    "project_path": "/path/to/project"
})
```

## Configuration Management

The `config` module provides centralized configuration:

```python
from config import config_manager

# Get model configuration
model_config = config_manager.get_model_config("gpt-4")

# Get application settings
max_attempts = config_manager.get_setting("agent.max_attempts", 5)

# Get API key
api_key = config_manager.get_api_key("openai")
```

### Configuration Files

- `config/models.yaml` - LLM model configurations
- `config/features.yaml` - Feature settings
- `config/settings.yaml` - Application settings
- `config/prompts/` - Prompt templates

## Testing

Run tests with:

```bash
python scripts/run_tests.py
```

Or directly with pytest:

```bash
pytest tests/
```

## AI Development Workflow

### 1. Feature-Driven Development

Each AI capability should be implemented as a separate feature:

- **Code Generation**: Template-based code generation
- **Code Analysis**: Static analysis and metrics
- **Refactoring**: Automated code improvements
- **Testing**: Test generation and execution
- **Documentation**: Auto-documentation generation

### 2. Prompt Engineering

Store prompts in `config/prompts/`:

```yaml
# config/prompts/code_generation.yaml
prompts:
    python_function:
        system: "You are a Python code generator..."
        user: "Generate a Python function that {description}"

    javascript_component:
        system: "You are a React component generator..."
        user: "Create a React component for {component_type}"
```

### 3. Model Management

Configure multiple models in `config/models.yaml`:

```yaml
models:
    - name: gpt-4
      provider: openai
      model_id: gpt-4
      max_tokens: 4096
      cost_per_1k_input: 0.03
      cost_per_1k_output: 0.06

    - name: claude-3-haiku
      provider: anthropic
      model_id: claude-3-haiku-20240307
      max_tokens: 4096
      cost_per_1k_input: 0.00025
      cost_per_1k_output: 0.00125
```

### 4. Monitoring and Analytics

The monitoring system tracks:

- API usage and costs
- Feature performance
- User interactions
- Error rates

Access monitoring data:

```python
from core.monitoring import MasterMonitoring

monitor = MasterMonitoring()
metrics = monitor.get_session_summary()
```

## Advanced Features

### 1. Project Templates

Create reusable project templates in `features/project_templates/`:

```python
class WebAppTemplate(BaseFeature):
    def get_template_files(self):
        return {
            "app.py": "# Flask web application...",
            "requirements.txt": "flask>=2.0.0...",
            "static/style.css": "/* CSS styles */",
            "templates/index.html": "<!-- HTML template -->"
        }
```

### 2. External Integrations

Integrate with external tools in `features/integrations/`:

- Git operations
- Docker containerization
- CI/CD pipelines
- Cloud deployments

### 3. Code Quality Tools

Automated integration with:

- **flake8** - Style checking
- **bandit** - Security analysis
- **mypy** - Type checking
- **black** - Code formatting

## Best Practices

### 1. Feature Design

- Keep features focused and single-purpose
- Use dependency injection for configuration
- Implement proper error handling
- Include comprehensive tests

### 2. Configuration Management

- Use environment variables for secrets
- Store settings in YAML files
- Provide sensible defaults
- Document all configuration options

### 3. Monitoring

- Track all LLM API calls
- Monitor feature usage
- Log errors and performance metrics
- Generate regular reports

### 4. Testing

- Write unit tests for all features
- Include integration tests
- Test with different models
- Mock external dependencies

## Debugging

### Enable Debug Mode

Set in `.env`:

```
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

### Logging

Features should use proper logging:

```python
import logging

logger = logging.getLogger(__name__)

class YourFeature(BaseFeature):
    async def execute(self, request):
        logger.info(f"Executing {self.name} with request: {request}")
        try:
            result = self.process(request)
            logger.debug(f"Feature result: {result}")
            return result
        except Exception as e:
            logger.error(f"Feature error: {e}")
            raise
```

## Contributing

1. Create a feature branch
2. Implement your feature with tests
3. Run the test suite
4. Update documentation
5. Submit a pull request

## Roadmap

### Planned Features

1. **Advanced Code Analysis**
   - AST-based refactoring
   - Performance optimization suggestions
   - Architecture analysis

2. **Multi-Model Orchestration**
   - Model routing based on task type
   - Cost optimization
   - Fallback strategies

3. **Collaborative Development**
   - Multi-user support
   - Shared projects
   - Real-time collaboration

4. **Cloud Integration**
   - Remote execution
   - Scalable infrastructure
   - API endpoints

This structure provides a solid foundation for AI-powered development tools
while maintaining flexibility and extensibility.
