from .base import BaseLanguageHandler

class YAMLHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.yaml') or filename.endswith('.yml')

    def is_executable(self):
        return False

    def compile(self, filename, project_dir):
        return True, ""

    def run(self, filename, project_dir):
        return False, "YAML files are not executable."
