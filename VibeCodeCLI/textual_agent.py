from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, Button, Log, Select
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual import events
from rich.tree import Tree
from rich.text import Text
from rich.console import Console
from agent import LLMCodingAgent
from llm_utils import LLMUtils
import os
import re
import json
import threading
import time
import asyncio
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

def safe_project_name(name):
    # Simple slugify for folder names - enhanced version from main.py
    name = re.sub(r'[^a-zA-Z0-9]+', '-', name.strip().lower()).strip('-')
    return name[:32] or 'project'

def check_api_key():
    """Check if API key is available in environment variables"""
    # Load .env file from current directory
    load_dotenv()
    
    # Check for common API key environment variable names
    api_key = (
        os.getenv('OPENAI_API_KEY') or 
        os.getenv('ANTHROPIC_API_KEY') or 
        os.getenv('API_KEY') or
        os.getenv('LLM_API_KEY')
    )
    
    return api_key is not None and api_key.strip() != ""

def get_env_file_instructions():
    """Return instructions for setting up the environment file"""
    return """
[bold red]API Key Required![/bold red]

To use this coding agent, you need to create a [bold].env[/bold] file in the project directory with your API key.

[bold yellow]Steps:[/bold yellow]
1. Create a file named [bold].env[/bold] in the same directory as this script
2. Add one of the following lines (depending on your LLM provider):

   [cyan]OPENAI_API_KEY=your_openai_api_key_here[/cyan]
   [cyan]ANTHROPIC_API_KEY=your_anthropic_api_key_here[/cyan]
   [cyan]API_KEY=your_api_key_here[/cyan]
   [cyan]LLM_API_KEY=your_api_key_here[/cyan]

3. Save the file and restart the application

[bold]Example .env file:[/bold]
[dim]# .env file content
OPENAI_API_KEY=sk-proj-abcd1234...
# or
ANTHROPIC_API_KEY=sk-ant-api03-abcd1234...[/dim]

[bold red]Note:[/bold red] Never commit your .env file to version control!
Add [bold].env[/bold] to your [bold].gitignore[/bold] file.
"""

def ascii_tree(files):
    """Generate ASCII tree structure from files list - from main.py"""
    from collections import defaultdict
    tree = defaultdict(list)
    for f in files:
        parts = f['filename'].split('/')
        for i in range(1, len(parts)):
            tree['/'.join(parts[:i])].append(parts[i])
    
    def build(prefix, path, depth=0):
        lines = []
        children = sorted(set(tree.get(path, [])))
        for i, child in enumerate(children):
            connector = '└── ' if i == len(children)-1 else '├── '
            full = f"{path}/{child}" if path else child
            lines.append(prefix + connector + child)
            lines += build(prefix + ("    " if i == len(children)-1 else "│   "), full, depth+1)
        return lines
    
    roots = sorted(set(f['filename'].split('/')[0] for f in files))
    lines = []
    for r in roots:
        lines.append(r)
        lines += build("", r)
    return lines

def detect_main_file(files):
    """
    Detect the main executable file from the project files.
    Returns the filename of the main file to execute, or None if no executable file found.
    """
    # Priority order for main files
    main_file_priorities = {
        'main.py': 100,
        'app.py': 90,
        'run.py': 85,
        'index.js': 80,
        'main.js': 80,
        'app.js': 75,
        'server.js': 70,
        'Main.java': 65,
        'App.java': 60,
        'main.cpp': 55,
        'main.c': 50,
        'Program.cs': 45,
        'main.cs': 40,
        'index.html': 35,
        'main.html': 30,
        'main.go': 85,
        'main.rs': 80,
        'main.rb': 75,
        'main.php': 70
    }
    
    # Get all filenames
    filenames = [f['filename'] for f in files]
    
    # First, check for exact matches with priority
    for filename in filenames:
        basename = os.path.basename(filename)
        if basename in main_file_priorities:
            return filename
    
    # If no exact match, look for files by extension with executable potential
    executable_extensions = {
        '.py': 90,
        '.js': 80,
        '.java': 70,
        '.cpp': 60,
        '.c': 50,
        '.cs': 40,
        '.ts': 35,
        '.go': 85,
        '.rs': 80,
        '.rb': 75,
        '.php': 70,
        '.html': 20
    }
    
    best_file = None
    best_score = 0
    
    for filename in filenames:
        ext = os.path.splitext(filename)[1].lower()
        if ext in executable_extensions:
            score = executable_extensions[ext]
            basename = os.path.basename(filename).lower()
            
            # Boost score for files with "main" in name
            if 'main' in basename:
                score += 20
            elif 'app' in basename:
                score += 15
            elif 'index' in basename:
                score += 10
            
            if score > best_score:
                best_score = score
                best_file = filename
    
    return best_file

