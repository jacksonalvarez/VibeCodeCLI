from .base import BaseLanguageHandler

class TextHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.txt')

    def is_executable(self):
        return False

    def compile(self, filename, project_dir):
        return True, ""

    def run(self, filename, project_dir):
        return False, "Text files are not executable."
