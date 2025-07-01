from .base import BaseLanguageHandler

class MarkdownHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.md')

    def is_executable(self):
        return False

    def compile(self, filename, project_dir):
        return True, ""

    def run(self, filename, project_dir):
        return False, "Markdown files are not executable."
