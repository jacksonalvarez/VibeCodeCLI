import json
import os
from llm_utils import LLMUtils

# Load environment variables at module level
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables should be set manually.")
    print("Install with: pip install python-dotenv")

class LLMCodingAgent:
    def __init__(self, max_attempts=5, model="gpt-4o", project_folder=None):
        """
        Initialize the coding agent.
        Args:
            max_attempts (int): Maximum number of attempts to solve the task.
            model (str): OpenAI model name to use.
            project_folder (str): Optional project folder name.
        """
        self.max_attempts = max_attempts
        self.model = model
        self.attempts = 0
        self.task_prompt = ""
        self.chat_history = []
        self.project_files = []
        self.project_folder = project_folder
        
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
        Estimate the maximum number of tokens for the LLM call based on prompt and history length.
        Returns:
            int: Estimated max tokens (capped at 4096).
        """
        base = 1024
        prompt_len = len(self.task_prompt)
        history_len = sum(len(m["content"]) for m in self.chat_history)
        extra = ((prompt_len + history_len) // 500) * 512
        return min(4096, base + extra)

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
        Args:
            feedback (str): Feedback message to send to the LLM.
        """
        # Add the current files as assistant response
        self.chat_history.append({"role": "assistant", "content": json.dumps({"files": self.project_files})})
        
        # Add user feedback
        self.chat_history.append({
            "role": "user", 
            "content": f"The code failed. Error or issue:\n{feedback}\nFix and retry. Return the full JSON manifest again."
        })

    def reset(self):
        """
        Reset the agent state for a new task.
        """
        self.attempts = 0
        self.task_prompt = ""
        self.chat_history = []
        self.project_files = []
        self.project_folder = None

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