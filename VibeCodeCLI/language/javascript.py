from .base import BaseLanguageHandler
import subprocess

class JavaScriptHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.js')

    def is_executable(self):
        return True

    def compile(self, filename, project_dir):
        # No compilation needed for JavaScript
        return True, ""

    def run(self, filename, project_dir):
        try:
            result = subprocess.run(
                ["node", filename],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
