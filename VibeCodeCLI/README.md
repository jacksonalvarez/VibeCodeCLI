# VibeCodeCLI

## Overview

VibeCodeCLI is an AI-assisted coding agent designed to streamline software
development tasks. It leverages advanced language models to generate, debug, and
refine code projects based on user feedback. The project integrates a
Textual-based UI for seamless interaction and monitoring.

## Features

- **AI-Powered Code Generation**: Generate complete project structures and files
  using advanced LLMs.
- **Feedback Integration**: Process user feedback to iteratively improve project
  files.
- **Textual UI**: Interactive and user-friendly interface for managing projects
  and chat history.
- **Monitoring**: Integrated monitoring classes for tracking operations and
  debugging.
- **Multi-threading**: Efficient parallel processing for feedback and file
  operations.

## Project Structure

```
C:/
│   LICENSE
│   README.md
│
├───ai_projects
│       projects_will_be_here.txt
│
└───VibeCodeCLI
    │   agent.py
    │   api_monitoring.db
    │   debug_global_monitoring.py
    │   llm_utils.py
    │   master_monitoring.py
    │   prompter.txt
    │   README.md
    │   simple_analyzer.py
    │   test_monitoring_data.py
    │   textual_agent.py
    │   ui_utils.py
    │
    ├───config
    │   │   models.yaml
    │   │   settings.yaml
    │   │   __init__.py
    │   │
    │   ├───prompts
    │
    ├───core
    │   │   __init__.py
    │   │
    │   ├───language
    │   │       __init__.py
    │   │
    │   └───monitoring
    │           __init__.py
    │
    ├───data
    │   ├───cache
    │   ├───examples
    │   └───templates
    ├───docs
    │   ├───api
    │   ├───development
    │   └───user_guide
    ├───features
    │   │   __init__.py
    │   │
    │   ├───code_analysis
    │   │       __init__.py
    │   │
    │   ├───code_generation
    │   │       __init__.py
    │   │
    │   ├───integrations
    │   │       __init__.py
    │   │
    │   └───project_templates
    │           __init__.py
    │
    ├───language
    │   │   base.py
    │   │   c.py
    │   │   cpp.py
    │   │   cs.py
    │   │   css.py
    │   │   go.py
    │   │   html.py
    │   │   java.py
    │   │   javascript.py
    │   │   json.py
    │   │   md.py
    │   │   php.py
    │   │   python.py
    │   │   rb.py
    │   │   rs.py
    │   │   text.py
    │   │   typescript.py
    │   │   yaml.py
    │   │   __init__.py
    │   │
    │
    ├───requirements
    │       base.txt
    │       dev.txt
    │
    ├───scripts
    │       setup_dev.py
    │       __init__.py
    │
    ├───tests
    │   │   __init__.py
    │   │
    │   ├───fixtures
    │   │       __init__.py
    │   │
    │   ├───integration
    │   │       __init__.py
    │   │
    │   └───unit
    │           __init__.py
    │
    ├───ui
    │   │   __init__.py
    │   │
    │   ├───components
    │   │       __init__.py
    │   │
    │   └───themes
    │           __init__.py
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/VibeCodeCLI.git
   cd VibeCodeCLI
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Create a `.env` file in the root directory.
   - Add your API key:
     ```
     OPENAI_API_KEY=your_openai_api_key
     ```

## Usage

1. Run the Textual UI:
   ```bash
   python textual_agent.py
   ```

2. Interact with the coding agent:
   - Provide a project description or feedback via the UI.
   - View generated project structure and files.

3. Monitor operations:
   - Debug output and monitoring logs are displayed in the terminal.

## How It Works

- **Initialization**: The agent verifies API keys and sets up the environment.
- **Project Creation**: Users provide a task prompt, and the agent generates a
  project structure.
- **Feedback Processing**: Users can provide feedback to refine the project
  iteratively.
- **Execution**: The agent writes files to disk and executes the main file to
  validate functionality.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request
with your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for
details.

## Contact

For questions or support, please contact alvarezjd404@gmail.com.

## Architecture and File Justification

### Root Directory

- **LICENSE**: Contains the licensing information for the project.
- **README.md**: Documentation for the project, including installation, usage,
  and architecture.

### ai_projects

- **projects_will_be_here.txt**: Placeholder file indicating where AI-generated
  projects will be stored.

### VibeCodeCLI

#### Scripts

- **agent.py**: Implements the `LLMCodingAgent` class, which handles project
  creation, feedback processing, and file execution. It includes methods for API
  key verification, feedback integration, and asynchronous operations.
- **api_monitoring.db**: Database file for storing API monitoring data.
- **debug_global_monitoring.py**: Script for debugging and tracking global
  monitoring operations.
- **llm_utils.py**: Utility functions for interacting with language models,
  including `call_llm`, `write_files`, and `run_code`.
- **master_monitoring.py**: Contains monitoring logic for tracking operations
  and debugging. Includes classes like `FallbackMonitoring` and
  `MonitoringIntegration`.
- **prompter.txt**: Stores prompts used for feedback and project creation.
- **README.md**: Project documentation.
- **simple_analyzer.py**: Analyzes project structure and dependencies.
- **test_monitoring_data.py**: Placeholder script for testing monitoring data.
- **textual_agent.py**: Implements the Textual-based UI for interacting with the
  coding agent. Includes features like scrollable panels, text wrapping, and
  ASCII project structure display.
- **ui_utils.py**: Utility functions for UI components.

#### Folders

##### config

- **models.yaml**: Configuration for AI models.
- **settings.yaml**: General settings for the project.
- ****init**.py**: Initializes the `config` module.
- **prompts/**: Contains prompt templates for various tasks.

##### core

- ****init**.py**: Initializes the `core` module.
- **language/**: Contains language-specific utilities.
  - ****init**.py**: Initializes the `language` module.
- **monitoring/**: Contains monitoring-related utilities.
  - ****init**.py**: Initializes the `monitoring` module.

##### data

- **cache/**: Stores cached data.
- **examples/**: Contains example data files.
- **templates/**: Stores templates for project generation.

##### docs

- **api/**: API documentation.
- **development/**: Development guidelines.
- **user_guide/**: User guide documentation.

##### features

- ****init**.py**: Initializes the `features` module.
- **code_analysis/**: Contains scripts for analyzing code.
  - ****init**.py**: Initializes the `code_analysis` module.
- **code_generation/**: Contains scripts for generating code.
  - ****init**.py**: Initializes the `code_generation` module.
- **integrations/**: Contains integration-related scripts.
  - ****init**.py**: Initializes the `integrations` module.
- **project_templates/**: Contains templates for project creation.
  - ****init**.py**: Initializes the `project_templates` module.

##### language

- **base.py**: Base class for language-specific utilities.
- **c.py**: Utilities for C programming.
- **cpp.py**: Utilities for C++ programming.
- **cs.py**: Utilities for C# programming.
- **css.py**: Utilities for CSS.
- **go.py**: Utilities for Go programming.
- **html.py**: Utilities for HTML.
- **java.py**: Utilities for Java programming.
- **javascript.py**: Utilities for JavaScript.
- **json.py**: Utilities for JSON.
- **md.py**: Utilities for Markdown.
- **php.py**: Utilities for PHP.
- **python.py**: Utilities for Python programming.
- **rb.py**: Utilities for Ruby programming.
- **rs.py**: Utilities for Rust programming.
- **text.py**: Utilities for plain text.
- **typescript.py**: Utilities for TypeScript.
- **yaml.py**: Utilities for YAML.
- ****init**.py**: Initializes the `language` module.

##### requirements

- **base.txt**: Base requirements for the project.
- **dev.txt**: Development requirements.

##### scripts

- **setup_dev.py**: Script for setting up the development environment.
- ****init**.py**: Initializes the `scripts` module.

##### tests

- ****init**.py**: Initializes the `tests` module.
- **fixtures/**: Contains test fixtures.
  - ****init**.py**: Initializes the `fixtures` module.
- **integration/**: Contains integration tests.
  - ****init**.py**: Initializes the `integration` module.
- **unit/**: Contains unit tests.
  - ****init**.py**: Initializes the `unit` module.

##### ui

- ****init**.py**: Initializes the `ui` module.
- **components/**: Contains UI components.
  - ****init**.py**: Initializes the `components` module.
- **themes/**: Contains UI themes.
  - ****init**.py**: Initializes the `themes` module.
