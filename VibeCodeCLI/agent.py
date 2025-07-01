import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from llm_utils import LLMUtils

# Load environment variables at module level
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables should be set manually.")
    print("Install with: pip install python-dotenv")

class LLMCodingAgent:
    def __init__(self, max_attempts=5, model="gpt-4o", project_folder=None, max_workers=2):
        """
        Initialize the coding agent.
        Args:
            max_attempts (int): Maximum number of attempts to solve the task.
            model (str): OpenAI model name to use. Default is gpt-4o for superior programming capabilities.
            project_folder (str): Optional project folder name.
            max_workers (int): Maximum number of worker threads for parallel operations.
        """
        self.max_attempts = max_attempts
        self.model = model
        self.attempts = 0
        self.task_prompt = ""
        self.chat_history = []
        self.project_files = []
        self.project_folder = project_folder
        self.max_workers = max_workers
        
        # Thread synchronization
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._active_threads = {}
        
        # Verify API key is available
        self._verify_api_key()

    def _verify_api_key(self):
        """
        Verify that an API key is available in environment variables.
        Raises ValueError if no API key is found.
        """
        api_key = (
            os.getenv('OPENAI_API_KEY') or 
            os.getenv('ANTHROPIC_API_KEY') or 
            os.getenv('API_KEY') or
            os.getenv('LLM_API_KEY')
        )
        
        if not api_key or api_key.strip() == "":
            raise ValueError(
                "No API key found in environment variables. "
                "Please set one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, API_KEY, or LLM_API_KEY "
                "in your .env file or environment."
            )
        
        print(f"DEBUG: API key verification successful for model: {self.model}")  # Debug output

    def get_task(self):
        """
        Initialize the chat history using the current task prompt (set externally by the UI).
        """
        self.chat_history = [
            {"role": "system", "content": (
                "You are an expert software engineer. "
                "When asked for a project, return a JSON object with a 'files' key. "
                "Each file should be an object with 'filename' and 'content'. "
                "Example:\n"
                "{'files': [{'filename': 'main.py', 'content': '...'}, {'filename': 'utils.js', 'content': '...'}, {'filename': 'App.jsx', 'content': '...'}]}\n"
                "Do not include markdown or explanations. Only return the JSON."
            )},
            {"role": "user", "content": self.task_prompt}
        ]

    def estimate_max_tokens(self):
        """
        Estimate the maximum number of tokens for the LLM call based on model capabilities.
        Returns:
            int: Estimated max tokens based on model type.
        """
        # Updated model token limits for output - optimized for programming tasks
        model_limits = {
            'gpt-4o': 8192,            # GPT-4o: Use more tokens for complex code generation
            'gpt-4o-2024-08-06': 8192, # Same as gpt-4o
            'gpt-4o-mini': 16384,      # GPT-4o-mini: Excellent for smaller programming tasks
            'gpt-4': 8192,             # GPT-4: Good for programming
            'gpt-4-turbo': 8192,       # GPT-4 Turbo: Increased for better code output
            'gpt-3.5-turbo': 4096,     # GPT-3.5 Turbo: Standard limit
            'claude-3-5-sonnet': 8192, # Claude 3.5 Sonnet: Great for code
            'claude-3-opus': 4096,     # Claude 3 Opus: Standard limit
        }
        
        # Get the limit for current model, default to 8192 for programming
        base_limit = model_limits.get(self.model, 8192)
        
        # For programming tasks, we want substantial output for complete files and functions
        # Use 90% of limit to ensure we don't hit the boundary
        return int(base_limit * 0.90)

    def parse_files(self, llm_response, max_prompt_attempts=3):
        """
        Parse the LLM response as JSON and extract the file manifest.
        Retries if parsing fails, and prompts the LLM to return only JSON.
        Args:
            llm_response (str): The LLM's response content.
            max_prompt_attempts (int): Maximum number of parse attempts.
        Returns:
            list: List of file dictionaries with 'filename' and 'content'.
        """
        attempt = 0
        while attempt < max_prompt_attempts:
            print(f"LLM raw response (attempt {attempt+1}):", repr(llm_response))
            try:
                # Clean up response if it has markdown code blocks
                if llm_response.strip().startswith("```"):
                    lines = llm_response.strip().splitlines()
                    llm_response = "\n".join(lines[1:-1])
                
                # Handle single quotes in JSON (common LLM mistake)
                if llm_response.strip().startswith("{'files'"):
                    llm_response = llm_response.replace("'", '"')
                
                data = json.loads(llm_response)
                files = data.get("files", [])
                
                if not files:
                    raise ValueError("No files found in response")
                    
                return files
                
            except Exception as e:
                print(f"❌ Failed to parse LLM response as JSON (attempt {attempt+1}):", e)
                attempt += 1
                if attempt < max_prompt_attempts:
                    print("🔁 Asking LLM to return ONLY the JSON manifest, no explanations or markdown.")
                    self.chat_history.append({
                        "role": "user",
                        "content": (
                            "Your last response could not be parsed as JSON. "
                            "Return ONLY the JSON manifest for the files, no explanations, no markdown, no extra text. "
                            "Format: {\"files\": [{\"filename\": \"main.py\", \"content\": \"...\"}]}"
                        )
                    })
                    try:
                        llm_response = LLMUtils.call_llm(self.model, self.chat_history, self.estimate_max_tokens())
                    except Exception as llm_error:
                        print(f"❌ LLM call failed during retry: {llm_error}")
                        break
        
        print(f"❌ Failed to parse response after {max_prompt_attempts} attempts")
        return []

    def evaluate_output(self, output, error):
        """
        Evaluate the output and error from running the code.
        Args:
            output (str): The standard output from the code.
            error (str): The error output, if any.
        Returns:
            tuple: (success (bool), feedback (str))
        """
        if error:
            return False, "Code threw an error:\n" + error
        if not output:
            return False, "Code ran but produced no output."
        return True, "Output looks valid."

    def update_prompt(self, feedback):
        """
        Update the chat history with feedback for the LLM to improve its next response.
        Also updates the project structure to maintain consistency.
        Thread-safe implementation.
        
        Args:
            feedback (str): Feedback message to send to the LLM.
        """
        # Use lock for thread safety when modifying shared data
        with self._lock:
            # Add the current project files as assistant response to maintain context
            if self.project_files:
                self.chat_history.append({
                    "role": "assistant", 
                    "content": json.dumps({"files": self.project_files})
                })
            
            # Add user feedback with enhanced context
            self.chat_history.append({
                "role": "user", 
                "content": (
                    f"The current project has issues. Feedback:\n{feedback}\n\n"
                    f"Please analyze the existing project structure and make the necessary improvements. "
                    f"Return the complete updated JSON manifest with all files (both modified and unchanged). "
                    f"Ensure the project structure is coherent and addresses the feedback."
                )
            })
            
            # Increment attempts counter
            self.attempts += 1
            
            print(f"DEBUG: Updated chat history with feedback. Total messages: {len(self.chat_history)}")
            print(f"DEBUG: Attempt number: {self.attempts}/{self.max_attempts}")

    def reset(self):
        """
        Reset the agent state for a new task.
        Thread-safe implementation.
        """
        with self._lock:
            # Cancel any ongoing operations
            for thread_id, thread in list(self._active_threads.items()):
                if thread.is_alive():
                    print(f"DEBUG: Cancelling active thread {thread_id}")
                    # Can't actually cancel threads in Python, but we can note they should be ignored
            
            self._active_threads = {}
            self.attempts = 0
            self.task_prompt = ""
            self.chat_history = []
            self.project_files = []
            self.project_folder = None
            
            print("DEBUG: Agent state reset completely")

    @staticmethod
    def check_api_key():
        """
        Static method to check if API key is available.
        Returns:
            bool: True if API key is found, False otherwise.
        """
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
            
        api_key = (
            os.getenv('OPENAI_API_KEY') or 
            os.getenv('ANTHROPIC_API_KEY') or 
            os.getenv('API_KEY') or
            os.getenv('LLM_API_KEY')
        )
        
        return api_key is not None and api_key.strip() != ""

    def write_and_execute_files(self, files):
        """
        Write files to disk and attempt to execute the main file.
        Updates the project structure to maintain consistency.
        Args:
            files (list): List of file dictionaries with 'filename' and 'content'.
        Returns:
            tuple: (output, error, success) - execution results
        """
        try:
            # Store files in the agent and update project structure
            previous_files = len(self.project_files) if self.project_files else 0
            self.project_files = files
            
            # Add record to chat history about project structure update
            self.chat_history.append({
                "role": "system", 
                "content": f"Project files updated. Files: {len(files)}"
            })
            
            print(f"DEBUG: Project structure updated. Previous: {previous_files}, Current: {len(files)}")
            
            # Write files to disk using LLMUtils
            LLMUtils.write_files(files, self.project_folder)
            
            # Detect the main executable file
            main_file = self._detect_main_file(files)
            if not main_file:
                return "", "No executable file found in project", False
            
            print(f"DEBUG: Executing main file: {main_file}")
            
            # Get the full path to the main file
            if self.project_folder:
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ai_projects', self.project_folder))
                main_file_path = os.path.join(base_dir, main_file)
            else:
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ai_projects'))
                main_file_path = os.path.join(base_dir, main_file)
            
            # Change to the project directory before execution
            original_cwd = os.getcwd()
            try:
                os.chdir(os.path.dirname(main_file_path))
                
                # Run the main file
                output, error = LLMUtils.run_code(os.path.basename(main_file_path))
                
                if error:
                    print(f"DEBUG: Execution error: {error}")
                    return output or "", error, False
                else:
                    print(f"DEBUG: Execution successful: {output}")
                    return output or "", "", True
                    
            finally:
                # Always restore the original working directory
                os.chdir(original_cwd)
                
        except Exception as e:
            print(f"DEBUG: Exception in write_and_execute_files: {e}")
            return "", f"Execution error: {str(e)}", False

    def process_feedback(self, feedback):
        """
        Process user feedback and generate updated files.
        Updates both the project structure and chat history to maintain consistency.
        Thread-safe implementation.
        
        Args:
            feedback (str): User feedback on the current project.
        Returns:
            list: Updated list of files or None if failed.
        """
        thread_id = threading.get_ident()
        print(f"DEBUG: Process feedback thread {thread_id} started")
        
        try:
            with self._lock:
                # Track the previous project state before updates
                previous_file_count = len(self.project_files) if self.project_files else 0
                # Register this thread as active
                self._active_threads[thread_id] = threading.current_thread()
            
            # Update the prompt with feedback (this also updates chat history)
            # update_prompt has its own thread safety
            self.update_prompt(feedback)
            
            print(f"DEBUG: Thread {thread_id} processing feedback to update project structure. Previous files: {previous_file_count}")
            
            # Call LLM with updated chat history - this can be time-consuming
            # We're outside the lock so multiple threads can call LLMs in parallel
            chat_history_copy = None
            with self._lock:
                chat_history_copy = list(self.chat_history)  # Create a copy for thread safety
                
            llm_response = LLMUtils.call_llm(self.model, chat_history_copy, self.estimate_max_tokens())
            
            # Parse the new files
            new_files = self.parse_files(llm_response)
            
            # Acquire lock again for updating shared state
            with self._lock:
                if new_files:
                    # Update the project files
                    self.project_files = new_files
                    
                    # Add a record of the updated structure to chat history for context continuity
                    file_summary = [f"{i+1}. {f.get('filename', 'unnamed')}" for i, f in enumerate(new_files)]
                    print(f"DEBUG: Thread {thread_id}: Project structure updated successfully. New files: {len(new_files)}")
                    print(f"DEBUG: Thread {thread_id}: Updated files: {', '.join(file_summary[:5])}" + 
                          (f" and {len(file_summary) - 5} more..." if len(file_summary) > 5 else ""))
                    
                    # Keep a record of changes in the chat history (as system message for context)
                    self.chat_history.append({
                        "role": "system",
                        "content": f"Project structure has been updated based on feedback. Current file count: {len(new_files)}"
                    })
                    
                    # Remove from active threads
                    if thread_id in self._active_threads:
                        del self._active_threads[thread_id]
                        
                    return new_files
                else:
                    print(f"DEBUG: Thread {thread_id}: Failed to generate new files from feedback")
                    
                    # Remove from active threads
                    if thread_id in self._active_threads:
                        del self._active_threads[thread_id]
                        
                    return None
                
        except Exception as e:
            print(f"DEBUG: Thread {thread_id}: Error processing feedback: {e}")
            
            # Clean up active threads on error
            with self._lock:
                if thread_id in self._active_threads:
                    del self._active_threads[thread_id]
                    
            return None

    def process_feedback_async(self, feedback, callback=None):
        """
        Process user feedback asynchronously using a separate thread.
        Updates both the project structure and chat history to maintain consistency.
        
        Args:
            feedback (str): User feedback on the current project.
            callback (callable): Optional callback function that will be called with 
                                 the updated files when processing completes.
        Returns:
            threading.Thread: The thread handling the feedback processing.
        """
        def _process_thread():
            try:
                # Track start time for performance monitoring
                start_time = time.time()
                print(f"DEBUG: Starting async feedback processing thread")
                
                # Get updated files
                updated_files = self.process_feedback(feedback)
                
                # Calculate processing time
                duration = time.time() - start_time
                print(f"DEBUG: Async feedback processing completed in {duration:.2f}s")
                
                # Call the callback with results if provided
                if callback and callable(callback):
                    callback(updated_files)
                    
            except Exception as e:
                print(f"ERROR: Exception in feedback processing thread: {str(e)}")
                if callback and callable(callback):
                    callback(None)
        
        # Create and start the thread
        thread = threading.Thread(target=_process_thread)
        thread.daemon = True  # Make thread a daemon so it won't block program exit
        thread.start()
        return thread
        
    def process_feedback_with_executor(self, feedback_list, max_workers=2):
        """
        Process multiple feedback items in parallel using a thread pool.
        
        Args:
            feedback_list (list): List of feedback strings to process.
            max_workers (int): Maximum number of parallel workers.
        Returns:
            list: List of updated file sets, one for each feedback item.
        """
        results = []
        
        # Set up callback to collect results
        def collect_result(updated_files):
            if updated_files:
                results.append(updated_files)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for fb in feedback_list:
                future = executor.submit(self.process_feedback, fb)
                futures.append(future)
            
            # Wait for all to complete and collect results
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"ERROR: Exception in feedback executor: {str(e)}")
        
        return results

    def get_feedback_processing_status(self):
        """
        Get the status of any ongoing feedback processing.
        
        Returns:
            dict: Status information including active threads count and progress.
        """
        with self._lock:
            active_count = len(self._active_threads)
            active_threads = [str(thread.ident) for thread in self._active_threads.values() if thread.is_alive()]
            
            return {
                "active_count": active_count,
                "active_threads": active_threads,
                "attempts": self.attempts,
                "max_attempts": self.max_attempts,
                "has_project": len(self.project_files) > 0,
                "chat_history_length": len(self.chat_history)
            }

    def cleanup(self):
        """
        Clean up resources used by the agent.
        Should be called when the agent is no longer needed.
        """
        try:
            # Shut down thread pool
            if hasattr(self, '_executor') and self._executor:
                self._executor.shutdown(wait=False)
                
            # Reset internal state
            with self._lock:
                self._active_threads = {}
                
            print("DEBUG: Agent resources cleaned up")
        except Exception as e:
            print(f"ERROR: Exception during agent cleanup: {str(e)}")
            
    def __del__(self):
        """Destructor to ensure resources are cleaned up"""
        try:
            self.cleanup()
        except:
            pass  # Suppress errors during destruction

    def _detect_main_file(self, files):
        """
        Detect the main executable file from a list of files.
        Args:
            files (list): List of file dictionaries.
        Returns:
            str: Main file name or None if not found.
        """
        # Priority scoring for different file extensions
        executable_extensions = {
            '.py': 90,
            '.js': 80,
            '.ts': 78,
            '.java': 70,
            '.cpp': 60,
            '.c': 50,
            '.cs': 40,
            '.go': 85,
            '.rs': 80,
            '.rb': 75,
            '.php': 70,
            '.html': 20
        }
        
        best_file = None
        best_score = 0
        
        for file_dict in files:
            filename = file_dict.get('filename', '')
            if not filename:
                continue
                
            # Get file extension
            ext = os.path.splitext(filename)[1].lower()
            
            # Base score from extension
            score = executable_extensions.get(ext, 0)
            
            # Bonus points for common main file names
            basename = os.path.splitext(os.path.basename(filename))[0].lower()
            if basename in ['main', 'index', 'app', 'program', 'run']:
                score += 20
            elif basename.startswith('main'):
                score += 10
            
            # Bonus for being in root directory (no subdirectories)
            if '/' not in filename and '\\' not in filename:
                score += 5
            
            if score > best_score:
                best_score = score
                best_file = filename
        
        return best_file