"""
Configuration Management System for AI Coding Agent

Handles all configuration aspects including:
- Environment variables
- Model configurations
- Feature settings
- Prompt templates
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

@dataclass
class LLMModelConfig:
    """Configuration for an LLM model"""
    name: str
    provider: str  # openai, anthropic, etc.
    model_id: str
    max_tokens: int
    temperature: float
    cost_per_1k_input: float
    cost_per_1k_output: float
    context_window: int
    supports_functions: bool = False
    supports_vision: bool = False

@dataclass
class FeatureConfig:
    """Configuration for a feature"""
    name: str
    enabled: bool
    config: Dict[str, Any] = None
    dependencies: List[str] = None

class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or "config")
        self.config_dir.mkdir(exist_ok=True)
        
        # Load environment variables
        load_dotenv()
        
        # Configuration cache
        self._models = {}
        self._features = {}
        self._prompts = {}
        self._settings = {}
        
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files"""
        try:
            self._load_models()
            self._load_features()
            self._load_prompts()
            self._load_settings()
        except Exception as e:
            print(f"Error loading configurations: {e}")
    
    def _load_models(self):
        """Load model configurations"""
        models_file = self.config_dir / "models.yaml"
        if models_file.exists():
            with open(models_file, 'r') as f:
                models_data = yaml.safe_load(f)
                for model_data in models_data.get('models', []):
                    model = LLMModelConfig(**model_data)
                    self._models[model.name] = model
        else:
            # Create default models config
            self._create_default_models_config()
    
    def _create_default_models_config(self):
        """Create default models configuration"""
        default_models = {
            'models': [
                {
                    'name': 'gpt-4',
                    'provider': 'openai',
                    'model_id': 'gpt-4',
                    'max_tokens': 4096,
                    'temperature': 0.7,
                    'cost_per_1k_input': 0.03,
                    'cost_per_1k_output': 0.06,
                    'context_window': 8192,
                    'supports_functions': True,
                    'supports_vision': False
                },
                {
                    'name': 'gpt-3.5-turbo',
                    'provider': 'openai',
                    'model_id': 'gpt-3.5-turbo',
                    'max_tokens': 4096,
                    'temperature': 0.7,
                    'cost_per_1k_input': 0.001,
                    'cost_per_1k_output': 0.002,
                    'context_window': 16384,
                    'supports_functions': True,
                    'supports_vision': False
                },
                {
                    'name': 'claude-3-haiku',
                    'provider': 'anthropic',
                    'model_id': 'claude-3-haiku-20240307',
                    'max_tokens': 4096,
                    'temperature': 0.7,
                    'cost_per_1k_input': 0.00025,
                    'cost_per_1k_output': 0.00125,
                    'context_window': 200000,
                    'supports_functions': False,
                    'supports_vision': True
                }
            ]
        }
        
        models_file = self.config_dir / "models.yaml"
        with open(models_file, 'w') as f:
            yaml.dump(default_models, f, default_flow_style=False)
        
        # Load the created config
        for model_data in default_models['models']:
            model = LLMModelConfig(**model_data)
            self._models[model.name] = model
    
    def _load_features(self):
        """Load feature configurations"""
        features_file = self.config_dir / "features.yaml"
        if features_file.exists():
            with open(features_file, 'r') as f:
                features_data = yaml.safe_load(f)
                for feature_data in features_data.get('features', []):
                    feature = FeatureConfig(**feature_data)
                    self._features[feature.name] = feature
    
    def _load_prompts(self):
        """Load prompt templates"""
        prompts_dir = self.config_dir / "prompts"
        if prompts_dir.exists():
            for prompt_file in prompts_dir.glob("*.yaml"):
                with open(prompt_file, 'r') as f:
                    prompt_data = yaml.safe_load(f)
                    self._prompts[prompt_file.stem] = prompt_data
    
    def _load_settings(self):
        """Load application settings"""
        settings_file = self.config_dir / "settings.yaml"
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                self._settings = yaml.safe_load(f)
        else:
            # Create default settings
            self._create_default_settings()
    
    def _create_default_settings(self):
        """Create default application settings"""
        default_settings = {
            'agent': {
                'max_attempts': 5,
                'max_json_retries': 3,
                'default_model': 'gpt-3.5-turbo',
                'enable_monitoring': True,
                'auto_save_projects': True
            },
            'ui': {
                'theme': 'default',
                'auto_refresh_monitoring': True,
                'monitoring_refresh_interval': 5
            },
            'development': {
                'debug_mode': False,
                'log_level': 'INFO',
                'enable_experimental_features': False
            }
        }
        
        settings_file = self.config_dir / "settings.yaml"
        with open(settings_file, 'w') as f:
            yaml.dump(default_settings, f, default_flow_style=False)
        
        self._settings = default_settings
    
    # Public API methods
    def get_model_config(self, model_name: str) -> Optional[LLMModelConfig]:
        """Get configuration for a specific model"""
        return self._models.get(model_name)
    
    def get_all_models(self) -> Dict[str, LLMModelConfig]:
        """Get all model configurations"""
        return self._models.copy()
    
    def get_feature_config(self, feature_name: str) -> Optional[FeatureConfig]:
        """Get configuration for a specific feature"""
        return self._features.get(feature_name)
    
    def get_prompt_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get a prompt template"""
        return self._prompts.get(template_name)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value using dot notation (e.g., 'agent.max_attempts')"""
        keys = key.split('.')
        value = self._settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_api_key(self, provider: str = None) -> Optional[str]:
        """Get API key for a provider"""
        if provider:
            key_var = f"{provider.upper()}_API_KEY"
            return os.getenv(key_var)
        
        # Try common API key environment variables
        for var in ['LLM_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'API_KEY']:
            key = os.getenv(var)
            if key:
                return key
        
        return None
    
    def update_setting(self, key: str, value: Any) -> None:
        """Update a setting value"""
        keys = key.split('.')
        current = self._settings
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        self._save_settings()
    
    def _save_settings(self):
        """Save settings to file"""
        settings_file = self.config_dir / "settings.yaml"
        with open(settings_file, 'w') as f:
            yaml.dump(self._settings, f, default_flow_style=False)

# Global configuration manager
config_manager = ConfigManager()
