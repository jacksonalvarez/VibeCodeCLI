from .base import BaseLanguageHandler

class CSSHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.css')

    def is_executable(self):
        return False

    def compile(self, filename, project_dir):
        return True, ""

    def run(self, filename, project_dir):
        return False, "CSS files are not executable."
