from .base import BaseLanguageHandler

class JSONHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.json')

    def is_executable(self):
        return False

    def compile(self, filename, project_dir):
        return True, ""

    def run(self, filename, project_dir):
        return False, "JSON files are not executable."
