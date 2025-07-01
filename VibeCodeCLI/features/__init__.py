"""
Feature Development Framework for AI Coding Agent

This module provides the base infrastructure for developing and integrating
new features into the AI coding agent.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseFeature(ABC):
    """Base class for all agent features"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.enabled = True
        self.dependencies = []
        self.config = {}
    
    @abstractmethod
    async def initialize(self, agent_context: Dict[str, Any]) -> bool:
        """Initialize the feature with agent context"""
        pass
    
    @abstractmethod
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the feature functionality"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this feature provides"""
        pass
    
    def validate_dependencies(self, available_features: List[str]) -> bool:
        """Check if all dependencies are available"""
        return all(dep in available_features for dep in self.dependencies)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the feature"""
        self.config.update(config)

class FeatureManager:
    """Manages all features in the agent"""
    
    def __init__(self):
        self.features: Dict[str, BaseFeature] = {}
        self.feature_order: List[str] = []
        self.initialized = False
    
    def register_feature(self, feature: BaseFeature) -> None:
        """Register a new feature"""
        if feature.name in self.features:
            logger.warning(f"Feature {feature.name} already registered, overwriting")
        
        self.features[feature.name] = feature
        if feature.name not in self.feature_order:
            self.feature_order.append(feature.name)
        
        logger.info(f"Registered feature: {feature.name} v{feature.version}")
    
    async def initialize_all(self, agent_context: Dict[str, Any]) -> None:
        """Initialize all registered features"""
        # Sort features by dependencies
        sorted_features = self._sort_by_dependencies()
        
        for feature_name in sorted_features:
            feature = self.features[feature_name]
            if feature.enabled:
                try:
                    success = await feature.initialize(agent_context)
                    if success:
                        logger.info(f"Initialized feature: {feature_name}")
                    else:
                        logger.error(f"Failed to initialize feature: {feature_name}")
                        feature.enabled = False
                except Exception as e:
                    logger.error(f"Error initializing feature {feature_name}: {e}")
                    feature.enabled = False
        
        self.initialized = True
    
    def _sort_by_dependencies(self) -> List[str]:
        """Sort features by their dependencies"""
        # Simple topological sort
        sorted_features = []
        remaining = list(self.feature_order)
        
        while remaining:
            # Find features with no unresolved dependencies
            ready = []
            for feature_name in remaining:
                feature = self.features[feature_name]
                deps_satisfied = all(
                    dep in sorted_features or dep not in self.features
                    for dep in feature.dependencies
                )
                if deps_satisfied:
                    ready.append(feature_name)
            
            if not ready:
                # Circular dependency or missing dependency
                logger.warning(f"Circular or missing dependencies detected for: {remaining}")
                ready = remaining  # Add all remaining
            
            for feature_name in ready:
                sorted_features.append(feature_name)
                remaining.remove(feature_name)
        
        return sorted_features
    
    async def execute_feature(self, feature_name: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific feature"""
        if not self.initialized:
            raise RuntimeError("FeatureManager not initialized")
        
        if feature_name not in self.features:
            raise ValueError(f"Feature {feature_name} not found")
        
        feature = self.features[feature_name]
        if not feature.enabled:
            raise RuntimeError(f"Feature {feature_name} is disabled")
        
        try:
            return await feature.execute(request)
        except Exception as e:
            logger.error(f"Error executing feature {feature_name}: {e}")
            raise
    
    def get_available_features(self) -> List[str]:
        """Get list of available (enabled) features"""
        return [name for name, feature in self.features.items() if feature.enabled]
    
    def get_feature_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all features"""
        return {
            name: feature.get_capabilities()
            for name, feature in self.features.items()
            if feature.enabled
        }

# Global feature manager instance
feature_manager = FeatureManager()
