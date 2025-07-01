from .base import BaseLanguageHandler

class HTMLHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.html')

    def is_executable(self):
        return False

    def compile(self, filename, project_dir):
        return True, ""

    def run(self, filename, project_dir):
        return False, "HTML files are not executable."
