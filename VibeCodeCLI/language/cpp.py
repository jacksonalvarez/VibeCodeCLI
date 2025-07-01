from .base import BaseLanguageHandler
import subprocess
import os

class CppHandler(BaseLanguageHandler):
    @staticmethod
    def matches(filename):
        return filename.endswith('.cpp')

    def is_executable(self):
        return True

    def compile(self, filename, project_dir):
        exe_name = os.path.splitext(os.path.basename(filename))[0]
        try:
            result = subprocess.run(
                ["g++", filename, "-o", exe_name],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, "C++ compilation successful."
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    def run(self, filename, project_dir):
        exe_name = os.path.splitext(os.path.basename(filename))[0]
        exe_path = os.path.join(project_dir, exe_name)
        try:
            result = subprocess.run(
                [exe_path],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
