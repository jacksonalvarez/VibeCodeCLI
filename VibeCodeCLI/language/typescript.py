from .base import BaseLanguageHandler
import subprocess
import os

class TypeScriptHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.ts')

    def is_executable(self):
        return True

    def compile(self, filename, project_dir):
        try:
            result = subprocess.run(
                ["tsc", filename],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, "TypeScript compilation successful."
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    def run(self, filename, project_dir):
        js_file = os.path.splitext(filename)[0] + ".js"
        try:
            result = subprocess.run(
                ["node", js_file],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
