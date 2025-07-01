import openai
import json
import io
import contextlib
import os
import subprocess
import traceback
import time
from datetime import datetime
from dotenv import load_dotenv

def select_project_type():
    """
    Prompt the user to select a language/project structure.
    Returns:
        str: The selected project type key.
    """
    print("Select a language/project structure:")
    print("1. Node.js (JS/HTML/React, option for mobile)")
    print("2. Python")
    print("3. Java (option to JAR)")
    print("4. C# Game Development")
    print("5. .NET Application (C++/C)")
    print("6. General (no specific structure)")
    choice = input("> ").strip()
    mapping = {
        "1": "node",
        "2": "python",
        "3": "java",
        "4": "csharp_game",
        "5": "dotnet",
        "6": "general"
    }
    return mapping.get(choice, "general")

def get_api_key():
    """
    Get API key from environment variables.
    Loads .env file and checks for common API key variable names.
    Returns:
        str: The API key if found, None otherwise.
    """
    # Load .env file from current directory
    load_dotenv()
    
    # Check for common API key environment variable names
    api_key = (
        os.getenv('LLM_API_KEY') or 
        os.getenv('OPENAI_API_KEY') or 
        os.getenv('ANTHROPIC_API_KEY') or 
        os.getenv('API_KEY')
    )
    
    print(f"🔑 API key check - Using: {'LLM_API_KEY' if os.getenv('LLM_API_KEY') else 'OPENAI_API_KEY' if os.getenv('OPENAI_API_KEY') else 'ANTHROPIC_API_KEY' if os.getenv('ANTHROPIC_API_KEY') else 'API_KEY' if os.getenv('API_KEY') else 'None found'}")
    print(f"   Key present: {'Yes' if api_key and api_key.strip() else 'No'}")
    
    if not api_key or not api_key.strip():
        raise ValueError(
            "No API key found in environment variables. "
            "Please set LLM_API_KEY in your .env file."
        )

    return api_key

