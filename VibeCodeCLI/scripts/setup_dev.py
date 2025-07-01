"""
Development Setup Script for AI Coding Agent

This script sets up the development environment and installs dependencies.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

class DevSetup:
    """Development environment setup"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.requirements_dir = self.project_root / "requirements"
        
    def run_command(self, command, check=True):
        """Run a shell command"""
        print(f"Running: {command}")
        result = subprocess.run(command, shell=True, check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result
    
    def check_python_version(self):
        """Check Python version compatibility"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("ERROR: Python 3.8+ is required")
            sys.exit(1)
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    
    def create_virtual_environment(self):
        """Create virtual environment if it doesn't exist"""
        venv_path = self.project_root / "venv"
        if not venv_path.exists():
            print("Creating virtual environment...")
            self.run_command(f"python -m venv {venv_path}")
        else:
            print("✓ Virtual environment exists")
        return venv_path
    
    def get_pip_command(self, venv_path):
        """Get pip command for the virtual environment"""
        if platform.system() == "Windows":
            return str(venv_path / "Scripts" / "pip")
        else:
            return str(venv_path / "bin" / "pip")
    
    def install_requirements(self, venv_path):
        """Install all requirements"""
        pip_cmd = self.get_pip_command(venv_path)
        
        # Install base requirements
        base_req = self.requirements_dir / "base.txt"
        if base_req.exists():
            self.run_command(f"{pip_cmd} install -r {base_req}")
        
        # Install development requirements
        dev_req = self.requirements_dir / "dev.txt"
        if dev_req.exists():
            self.run_command(f"{pip_cmd} install -r {dev_req}")
        
        # Install package in development mode
        self.run_command(f"{pip_cmd} install -e .")
    
    def create_requirements_files(self):
        """Create requirements files if they don't exist"""
        self.requirements_dir.mkdir(exist_ok=True)
        
        # Base requirements
        base_requirements = [
            "textual>=0.40.0",
            "rich>=13.0.0", 
            "python-dotenv>=1.0.0",
            "pyyaml>=6.0",
            "requests>=2.28.0",
            "aiohttp>=3.8.0",
            "pydantic>=2.0.0",
            "click>=8.0.0"
        ]
        
        base_file = self.requirements_dir / "base.txt"
        if not base_file.exists():
            with open(base_file, 'w') as f:
                f.write('\n'.join(base_requirements))
        
        # Development requirements
        dev_requirements = [
            "-r base.txt",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "pyperclip>=1.8.0"
        ]
        
        dev_file = self.requirements_dir / "dev.txt"
        if not dev_file.exists():
            with open(dev_file, 'w') as f:
                f.write('\n'.join(dev_requirements))
        
        print("✓ Requirements files created")
    
    def create_project_structure(self):
        """Create project directory structure"""
        directories = [
            "core",
            "core/monitoring",
            "core/language",
            "ui",
            "ui/components",
            "ui/themes",
            "features",
            "features/code_analysis",
            "features/project_templates", 
            "features/code_generation",
            "features/integrations",
            "scripts",
            "config",
            "config/prompts",
            "data",
            "data/templates",
            "data/examples",
            "data/cache",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/fixtures",
            "docs",
            "docs/api",
            "docs/user_guide",
            "docs/development"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py for Python packages
            if not directory.startswith(('docs', 'data', 'config')):
                init_file = dir_path / "__init__.py"
                if not init_file.exists():
                    init_file.touch()
        
        print("✓ Project structure created")
    
    def create_config_files(self):
        """Create configuration files"""
        # .env.example
        env_example = self.project_root / ".env.example"
        if not env_example.exists():
            with open(env_example, 'w') as f:
                f.write("""# AI Coding Agent Environment Variables

# LLM API Keys (choose one or more)
LLM_API_KEY=your_default_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Specific model preferences
DEFAULT_MODEL=gpt-3.5-turbo
ENABLE_MONITORING=true

# Development settings
DEBUG_MODE=false
LOG_LEVEL=INFO
""")
        
        # .gitignore
        gitignore = self.project_root / ".gitignore"
        if not gitignore.exists():
            with open(gitignore, 'w') as f:
                f.write("""# Environment files
.env
.env.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Data and cache
data/cache/
*.log
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db
""")
        
        print("✓ Configuration files created")
    
    def setup_pre_commit(self, venv_path):
        """Setup pre-commit hooks"""
        pip_cmd = self.get_pip_command(venv_path)
        
        # Create .pre-commit-config.yaml
        precommit_config = self.project_root / ".pre-commit-config.yaml"
        if not precommit_config.exists():
            with open(precommit_config, 'w') as f:
                f.write("""repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 22.12.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]
""")
        
        # Install pre-commit hooks
        try:
            if platform.system() == "Windows":
                python_cmd = str(venv_path / "Scripts" / "python")
            else:
                python_cmd = str(venv_path / "bin" / "python")
            
            self.run_command(f"{python_cmd} -m pre_commit install")
            print("✓ Pre-commit hooks installed")
        except subprocess.CalledProcessError:
            print("⚠ Pre-commit installation failed (optional)")
    
    def run_setup(self):
        """Run the complete setup process"""
        print("🚀 Setting up AI Coding Agent development environment...\n")
        
        # Check Python version
        self.check_python_version()
        
        # Create project structure
        self.create_project_structure()
        
        # Create requirements files
        self.create_requirements_files()
        
        # Create virtual environment
        venv_path = self.create_virtual_environment()
        
        # Install requirements
        print("Installing requirements...")
        self.install_requirements(venv_path)
        
        # Create configuration files
        self.create_config_files()
        
        # Setup pre-commit (optional)
        self.setup_pre_commit(venv_path)
        
        print("\n✅ Development environment setup complete!")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and add your API keys")
        print("2. Activate virtual environment:")
        if platform.system() == "Windows":
            print(f"   {venv_path}\\Scripts\\activate")
        else:
            print(f"   source {venv_path}/bin/activate")
        print("3. Run: python -m scripts.run_tests")
        print("4. Start developing! 🎉")

if __name__ == "__main__":
    setup = DevSetup()
    setup.run_setup()
