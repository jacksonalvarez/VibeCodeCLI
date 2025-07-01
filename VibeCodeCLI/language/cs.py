from .base import BaseLanguageHandler
import subprocess
import os

class CSharpHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.cs')

    def is_executable(self):
        return True

    def compile(self, filename, project_dir):
        try:
            result = subprocess.run(
                ["csc", filename],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, "C# compilation successful."
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    def run(self, filename, project_dir):
        exe_name = os.path.splitext(os.path.basename(filename))[0] + ".exe"
        exe_path = os.path.join(project_dir, exe_name)
        try:
            result = subprocess.run(
                ["mono", exe_path],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