class LLMUtils:
    """
    Utility class for LLM calls and file operations.
    """
    _monitor_instance = None  # Shared monitoring instance
    
    @staticmethod
    def call_llm(model, chat_history, max_tokens):
        """
        Call the OpenAI LLM with the given chat history.
        Args:
            model (str): Model name.
            chat_history (list): List of chat messages.
            max_tokens (int): Max tokens for response.
        Returns:
            str: LLM response content.
        Raises:
            Exception: If API key is not found or API call fails.
        """
        # Get API key from environment
        
        # Set the API key for OpenAI
        openai.api_key = get_api_key()
        
        try:
            print(f"\n🔍 OpenAI API Call at {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Model: {model}")
            print(f"   Max tokens: {max_tokens}")
            
            start_time = time.time()
            response = openai.chat.completions.create(
                model=model,
                messages=chat_history,
                temperature=0,
                max_tokens=max_tokens
            )
            
            duration = time.time() - start_time
            
            # Log usage information
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                print(f"   ✅ Success in {duration:.2f}s")
                print(f"   Input tokens: {usage.prompt_tokens:,}")
                print(f"   Output tokens: {usage.completion_tokens:,}")
                print(f"   Total tokens: {usage.total_tokens:,}")
                
                # Calculate cost based on actual model
                if model == "gpt-4o" or model == "gpt-4o-2024-08-06":
                    input_cost = (usage.prompt_tokens / 1_000_000) * 5.00
                    output_cost = (usage.completion_tokens / 1_000_000) * 15.00
                    print(f"   💰 Cost (gpt-4o): ${input_cost + output_cost:.4f}")
                elif model == "gpt-4o-mini":
                    input_cost = (usage.prompt_tokens / 1_000_000) * 0.15
                    output_cost = (usage.completion_tokens / 1_000_000) * 0.60
                    print(f"   💰 Cost (gpt-4o-mini): ${input_cost + output_cost:.4f}")
                else:
                    print(f"   💰 Cost calculation not available for model: {model}")
                
                # Record API call for monitoring (if monitoring is available)
                try:
                    from master_monitoring import MasterMonitoring
                    # Try to get global monitoring instance or create a temporary one
                    monitor = getattr(LLMUtils, '_monitor_instance', None)
                    if not monitor:
                        monitor = MasterMonitoring()
                        LLMUtils._monitor_instance = monitor
                    
                    # Get cached tokens safely
                    cached_tokens = 0
                    if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                        if hasattr(usage.prompt_tokens_details, 'cached_tokens'):
                            cached_tokens = usage.prompt_tokens_details.cached_tokens
                    
                    # Record the API call
                    monitor.record_api_call(
                        model=model,
                        input_tokens=usage.prompt_tokens,
                        output_tokens=usage.completion_tokens,
                        duration=duration,
                        cached_tokens=cached_tokens,
                        task_type="feedback_request",
                        success=True
                    )
                    print(f"   📊 Monitoring: API call recorded successfully")
                except Exception as monitor_error:
                    # Don't let monitoring errors break the main functionality
                    print(f"   ⚠️  Monitoring error: {monitor_error}")
                    
            else:
                print(f"   ✅ Success in {duration:.2f}s (no usage info)")
                
                # Still try to record the call even without usage info
                try:
                    from master_monitoring import MasterMonitoring
                    monitor = getattr(LLMUtils, '_monitor_instance', None)
                    if not monitor:
                        monitor = MasterMonitoring()
                        LLMUtils._monitor_instance = monitor
                    
                    # Estimate tokens if not available (rough estimate)
                    estimated_input = sum(len(msg.get('content', '')) for msg in chat_history) // 3
                    estimated_output = max_tokens // 2  # Rough estimate
                    
                    monitor.record_api_call(
                        model=model,
                        input_tokens=estimated_input,
                        output_tokens=estimated_output,
                        duration=duration,
                        task_type="llm_request",
                        success=True
                    )
                    print(f"   📊 Monitoring: API call recorded (estimated tokens)")
                except Exception as monitor_error:
                    print(f"   ⚠️  Monitoring error: {monitor_error}")
            
            return response.choices[0].message.content
        except openai.AuthenticationError:
            raise Exception(
                "Invalid API key. Please check your API key in the .env file. "
                "Make sure it'sdsdsds a valid OpenAI API key starting with 'sk-'"
            )
        except openai.RateLimitError:
            raise Exception(
                "API rate limit exceeded. Please wait a moment and try again."
            )
        except openai.APIError as e:
            raise Exception(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error calling LLM: {str(e)}")

    @staticmethod
    def write_files(files, project_folder=None):
        """
        Write the generated files to disk in a dedicated ai_projects folder outside the current project.
        Args:
            files (list): List of file dicts with 'filename' and 'content'.
            project_folder (str): The project folder name (slugified from task prompt).
        """
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ai_projects'))
        if project_folder:
            base_dir = os.path.join(base_dir, project_folder)
        os.makedirs(base_dir, exist_ok=True)
        for file in files:
            filename = file["filename"]
            content = file["content"]
            full_path = os.path.join(base_dir, filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Wrote file: {full_path}")

    @staticmethod
    def run_code(filename):
        """
        Run the specified code file in a subprocess and capture its output and errors.
        Args:
            filename (str): The filename to execute.
        Returns:
            tuple: (output, error) strings. Error is None if successful.
        """
        import subprocess, sys, os
        ext = os.path.splitext(filename)[1].lower()
        try:
            if ext == ".py":
                result = subprocess.run([sys.executable, filename], capture_output=True, text=True, timeout=30)
                return result.stdout.strip(), result.stderr if result.returncode != 0 else None
            elif ext == ".js":
                result = subprocess.run(["node", filename], capture_output=True, text=True, timeout=10)
                return result.stdout.strip(), result.stderr if result.returncode != 0 else None
            elif ext == ".ts":
                result = subprocess.run(["ts-node", filename], capture_output=True, text=True, timeout=10)
                return result.stdout.strip(), result.stderr if result.returncode != 0 else None
            elif ext == ".java":
                compile_result = subprocess.run(["javac", filename], capture_output=True, text=True, timeout=10)
                if compile_result.returncode != 0:
                    return None, compile_result.stderr
                classname = os.path.splitext(os.path.basename(filename))[0]
                run_result = subprocess.run(["java", classname], capture_output=True, text=True, timeout=10)
                return run_result.stdout.strip(), run_result.stderr if run_result.returncode != 0 else None
            elif ext == ".cpp":
                exe_name = "a.exe"
                compile_result = subprocess.run(["g++", filename, "-o", exe_name], capture_output=True, text=True, timeout=10)
                if compile_result.returncode != 0:
                    return None, compile_result.stderr
                run_result = subprocess.run([exe_name], capture_output=True, text=True, timeout=10)
                return run_result.stdout.strip(), run_result.stderr if run_result.returncode != 0 else None
            elif ext == ".c":
                exe_name = "a.exe"
                compile_result = subprocess.run(["gcc", filename, "-o", exe_name], capture_output=True, text=True, timeout=10)
                if compile_result.returncode != 0:
                    return None, compile_result.stderr
                run_result = subprocess.run([exe_name], capture_output=True, text=True, timeout=10)
                return run_result.stdout.strip(), run_result.stderr if run_result.returncode != 0 else None
            elif ext == ".cs":
                exe_name = "program.exe"
                compile_result = subprocess.run(["csc", "/out:" + exe_name, filename], capture_output=True, text=True, timeout=10)
                if compile_result.returncode != 0:
                    return None, compile_result.stderr
                run_result = subprocess.run([exe_name], capture_output=True, text=True, timeout=10)
                return run_result.stdout.strip(), run_result.stderr if run_result.returncode != 0 else None
            else:
                return None, f"Automatic execution for {ext} files is not supported."
        except subprocess.TimeoutExpired:
            return None, "Execution timed out."
        except Exception as e:
            import traceback
            return None, traceback.format_exc()

# Example integration for main.py or similar entry point:
if __name__ == "__main__":
    # 1. Select project type
    project_type = select_project_type()
    print(f"Selected project type: {project_type}")
    # 2. Use project_type to customize LLM prompt (not shown here)
    # 3. Continue with your normal workflow (get task, call LLM, etc.)
    # This is a minimal integration for future expansion.