def get_language_info(filename):
    """
    Get language information based on file extension.
    Returns tuple of (language_name, file_extension, is_executable, compile_command, run_command)
    """
    if not filename:
        return "Unknown", "", False, None, None
    
    ext = os.path.splitext(filename)[1].lower()
    basename = os.path.splitext(os.path.basename(filename))[0]
    
    language_map = {
        '.py': ('Python', '.py', True, None, 'python'),
        '.js': ('JavaScript (Node.js)', '.js', True, None, 'node'),
        '.ts': ('TypeScript', '.ts', True, 'tsc', 'node'),
        '.java': ('Java', '.java', True, 'javac', 'java'),
        '.cpp': ('C++', '.cpp', True, 'g++', './'),
        '.c': ('C', '.c', True, 'gcc', './'),
        '.cs': ('C#', '.cs', True, 'csc', 'mono'),
        '.go': ('Go', '.go', True, None, 'go run'),
        '.rs': ('Rust', '.rs', True, 'rustc', './'),
        '.rb': ('Ruby', '.rb', True, None, 'ruby'),
        '.php': ('PHP', '.php', True, None, 'php'),
        '.html': ('HTML', '.html', False, None, None),
        '.css': ('CSS', '.css', False, None, None),
        '.json': ('JSON', '.json', False, None, None),
        '.md': ('Markdown', '.md', False, None, None),
        '.txt': ('Text', '.txt', False, None, None),
        '.xml': ('XML', '.xml', False, None, None),
        '.yml': ('YAML', '.yml', False, None, None),
        '.yaml': ('YAML', '.yaml', False, None, None)
    }
    
    return language_map.get(ext, ('Unknown', ext, False, None, None))

def check_compiler_available(compile_command):
    """Check if a compiler/interpreter is available in the system"""
    if not compile_command:
        return True
    
    try:
        # Try to run the command with --version or -version flag
        for flag in ['--version', '-version', '--help']:
            try:
                subprocess.run([compile_command, flag], 
                             capture_output=True, 
                             text=True, 
                             timeout=5)
                return True
            except:
                continue
        return False
    except:
        return False

