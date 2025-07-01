from .base import BaseLanguageHandler
import subprocess
import os

class JavaHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.java')

    def is_executable(self):
        return True

    def compile(self, filename, project_dir):
        try:
            result = subprocess.run(
                ["javac", filename],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, "Java compilation successful."
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    def run(self, filename, project_dir):
        classname = os.path.splitext(os.path.basename(filename))[0]
        try:
            result = subprocess.run(
                ["java", classname],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
