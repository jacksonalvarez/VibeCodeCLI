from abc import ABC, abstractmethod

class BaseLanguageHandler(ABC):
    @staticmethod
    @abstractmethod
    def matches(filename):
        """Return True if this handler can handle the given filename."""
        pass

    @abstractmethod
    def is_executable(self):
        pass

    @abstractmethod
    def compile(self, filename, project_dir):
        """Compile the file if needed. Return (success: bool, output: str)"""
        pass

    @abstractmethod
    def run(self, filename, project_dir):
        """Run the file. Return (success: bool, output: str)"""
        pass