def compile_and_run_code(filepath, project_dir):
    """
    Compile and run code based on file extension.
    Returns tuple of (output, error, success)
    """
    filename = os.path.basename(filepath)
    basename = os.path.splitext(filename)[0]
    lang_name, ext, is_executable, compile_cmd, run_cmd = get_language_info(filename)
    
    if not is_executable:
        return f"File {filename} is not executable", "", False
    
    original_dir = os.getcwd()
    output = ""
    error = ""
    success = False
    
    try:
        os.chdir(project_dir)
        
        # Compilation step (if needed)
        if compile_cmd:
            if not check_compiler_available(compile_cmd):
                return "", f"Compiler '{compile_cmd}' not found. Please install it.", False
            
            compile_success = False
            
            if ext == '.java':
                # Java compilation
                result = subprocess.run([compile_cmd, filename], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    compile_success = True
                    output += f"Compilation successful.\n"
                else:
                    error += f"Compilation failed: {result.stderr}\n"
                    
            elif ext == '.cpp':
                # C++ compilation
                result = subprocess.run([compile_cmd, filename, '-o', basename], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    compile_success = True
                    output += f"Compilation successful.\n"
                else:
                    error += f"Compilation failed: {result.stderr}\n"
                    
            elif ext == '.c':
                # C compilation
                result = subprocess.run([compile_cmd, filename, '-o', basename], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    compile_success = True
                    output += f"Compilation successful.\n"
                else:
                    error += f"Compilation failed: {result.stderr}\n"
                    
            elif ext == '.cs':
                # C# compilation
                result = subprocess.run([compile_cmd, filename], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    compile_success = True
                    output += f"Compilation successful.\n"
                else:
                    error += f"Compilation failed: {result.stderr}\n"
                    
            elif ext == '.rs':
                # Rust compilation
                result = subprocess.run([compile_cmd, filename, '-o', basename], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    compile_success = True
                    output += f"Compilation successful.\n"
                else:
                    error += f"Compilation failed: {result.stderr}\n"
                    
            elif ext == '.ts':
                # TypeScript compilation
                result = subprocess.run([compile_cmd, filename], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    compile_success = True
                    output += f"TypeScript compilation successful.\n"
                    # Update filename to compiled JS file
                    filename = basename + '.js'
                else:
                    error += f"TypeScript compilation failed: {result.stderr}\n"
            
            if not compile_success:
                return output, error, False
        
        # Execution step
        if not check_compiler_available(run_cmd.split()[0] if run_cmd else 'python'):
            return output, error + f"Runtime '{run_cmd}' not found. Please install it.", False
        
        execution_success = False
        
        if ext == '.py':
            # Python execution
            result = subprocess.run([run_cmd, filename], 
                                  capture_output=True, text=True, timeout=30)
            output += result.stdout
            if result.stderr:
                error += result.stderr
            execution_success = result.returncode == 0
            
        elif ext == '.js':
            # JavaScript execution
            result = subprocess.run([run_cmd, filename], 
                                  capture_output=True, text=True, timeout=30)
            output += result.stdout
            if result.stderr:
                error += result.stderr
            execution_success = result.returncode == 0
            
        elif ext == '.java':
            # Java execution
            result = subprocess.run([run_cmd, basename], 
                                  capture_output=True, text=True, timeout=30)
            output += result.stdout
            if result.stderr:
                error += result.stderr
            execution_success = result.returncode == 0
            
        elif ext in ['.cpp', '.c', '.rs']:
            # Compiled executable execution
            executable_path = f"./{basename}"
            if os.path.exists(executable_path):
                result = subprocess.run([executable_path], 
                                      capture_output=True, text=True, timeout=30)
                output += result.stdout
                if result.stderr:
                    error += result.stderr
                execution_success = result.returncode == 0
            else:
                error += f"Executable {executable_path} not found after compilation."
                
        elif ext == '.cs':
            # C# execution with Mono
            exe_file = basename + '.exe'
            if os.path.exists(exe_file):
                result = subprocess.run([run_cmd, exe_file], 
                                      capture_output=True, text=True, timeout=30)
                output += result.stdout
                if result.stderr:
                    error += result.stderr
                execution_success = result.returncode == 0
            else:
                error += f"Executable {exe_file} not found after compilation."
                
        elif ext == '.go':
            # Go execution
            result = subprocess.run(['go', 'run', filename], 
                                  capture_output=True, text=True, timeout=30)
            output += result.stdout
            if result.stderr:
                error += result.stderr
            execution_success = result.returncode == 0
            
        elif ext == '.rb':
            # Ruby execution
            result = subprocess.run([run_cmd, filename], 
                                  capture_output=True, text=True, timeout=30)
            output += result.stdout
            if result.stderr:
                error += result.stderr
            execution_success = result.returncode == 0
            
        elif ext == '.php':
            # PHP execution
            result = subprocess.run([run_cmd, filename], 
                                  capture_output=True, text=True, timeout=30)
            output += result.stdout
            if result.stderr:
                error += result.stderr
            execution_success = result.returncode == 0
            
        success = execution_success
        
    except subprocess.TimeoutExpired:
        error += "Execution timed out (30 seconds limit)."
    except Exception as e:
        error += f"Execution error: {str(e)}"
    finally:
        os.chdir(original_dir)
    
    return output, error, success

class CodingAgentApp(App):
    CSS_PATH = None
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "reload_key", "Reload API Key"),
        ("ctrl+c", "cancel_operation", "Cancel Current Operation"),
    ]

    agent = None  # Will be initialized after key check
    attempts = reactive(0)
    max_attempts = reactive(5)
    max_json_retries = reactive(3)
    feedback = reactive("")
    project_files = reactive([])
    chat_history = reactive([])
    task_prompt = reactive("")
    main_output = reactive("")
    error_output = reactive("")
    api_key_valid = reactive(False)
    operation_in_progress = reactive(False)
    current_operation = reactive("")
    detected_language = reactive("None")
    main_file = reactive("")
    compilation_status = reactive("Not attempted")
    
    # Threading components
    executor = None
    current_task_future = None
    cancel_event = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="left", classes="panel"):
                yield Static("API Key Status: Checking...", id="api_status")
                yield Static("Detected Language: None", id="language_status")
                yield Static("Main File: None", id="main_file_status")
                yield Static("Compilation: Not attempted", id="compilation_status")
                yield Static("Configuration", id="config_label")
                yield Static("Max AI Attempts:", id="max_attempts_label")
                yield Select([("3", 3), ("5", 5), ("10", 10), ("15", 15)], value=5, id="max_attempts_select")
                yield Static("Max JSON Parse Retries:", id="max_json_label")
                yield Select([("1", 1), ("3", 3), ("5", 5), ("10", 10)], value=3, id="max_json_select")
                yield Static("Attempts: 0/0", id="attempts")
                yield Static("Task:", id="task_label")
                yield Input(placeholder="Enter a coding task...", id="task_input")
                yield Button("Start", id="start_btn")
                yield Static("", id="operation_status")
                yield Static("", id="output")
                yield Static("", id="error")
                yield Static("", id="feedback_display")
                yield Input(placeholder="Feedback or reprompt...", id="feedback_input")
                yield Button("Submit Feedback", id="feedback_btn")
                yield Button("Reload API Key", id="reload_btn")
                yield Button("Mark Complete", id="complete_btn")
            with Vertical(id="right", classes="panel"):
                yield Static("Project Structure:", id="proj_struct")
                yield Log(id="tree", highlight=True)
                yield Static("Chat History (Last 2 Messages):", id="chat_label")
                yield Log(id="chat", highlight=True)
        yield Footer()

    def on_mount(self):
        # Initialize thread pool
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.cancel_event = threading.Event()
        
        self.check_and_initialize_api()
        self.main_output = ""
        self.error_output = ""
        self.update_ui()
        self.query_one("#feedback_input", Input).display = False
        self.query_one("#feedback_btn", Button).display = False
        self.query_one("#complete_btn", Button).display = False

    def check_and_initialize_api(self):
        """Check for API key and initialize agent if available"""
        if check_api_key():
            self.api_key_valid = True
            # Initialize with default values
            self.max_attempts = 5
            self.max_json_retries = 3
            self.agent = LLMCodingAgent(max_attempts=self.max_attempts)
            self.query_one("#api_status", Static).update("[bold green]API Key: ✓ Valid[/bold green]")
            self.query_one("#task_input", Input).disabled = False
            self.query_one("#start_btn", Button).disabled = False
            self.query_one("#max_attempts_select", Select).disabled = False
            self.query_one("#max_json_select", Select).disabled = False
        else:
            self.api_key_valid = False
            self.agent = None
            self.query_one("#api_status", Static).update("[bold red]API Key: ✗ Missing[/bold red]")
            self.query_one("#task_input", Input).disabled = True
            self.query_one("#start_btn", Button).disabled = True
            self.query_one("#max_attempts_select", Select).disabled = True
            self.query_one("#max_json_select", Select).disabled = True
            
            # Show instructions in the tree area
            instructions = get_env_file_instructions()
            self.query_one("#tree", Log).clear()
            for line in instructions.split('\n'):
                if line.strip():
                    self.query_one("#tree", Log).write(line)

    def action_reload_key(self):
        """Action to reload API key"""
        self.check_and_initialize_api()
        if self.api_key_valid:
            self.notify("API key loaded successfully!", severity="information")
        else:
            self.notify("API key not found. Check your .env file.", severity="error")

    def action_cancel_operation(self):
        """Cancel current operation"""
        if self.operation_in_progress:
            self.cancel_event.set()
            self.operation_in_progress = False
            self.current_operation = "Cancelling operation..."
            self.update_ui()
            
            # Cancel the future if it exists
            if self.current_task_future and not self.current_task_future.done():
                self.current_task_future.cancel()
            
            self.notify("Operation cancelled", severity="warning")
            self.current_operation = "Operation cancelled by user"
            self.update_ui()

    def call_llm_threaded(self, model, chat_history, max_tokens, timeout=30):
        """Threaded LLM call that respects cancellation"""
        if self.cancel_event.is_set():
            return None, "Operation cancelled"
            
        try:
            response = LLMUtils.call_llm(model, chat_history, max_tokens)
            if self.cancel_event.is_set():
                return None, "Operation cancelled"
            return response, None
        except Exception as e:
            return None, str(e)

    def update_language_detection(self, files):
        """Update language detection based on generated files"""
        if not files:
            self.detected_language = "None"
            self.main_file = ""
            self.compilation_status = "Not attempted"
            return
        
        # Detect main file
        main_file = detect_main_file(files)
        self.main_file = main_file or "No executable file found"
        
        # Get language info
        if main_file:
            lang_name, lang_ext, is_executable, compile_cmd, run_cmd = get_language_info(main_file)
            self.detected_language = lang_name
            
            # Check compilation requirements
            if compile_cmd:
                if check_compiler_available(compile_cmd):
                    self.compilation_status = f"Compiler available: {compile_cmd}"
                else:
                    self.compilation_status = f"Compiler missing: {compile_cmd}"
            else:
                self.compilation_status = "No compilation needed"
        else:
            # If no main file, show the most common language in the project
            extensions = {}
            for f in files:
                ext = os.path.splitext(f['filename'])[1].lower()
                extensions[ext] = extensions.get(ext, 0) + 1
            
            if extensions:
                most_common_ext = max(extensions.keys(), key=extensions.get)
                lang_name, _, _, _, _ = get_language_info("dummy" + most_common_ext)
                self.detected_language = f"{lang_name} (No main file)"
            else:
                self.detected_language = "Mixed/Unknown"
            
            self.compilation_status = "No main file detected"

    def update_ui(self):
        if not self.api_key_valid or not self.agent:
            return
            
        self.query_one("#attempts", Static).update(f"Attempts: {self.agent.attempts}/{self.agent.max_attempts}")
        self.query_one("#output", Static).update(f"[bold green]Output:[/bold green] {self.main_output}")
        self.query_one("#error", Static).update(f"[bold red]Error:[/bold red] {self.error_output}")
        self.query_one("#feedback_display", Static).update(f"[bold yellow]Feedback:[/bold yellow] {self.feedback}")
        self.query_one("#operation_status", Static).update(f"[bold blue]Status:[/bold blue] {self.current_operation}")
        self.query_one("#language_status", Static).update(f"[bold cyan]Detected Language:[/bold cyan] {self.detected_language}")
        self.query_one("#main_file_status", Static).update(f"[bold magenta]Main File:[/bold magenta] {self.main_file}")
        self.query_one("#compilation_status", Static).update(f"[bold white]Compilation:[/bold white] {self.compilation_status}")
        
        # Enhanced Tree with ASCII art
        self.query_one("#tree", Log).clear()
        if self.agent.project_files:
            tree_lines = ascii_tree(self.agent.project_files)
            for line in tree_lines:
                self.query_one("#tree", Log).write(line)
        else:
            self.query_one("#tree", Log).write("No project files yet...")
            
        # Enhanced Chat History (last 2 messages like main.py)
        self.query_one("#chat", Log).clear()
        recent_messages = self.agent.chat_history[-2:] if len(self.agent.chat_history) >= 2 else self.agent.chat_history
        for m in recent_messages:
            color = "cyan" if m["role"] == "user" else "magenta"
            # Truncate long messages for display
            content = m['content'][:200].replace('\n', ' ')
            if len(m['content']) > 200:
                content += "..."
            self.query_one("#chat", Log).write(str(Text(f"{m['role']}: {content}", style=color)))

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle configuration changes"""
        if event.select.id == "max_attempts_select":
            self.max_attempts = event.value
            if self.agent:
                self.agent.max_attempts = event.value
                self.update_ui()
        elif event.select.id == "max_json_select":
            self.max_json_retries = event.value

    def process_task_threaded(self, task):
        """Threaded task processing that updates UI via call_from_thread"""
        if not task.strip():
            self.call_from_thread(self.notify, "Please enter a coding task!", severity="warning")
            return

        # Clear cancel event
        self.cancel_event.clear()
        
        # Initialize task
        self.agent.task_prompt = task
        self.agent.project_folder = safe_project_name(task)
        self.agent.get_task()
        
        # Update UI from thread
        self.call_from_thread(self._update_operation_status, "Initializing task...")

        # Main processing loop
        while self.agent.attempts < self.agent.max_attempts and not self.cancel_event.is_set():
            self.agent.attempts += 1
            self.call_from_thread(
                self._update_operation_status, 
                f"Attempt {self.agent.attempts}: Calling LLM... (UI remains responsive)"
            )

            try:
                max_tokens = self.agent.estimate_max_tokens()
                llm_response, llm_error = self.call_llm_threaded(
                    self.agent.model, 
                    self.agent.chat_history, 
                    max_tokens, 
                    timeout=30
                )

                if self.cancel_event.is_set():
                    break

                if llm_error:
                    self.call_from_thread(self._update_error, f"LLM API error: {llm_error}")
                    self.call_from_thread(self._update_operation_status, "LLM API error occurred")
                    break

                if llm_response is None:
                    self.call_from_thread(self._update_error, "LLM API returned no response")
                    self.call_from_thread(self._update_operation_status, "No response from LLM")
                    break

            except Exception as e:
                self.call_from_thread(self._update_error, f"LLM API error: {str(e)}")
                self.call_from_thread(self._update_operation_status, "LLM API error occurred")
                break

            # Parse files with retry logic
            self.call_from_thread(self._update_operation_status, "Parsing files...")
            
            try:
                files = self.agent.parse_files(llm_response, max_prompt_attempts=self.max_json_retries)
                if self.cancel_event.is_set():
                    break
            except Exception as e:
                self.call_from_thread(self._update_error, f"JSON parse error: {str(e)}")
                self.call_from_thread(self._update_operation_status, "JSON parsing failed")
                break

            if not files:
                self.call_from_thread(self._update_error, "No files generated")
                self.call_from_thread(self._update_operation_status, "No files generated")
                break

            self.agent.project_files = files
            
            # Update language detection
            self.call_from_thread(self._update_language_detection, files)
            self.call_from_thread(self.update_ui)

            # Write and execute files
            self.call_from_thread(self._update_operation_status, "Writing files and compiling/executing...")
            
            try:
                LLMUtils.write_files(files, project_folder=self.agent.project_folder)
                
                # Auto-detect main file
                main_file = detect_main_file(files)
                
                if main_file and not self.cancel_event.is_set():
                    run_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ai_projects', self.agent.project_folder))
                    main_path = os.path.join(run_dir, main_file)
                    
                    # Check if file is executable
                    _, _, is_executable, _, _ = get_language_info(main_file)
                    
                    if is_executable:
                        try:
                            output, error, success = compile_and_run_code(main_path, run_dir)
                            
                            if success:
                                self.call_from_thread(self._update_compilation_status, "✓ Compilation/Execution successful")
                            else:
                                self.call_from_thread(self._update_compilation_status, "✗ Compilation/Execution failed")
                                
                            self.call_from_thread(self._update_outputs, 
                                                output if output else "(no output)",
                                                error if error else "")
                        except Exception as e:
                            self.call_from_thread(self._update_error, f"Code execution error: {str(e)}")
                            self.call_from_thread(self._update_compilation_status, "✗ Execution error")
                    else:
                        self.call_from_thread(self._update_outputs, "", f"File {main_file} is not executable")
                        self.call_from_thread(self._update_compilation_status, "Not executable")
                else:
                    self.call_from_thread(self._update_outputs, "", "No main file detected")
                    self.call_from_thread(self._update_compilation_status, "No main file")

            except Exception as e:
                self.call_from_thread(self._update_error, f"File processing error: {str(e)}")
                self.call_from_thread(self._update_compilation_status, "✗ Processing error")

            # Evaluate output and generate feedback
            if not self.cancel_event.is_set():
                success, feedback = self.agent.evaluate_output(self.main_output, self.error_output)
                self.call_from_thread(self._update_feedback, feedback)
                self.call_from_thread(self._update_operation_status, "Task iteration complete")

                # Show feedback controls
                self.call_from_thread(self._show_feedback_controls)
            break

        # Final status update
        if not self.cancel_event.is_set():
            if self.agent.attempts >= self.agent.max_attempts:
                self.call_from_thread(self._update_operation_status, "Maximum attempts reached")
            else:
                self.call_from_thread(self._update_operation_status, "Ready for feedback")
        
        self.call_from_thread(self._task_completed)

    def _update_operation_status(self, status):
        """Helper to update operation status from thread"""
        self.current_operation = status
        self.update_ui()

    def _update_error(self, error):
        """Helper to update error from thread"""
        self.error_output = error
        self.update_ui()

    def _update_outputs(self, output, error):
        """Helper to update outputs from thread"""
        self.main_output = output
        self.error_output = error
        self.update_ui()

    def _update_feedback(self, feedback):
        """Helper to update feedback from thread"""
        self.feedback = feedback
        self.update_ui()

    def _update_language_detection(self, files):
        """Helper to update language detection from thread"""
        self.update_language_detection(files)

    def _update_compilation_status(self, status):
        """Helper to update compilation status from thread"""
        self.compilation_status = status
        self.update_ui()

    def _show_feedback_controls(self):
        """Helper to show feedback controls from thread"""
        self.query_one("#feedback_input", Input).display = True
        self.query_one("#feedback_btn", Button).display = True
        self.query_one("#complete_btn", Button).display = True

    def _task_completed(self):
        """Helper to mark task as completed from thread"""
        self.operation_in_progress = False
        self.current_task_future = None
        self.update_ui()

    async def process_task(self, task):
        """Process the main coding task with threading"""
        if self.operation_in_progress:
            self.notify("Operation already in progress!", severity="warning")
            return

        self.operation_in_progress = True
        self.current_operation = "Starting..."
        self.update_ui()

        # Submit task to thread pool
        try:
            self.current_task_future = self.executor.submit(self.process_task_threaded, task)
        except Exception as e:
            self.operation_in_progress = False
            self.error_output = f"Failed to start task: {str(e)}"
            self.update_ui()

    def process_feedback_threaded(self, feedback):
        """Threaded feedback processing"""
        # Clear cancel event
        self.cancel_event.clear()
        
        self.call_from_thread(self._update_operation_status, "Processing feedback...")
        
        # Check if this is a specific file fix request
        if "fix" in feedback.lower() or "update" in feedback.lower():
            # Advanced feedback processing
            self.agent.chat_history.append({"role": "assistant", "content": json.dumps({"files": self.agent.project_files})})
            self.agent.chat_history.append({
                "role": "user",
                "content": f"Please address this feedback and update the relevant files:\n{feedback}\nReturn the full JSON manifest for all files."
            })
        else:
            # Standard feedback processing
            self.agent.update_prompt(feedback)
        
        self.call_from_thread(self._update_feedback, feedback)

        # Process the feedback
        try:
            max_tokens = self.agent.estimate_max_tokens()
            llm_response, llm_error = self.call_llm_threaded(
                self.agent.model, 
                self.agent.chat_history, 
                max_tokens, 
                timeout=30
            )

            if self.cancel_event.is_set():
                return

            if llm_error:
                self.call_from_thread(self._update_error, f"LLM API error: {llm_error}")
                return

            if llm_response is None:
                self.call_from_thread(self._update_error, "LLM API returned no response")
                return

            # Parse and process files
            files = self.agent.parse_files(llm_response, max_prompt_attempts=self.max_json_retries)
            if self.cancel_event.is_set():
                return
                
            self.agent.project_files = files
            
            # Update language detection
            self.call_from_thread(self._update_language_detection, files)
            self.call_from_thread(self.update_ui)
            
            # Write and execute files
            self.call_from_thread(self._update_operation_status, "Writing files and compiling/executing...")
            
            LLMUtils.write_files(files, project_folder=self.agent.project_folder)
            
            # Auto-detect main file
            main_file = detect_main_file(files)
            
            if main_file and not self.cancel_event.is_set():
                run_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ai_projects', self.agent.project_folder))
                main_path = os.path.join(run_dir, main_file)
                
                # Check if file is executable
                _, _, is_executable, _, _ = get_language_info(main_file)
                
                if is_executable:
                    try:
                        output, error, success = compile_and_run_code(main_path, run_dir)
                        
                        if success:
                            self.call_from_thread(self._update_compilation_status, "✓ Compilation/Execution successful")
                        else:
                            self.call_from_thread(self._update_compilation_status, "✗ Compilation/Execution failed")
                        
                        self.call_from_thread(self._update_outputs, 
                                            output if output else "(no output)",
                                            error if error else "")
                    except Exception as e:
                        self.call_from_thread(self._update_error, f"Code execution error: {str(e)}")
                        self.call_from_thread(self._update_compilation_status, "✗ Execution error")
                else:
                    self.call_from_thread(self._update_outputs, "", f"File {main_file} is not executable")
                    self.call_from_thread(self._update_compilation_status, "Not executable")
            else:
                self.call_from_thread(self._update_outputs, "", "No main file detected")
                self.call_from_thread(self._update_compilation_status, "No main file")

        except Exception as e:
            self.call_from_thread(self._update_error, f"Processing error: {str(e)}")
            self.call_from_thread(self._update_compilation_status, "✗ Processing error")

        if not self.cancel_event.is_set():
            self.call_from_thread(self._update_operation_status, "Feedback processed")
            self.call_from_thread(self._clear_feedback_input)
        
        self.call_from_thread(self._task_completed)

    def _clear_feedback_input(self):
        """Helper to clear feedback input from thread"""
        self.query_one("#feedback_input", Input).value = ""

    async def _process_feedback(self, feedback):
        """Process feedback with threading"""
        if self.operation_in_progress:
            self.notify("Operation already in progress!", severity="warning")
            return

        self.operation_in_progress = True
        
        # Submit feedback processing to thread pool
        try:
            self.current_task_future = self.executor.submit(self.process_feedback_threaded, feedback)
        except Exception as e:
            self.operation_in_progress = False
            self.error_output = f"Failed to process feedback: {str(e)}"
            self.update_ui()

    async def on_button_pressed(self, event):
        if not self.api_key_valid:
            self.notify("Please set up your API key first!", severity="error")
            return
            
        if event.button.id == "reload_btn":
            self.action_reload_key()
            return
            
        if event.button.id == "complete_btn":
            # Cancel any ongoing operation
            if self.operation_in_progress:
                self.action_cancel_operation()
            
            self.current_operation = "Task marked complete by user"
            self.operation_in_progress = False
            self.query_one("#feedback_input", Input).display = False
            self.query_one("#feedback_btn", Button).display = False
            self.query_one("#complete_btn", Button).display = False
            self.update_ui()
            self.notify("Task marked as complete!", severity="information")
            return
            
        if event.button.id == "start_btn":
            task = self.query_one("#task_input", Input).value
            await self.process_task(task)
            
        elif event.button.id == "feedback_btn":
            feedback = self.query_one("#feedback_input", Input).value
            if not feedback.strip():
                self.notify("Please enter feedback!", severity="warning")
                return
            await self._process_feedback(feedback)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if not self.api_key_valid:
            self.notify("Please set up your API key first!", severity="error")
            return
            
        if event.input.id == "task_input":
            task = event.value
            await self.process_task(task)
            
        elif event.input.id == "feedback_input":
            feedback = event.value
            if not feedback.strip():
                self.notify("Please enter feedback!", severity="warning")
                return
            await self._process_feedback(feedback)

    def on_unmount(self):
        """Clean up resources when app closes"""
        if self.cancel_event:
            self.cancel_event.set()
        if self.executor:
            self.executor.shutdown(wait=False)

def main():
    """Main function with startup checks"""
    # Check if python-dotenv is available
    try:
        import dotenv
    except ImportError:
        print("Error: python-dotenv is required but not installed.")
        print("Please install it with: pip install python-dotenv")
        return
    
    # Check if .env file exists, if not create a template
    if not os.path.exists('.env'):
        print("No .env file found. Creating template...")
        with open('.env', 'w') as f:
            f.write("# Add your API key here\n")
            f.write("# Choose one of the following based on your LLM provider:\n")
            f.write("# OPENAI_API_KEY=your_openai_api_key_here\n")
            f.write("# ANTHROPIC_API_KEY=your_anthropic_api_key_here\n")
            f.write("# API_KEY=your_api_key_here\n")
        print("Created .env template. Please add your API key and restart the application.")
        return
    
    # Run the app
    CodingAgentApp().run()

if __name__ == "__main__":
    main()