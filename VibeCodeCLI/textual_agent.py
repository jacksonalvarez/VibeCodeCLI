from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, Button, Log, TabbedContent, TabPane, DataTable, Label, Rule
from textual.containers import Horizontal, Vertical, ScrollableContainer, Container
from textual.reactive import reactive
from textual import events
from textual.events import Key, Paste
from rich.tree import Tree
from rich.text import Text
from rich.console import Console

# Core imports - will be moved to core/ directory
from agent import LLMCodingAgent
from llm_utils import LLMUtils
from language import get_handler
from master_monitoring import MasterMonitoring

# Simple feature import - just one file!
try:
    from simple_analyzer import analyze_project_files, format_analysis_for_display
    SIMPLE_ANALYZER_AVAILABLE = True
except ImportError:
    print("Warning: Simple analyzer not available")
    SIMPLE_ANALYZER_AVAILABLE = False

import os
import re
import json
import threading
import time
import asyncio
import subprocess
import shutil
import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import textwrap

# Optional import for clipboard support
try:
    import pyperclip
except ImportError:
    pyperclip = None

# Initialize global monitoring instance for LLMUtils integration
try:
    _global_monitor = MasterMonitoring()
    from llm_utils import LLMUtils
    LLMUtils._monitor_instance = _global_monitor
    print("Global monitoring integration established")
except Exception as e:
    print(f"Warning: Could not establish global monitoring: {e}")
    _global_monitor = None

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
        os.getenv('LLM_API_KEY') or 
        os.getenv('OPENAI_API_KEY') or 
        os.getenv('ANTHROPIC_API_KEY') or 
        os.getenv('API_KEY')
    )
    
    return api_key is not None and api_key.strip() != ""

def get_env_file_instructions():
    """Return instructions for setting up the environment file"""
    return """
API Key Required!

To use this coding agent, you need to create a .env file in the project directory with your API key.

Steps:
1. Create a file named .env in the same directory as this script
2. Add one of the following lines (depending on your LLM provider):

   LLM_API_KEY=your_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   API_KEY=your_api_key_here

3. Save the file and restart the application

Example .env file:
# .env file content
LLM_API_KEY=sk-proj-abcd1234...
# or
OPENAI_API_KEY=sk-proj-abcd1234...
# or
ANTHROPIC_API_KEY=sk-ant-api03-abcd1234...

Note: Never commit your .env file to version control!
Add .env to your .gitignore file.
"""

def ascii_tree(files):
    """Generate a clean ASCII tree structure from files list"""
    from collections import defaultdict
    import os
    
    if not files:
        return ["No project files yet..."]
    
    # Build directory structure
    tree = defaultdict(list)
    all_paths = set()
    
    for f in files:
        filename = f['filename']
        parts = filename.split('/')
        
        # Add all directory paths
        for i in range(len(parts)):
            path = '/'.join(parts[:i+1])
            all_paths.add(path)
            
            if i > 0:
                parent = '/'.join(parts[:i])
                tree[parent].append(parts[i])
    
    # Get file extension indicators
    def get_file_indicator(filename):
        ext = os.path.splitext(filename)[1].lower()
        indicators = {
            '.py': '[PY]',
            '.js': '[JS]', 
            '.ts': '[TS]',
            '.html': '[HTML]',
            '.css': '[CSS]',
            '.json': '[JSON]',
            '.md': '[MD]',
            '.txt': '[TXT]',
            '.java': '[JAVA]',
            '.cpp': '[CPP]',
            '.c': '[C]',
            '.cs': '[C#]',
            '.go': '[GO]',
            '.rs': '[RUST]',
            '.rb': '[RUBY]',
            '.php': '[PHP]',
            '.xml': '[XML]',
            '.yml': '[YAML]',
            '.yaml': '[YAML]',
            '.sh': '[SHELL]',
            '.bat': '[BAT]',
            '.sql': '[SQL]'
        }
        
        # Special filename handling
        name_lower = filename.lower()
        if 'readme' in name_lower:
            return '[README]'
        elif 'license' in name_lower:
            return '[LICENSE]'
        elif 'makefile' in name_lower:
            return '[MAKE]'
        elif 'dockerfile' in name_lower:
            return '[DOCKER]'
        elif name_lower.startswith('.'):
            return '[CONFIG]'
        
        return indicators.get(ext, '[FILE]')
    
    def is_directory(path):
        """Check if path is a directory by seeing if it has children"""
        return path in tree and len(tree[path]) > 0
    
    def build_tree(prefix, path, depth=0, is_last=True):
        lines = []
        
        # Skip root level empty path
        if path == "":
            children = sorted(set(tree.get("", [])))
        else:
            # Get the display name (last part of path)
            display_name = os.path.basename(path) if path else ""
            
            # Choose connector
            if depth == 0:
                connector = ""
                indicator = "[DIR]" if is_directory(path) else get_file_indicator(path)
                lines.append(f"{prefix}{indicator} {display_name}")
            else:
                connector = "└── " if is_last else "├── "
                indicator = "[DIR]" if is_directory(path) else get_file_indicator(path)
                lines.append(f"{prefix}{connector}{indicator} {display_name}")
            
            # Get children for this path
            children = sorted(set(tree.get(path, [])))
        
        # Process children
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            child_path = f"{path}/{child}" if path else child
            
            # Determine prefix for children
            if depth == 0:
                child_prefix = prefix
            else:
                child_prefix = prefix + ("    " if is_last else "│   ")
            
            lines.extend(build_tree(child_prefix, child_path, depth + 1, is_last_child))
        
        return lines
    
    # Start building from root
    result_lines = []
    
    # Add a header with better formatting
    header = "📂 PROJECT STRUCTURE"
    result_lines.append(header)
    result_lines.append("═" * len(header))
    result_lines.append("")  # Empty line for spacing
    
    # Get root level items
    root_items = []
    for f in files:
        first_part = f['filename'].split('/')[0]
        if first_part not in root_items:
            root_items.append(first_part)
    
    root_items.sort()
    
    # Build tree for each root item
    for i, root_item in enumerate(root_items):
        is_last = (i == len(root_items) - 1)
        lines = build_tree("", root_item, 0, is_last)
        result_lines.extend(lines)
    
    # Add footer with file count and better formatting
    file_count = len(files)
    result_lines.append("")  # Empty line before footer
    result_lines.append("─" * 30)
    result_lines.append(f"📊 Total files: {file_count}")
    result_lines.append("🔧 Use 'Analyze Project' for details")
    
    return result_lines

def detect_main_file(files):
    """
    Detect the main executable file from the project files.
    Returns the filename of the main file to execute, or None if no executable file found.
    """
    # Priority order for main files with enhanced detection
    main_file_priorities = {
        'main.py': 100,
        'app.py': 90,
        'run.py': 85,
        'server.py': 88,
        'index.js': 80,
        'main.js': 80,
        'app.js': 75,
        'server.js': 70,
        'index.ts': 78,
        'main.ts': 78,
        'app.ts': 73,
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
        'main.php': 70,
        'manage.py': 85,  # Django
        'wsgi.py': 82,    # WSGI apps
        'asgi.py': 82,    # ASGI apps
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
    
    for filename in filenames:
        ext = os.path.splitext(filename)[1].lower()
        if ext in executable_extensions:
            score = executable_extensions[ext]
            basename = os.path.basename(filename).lower()
            
            # Boost score for files with important keywords in name
            if 'main' in basename:
                score += 25
            elif 'app' in basename:
                score += 20
            elif 'index' in basename:
                score += 15
            elif 'server' in basename:
                score += 18
            elif 'run' in basename:
                score += 16
            elif 'start' in basename:
                score += 14
            
            # Boost for root level files
            if '/' not in filename:
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
    Compile and run code using polymorphic language handlers.
    Returns tuple of (output, error, success)
    """
    import os
    filename = os.path.basename(filepath)
    handler = get_handler(filename)
    if not handler or not handler.is_executable():
        return f"File {filename} is not executable", "", False

    # Compile step
    compile_success, compile_output = handler.compile(filename, project_dir)
    if not compile_success:
        return "", compile_output, False

    # Run step
    run_success, run_output = handler.run(filename, project_dir)
    if run_success:
        return run_output, "", True
    else:
        return "", run_output, False

class CodingAgentApp(App):
    CSS = """
    .panel {
        border: solid #00ff00;
        height: 100%;
        background: #0d1117;
    }
    
    #left {
        width: 50%;
        padding: 1;
        overflow-y: auto;
        height: 100%;
    }
    
    #right {
        width: 50%;
        padding: 1;
        overflow-y: auto;
        height: 100%;
    }
    
    /* Monitoring tab specific styles */
    .monitoring-panel {
        padding: 1;
        background: #0d1117;
        border: solid #30363d;
        margin-bottom: 1;
    }
    
    .metric-card {
        background: #161b22;
        border: solid #30363d;
        padding: 1;
        margin: 1;
    }
    
    .metric-value {
        color: #00ff00;
        text-style: bold;
        text-align: center;
    }
    
    .metric-label {
        color: #c9d1d9;
        text-align: center;
        text-style: italic;
    }
    
    .cost-high {
        color: #ff4444;
        text-style: bold;
    }
    
    .cost-medium {
        color: #ffaa00;
        text-style: bold;
    }
    
    .cost-low {
        color: #00ff00;
        text-style: bold;
    }
    
    DataTable {
        background: #0d1117;
        color: #c9d1d9;
        border: solid #30363d;
    }
    
    TabbedContent {
        background: #0d1117;
    }
    
    TabPane {
        background: #0d1117;
        padding: 1;
    }
    
    .status-good {
        color: #00ff00;
        text-style: bold;
    }
    
    .status-error {
        color: #ff4444;
        text-style: bold;
    }
    
    .status-warning {
        color: #ffaa00;
        text-style: bold;
    }
    
    .status-info {
        color: #00aaff;
        text-style: bold;
    }
    
    .label {
        text-style: bold;
        color: #c9d1d9;
    }
    
    .section-header {
        text-style: bold;
        color: #00ff00;
        background: #161b22;
        padding: 0 1;
        margin-bottom: 1;
        border: solid #30363d;
    }
    
    Button {
        margin: 1;
        min-width: 16;
        border: solid #30363d;
    }
    
    Button.-primary {
        background: #238636;
        color: #ffffff;
        border: solid #2ea043;
    }
    
    Button.-secondary {
        background: #1f6feb;
        color: #ffffff;
        border: solid #388bfd;
    }
    
    Button.-danger {
        background: #da3633;
        color: #ffffff;
        border: solid #f85149;
    }
    
    Button:hover {
        text-style: bold;
    }
    
    Input {
        margin: 1;
        border: solid #30363d;
        background: #0d1117;
        color: #c9d1d9;
    }
    
    Input:focus {
        border: solid #00aaff;
        background: #161b22;
    }
    
    Log {
        border: solid #30363d;
        height: 1fr;
        background: #010409;
        color: #c9d1d9;
    }
    
    #api_status {
        margin-bottom: 1;
        padding: 1;
        border: solid #30363d;
        background: #161b22;
    }
    
    #operation_status {
        background: #161b22;
        padding: 1;
        border: solid #00aaff;
        margin: 1 0;
    }
    
    #tree {
        height: 1fr;
        min-height: 15;
        max-height: 100%;
        background: #010409;
        border: solid #00ff00;
        scrollbar-background: #161b22;
        scrollbar-color: #00ff00;
        scrollbar-corner-color: #00ff00;
        scrollbar-size: 1 1;
        overflow-y: scroll;
        overflow-x: hidden;
    }
    
    #chat {
        height: 1fr;
        min-height: 12;
        max-height: 100%;
        background: #010409;
        border: solid #1f6feb;
        scrollbar-background: #161b22;
        scrollbar-color: #1f6feb;
        scrollbar-corner-color: #1f6feb;
        scrollbar-size: 1 1;
        overflow-y: scroll;
        overflow-x: hidden;
    }
    
    Header {
        background: #161b22;
        color: #00ff00;
    }
    
    Footer {
        background: #161b22;
        color: #c9d1d9;
    }
    
    Static {
        color: #c9d1d9;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "reload_key", "Reload API Key"),
        ("ctrl+c", "cancel_operation", "Cancel Operation"),
        ("ctrl+v", "paste_clipboard", "Paste"),
        ("ctrl+shift+c", "copy_output", "Copy Output"),
        ("ctrl+alt+c", "copy_all", "Copy All Project Data"),
        ("f1", "show_help", "Help"),
        ("f2", "refresh_monitoring", "Refresh Monitoring"),
    ]

    agent = None  # Will be initialized after key check
    monitor = None  # Monitoring system
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
    project_active = reactive(False)  # New reactive for tracking active project
    
    # Monitoring reactive variables
    monitoring_data = reactive({})
    monitoring_enabled = reactive(False)
    
    # Threading components
    executor = None
    current_task_future = None
    cancel_event = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("API Status: Checking...", id="api_status", classes="label")
        
        with TabbedContent():
            with TabPane("Project Creator", id="main_tab"):
                with Horizontal():
                    with Vertical(id="left", classes="panel"):
                        yield Static("Project Creation", classes="section-header")
                        yield Input(placeholder="Describe your project...", id="project_input")
                        yield Button("Create Project", id="create_btn", classes="-primary")
                        
                        yield Static("Operation Status", classes="section-header")
                        yield Static("", id="operation_status", classes="label")
                        yield Static("", id="output", classes="label")
                        yield Static("", id="error", classes="label")
                        
                        yield Static("Feedback", classes="section-header")
                        yield Static("", id="feedback_display", classes="label")
                        yield Input(placeholder="Feedback or reprompt...", id="feedback_input")
                        with Horizontal():
                            yield Button("Submit Feedback", id="feedback_btn", classes="-secondary")
                            yield Button("Use Prompter", id="prompter_btn", classes="-primary")

                        yield Static("Actions", classes="section-header")
                        yield Button("Reload API Key", id="reload_btn", classes="-secondary")
                        yield Button("Mark Complete", id="complete_btn", classes="-primary")
                        yield Button("Analyze Project", id="analyze_btn", classes="-secondary")
                        yield Button("Copy Output", id="copy_output_btn", classes="-secondary")
                        yield Button("Copy All Data", id="copy_all_btn", classes="-secondary")
                        
                    with Vertical(id="right", classes="panel"):
                        yield Static("Project Structure", classes="section-header")
                        yield Log(id="tree", highlight=True)
                        yield Static("Chat History (Recent Messages)", classes="section-header")
                        yield Log(id="chat", highlight=True)
                        yield Static("Project Information", classes="section-header")
                        yield Static("Detected Language: None", id="language_status", classes="label")
                        yield Static("Main File: None", id="main_file_status", classes="label")
                        yield Static("Compilation: Not attempted", id="compilation_status", classes="label")
                        yield Static("Attempts: 0/5", id="attempts", classes="label")
            
            with TabPane("Token Monitor", id="monitoring_tab"):
                with Container(classes="monitoring-panel"):
                    yield Static("Token Usage & Cost Monitoring", classes="section-header")
                    
                    # Real-time metrics row
                    with Horizontal():
                        with Vertical(classes="metric-card"):
                            yield Static("0", id="total_calls_metric", classes="metric-value")
                            yield Static("Total API Calls", classes="metric-label")
                        
                        with Vertical(classes="metric-card"):
                            yield Static("0", id="total_tokens_metric", classes="metric-value")
                            yield Static("Total Tokens", classes="metric-label")
                        
                        with Vertical(classes="metric-card"):
                            yield Static("$0.00", id="total_cost_metric", classes="metric-value")
                            yield Static("Total Cost", classes="metric-label")
                        
                        with Vertical(classes="metric-card"):
                            yield Static("$0.00", id="session_cost_metric", classes="metric-value")
                            yield Static("Session Cost", classes="metric-label")
                    
                    yield Rule()
                    
                    # Simple Controls - Just three buttons as requested
                    with Horizontal():
                        yield Button("Refresh Data", id="refresh_monitoring_btn", classes="-secondary")
                        yield Button("Reset Statistics", id="reset_stats_btn", classes="-danger")
                        yield Button("Generate LaTeX Report", id="generate_report_btn", classes="-primary")
                    
                    yield Rule()
                    
                    # Status and monitoring log
                    yield Static("Monitoring Status", classes="section-header")
                    yield Log(id="monitoring_log", highlight=True)
        
        yield Footer()

    def update_status_display(self, widget_id, label, value, status_type="info"):
        """Update status displays with proper styling"""
        widget = self.query_one(f"#{widget_id}", Static)
        
        # Remove previous status classes
        widget.remove_class("status-good", "status-error", "status-warning", "status-info")
        
        # Set CSS class based on status type
        if status_type == "good":
            widget.add_class("status-good")
        elif status_type == "error":
            widget.add_class("status-error")
        elif status_type == "warning":
            widget.add_class("status-warning")
        else:
            widget.add_class("status-info")
        
        widget.update(f"{label}: {value}")

    def update_project_controls(self):
        """Update project control states based on current project status"""
        if not self.api_key_valid:
            # Disable all project controls if no API key
            self.query_one("#project_input", Input).disabled = True
            self.query_one("#create_btn", Button).disabled = True
            return
            
        if self.project_active:
            # Project is active - disable new project creation
            self.query_one("#project_input", Input).disabled = True
            self.query_one("#create_btn", Button).disabled = True
        else:
            # No active project - enable new project creation
            self.query_one("#project_input", Input).disabled = False
            self.query_one("#create_btn", Button).disabled = False

    def check_and_initialize_api(self):
        """Check for API key and initialize agent if available"""
        if check_api_key():
            self.api_key_valid = True
            # Initialize with default values - wrap in try/catch
            self.max_attempts = 5
            self.max_json_retries = 3
            try:
                self.agent = LLMCodingAgent(max_attempts=self.max_attempts)
                self.update_status_display("api_status", "API Status", "Valid", "good")
                self.update_project_controls()
            except ValueError as e:
                # Handle API key verification error
                self.api_key_valid = False
                self.agent = None
                self.update_status_display("api_status", "API Status", f"Error: {str(e)}", "error")
                self.query_one("#project_input", Input).disabled = True
                self.query_one("#create_btn", Button).disabled = True
                return
        else:
            self.api_key_valid = False
            self.agent = None
            self.update_status_display("api_status", "API Status", "Missing", "error")
            self.query_one("#project_input", Input).disabled = True
            self.query_one("#create_btn", Button).disabled = True
            
            # Show instructions in the tree area
            instructions = get_env_file_instructions()
            tree_log = self.query_one("#tree", Log)
            tree_log.clear()
            
            for line in instructions.split('\n'):
                if line.strip():
                    tree_log.write(line)

    def initialize_monitoring(self):
        """Initialize the monitoring system with enhanced integration"""
        try:
            # Use the enhanced monitoring integration
            success = MonitoringIntegration.setup_monitoring_for_app(self)
            
            if success and self.monitor:
                self.monitoring_enabled = True
                
                # Force an initial update of the monitoring display
                self.update_monitoring_display()
                
                print("Enhanced monitoring system initialized successfully")
                
                # Notify user
                if hasattr(self, 'notify'):
                    self.notify("Enhanced monitoring system initialized", severity="information")
            else:
                print("Failed to initialize enhanced monitoring")
                self.monitor = None
                self.monitoring_enabled = False
                
                if hasattr(self, 'notify'):
                    self.notify("Warning: Monitoring system failed to initialize", severity="warning")
                
        except Exception as e:
            print(f"Error initializing enhanced monitoring: {e}")
            self.monitor = None
            self.monitoring_enabled = False
            
            # Notify user of error
            if hasattr(self, 'notify'):
                self.notify(f"Error initializing monitoring: {str(e)}", severity="error")

    def test_monitoring_integration(self):
        """Test the monitoring system integration"""
        try:
            if not self.monitoring_enabled or not self.monitor:
                return False
            
            # Test basic monitoring functionality
            if hasattr(self.monitor, 'get_metrics'):
                metrics = self.monitor.get_metrics()
                return metrics is not None
            
            return True
        except Exception as e:
            print(f"Error testing monitoring integration: {e}")
            return False

    def setup_monitoring_with_callback(self):
        """Enhanced monitoring setup with real-time callback"""
        try:
            if self.monitor:
                self.monitor.set_callback(self.on_monitoring_update)
        except Exception as e:
            print(f"Error setting up monitoring callback: {e}")

    def on_monitoring_update(self, monitoring_summary):
        """Callback method for real-time monitoring updates"""
        try:
            self.call_from_thread(self._update_monitoring_from_callback, monitoring_summary)
        except Exception as e:
            print(f"Error in monitoring update callback: {e}")

    def _update_monitoring_from_callback(self, summary):
        """Thread-safe monitoring update method with better error handling"""
        try:
            # Update session metrics if elements exist
            session = summary.get('session', {})
            if session:
                try:
                    self.query_one("#total_calls_metric", Static).update(f"{session.get('total_calls', 0):,}")
                    self.query_one("#total_tokens_metric", Static).update(f"{session.get('total_tokens', 0):,}")
                    self.query_one("#total_cost_metric", Static).update(f"${session.get('total_cost', 0):.4f}")
                    self.query_one("#session_cost_metric", Static).update(f"${session.get('session_cost', 0):.4f}")
                except Exception as e:
                    print(f"Error updating session metrics: {e}")
            
            # Update monitoring log (simplified - no tables)
            try:
                log = self.query_one("#monitoring_log", Log)
                log.clear()
                if hasattr(self.monitor, 'format_ui_summary'):
                    summary_lines = self.monitor.format_ui_summary()
                    for line in summary_lines:
                        log.write(line)
                else:
                    # Fallback summary
                    log.write(f"Total API Calls: {session.get('total_calls', 0)}")
                    log.write(f"Total Tokens: {session.get('total_tokens', 0):,}")
                    log.write(f"Total Cost: ${session.get('total_cost', 0):.4f}")
                    log.write("Monitoring system active")
            except Exception as e:
                print(f"Error updating monitoring log: {e}")
                
        except Exception as e:
            print(f"Error updating monitoring from callback: {e}")

    def update_monitoring_display(self):
        """Update the monitoring display with current data"""
        if not self.monitor:
            print("No monitor available for update")
            return
        try:
            # Try different methods based on what's available
            if hasattr(self.monitor, 'get_ui_summary'):
                summary = self.monitor.get_ui_summary()
            elif hasattr(self.monitor, 'get_session_summary'):
                # For MasterMonitoring, use get_session_summary and format it
                session_data = self.monitor.get_session_summary()
                recent_calls = []
                model_usage = {}
                
                # Try to get additional data if available
                if hasattr(self.monitor, 'get_real_time_metrics'):
                    metrics = self.monitor.get_real_time_metrics()
                    recent_calls = metrics.get('recent_calls', [])
                    model_usage = metrics.get('model_usage', {})
                
                summary = {
                    'session': session_data,
                    'recent_calls': recent_calls,
                    'model_usage': model_usage
                }
            else:
                # Create a basic summary
                summary = {
                    'session': {'total_calls': 0, 'total_tokens': 0, 'total_cost': 0.0, 'session_cost': 0.0},
                    'recent_calls': [],
                    'model_usage': {}
                }
                
            self._update_monitoring_from_callback(summary)
            print("Monitoring display updated successfully")
        except Exception as e:
            print(f"Error updating monitoring display: {e}")
            # Try to show some basic info even if monitoring fails
            try:
                log = self.query_one("#monitoring_log", Log)
                log.clear()
                log.write("Monitoring system encountered an error")
                log.write(f"Error: {str(e)}")
                log.write("Please check console for details")
            except:
                pass

    async def process_task(self, task):
        """Process task with error handling"""
        if not self.api_key_valid or not self.agent:
            self.notify("API key not available! Please check your .env file.", severity="error")
            return
        
        if self.operation_in_progress:
            self.notify("Operation already in progress!", severity="warning")
            return

        if self.project_active:
            self.notify("Please complete the current project first!", severity="warning")
            return

        try:
            self.operation_in_progress = True
            self.current_operation = "Starting project..."
            self.update_ui()
            # Submit task processing to thread pool
            self.current_task_future = self.executor.submit(self.process_task_threaded, task)
        except Exception as e:
            self.operation_in_progress = False
            self.error_output = f"Failed to start project: {str(e)}"
            self.current_operation = "Project failed to start"
            self.update_ui()
            self.notify(f"Error starting project: {str(e)}", severity="error")
        finally:
            # Always refresh monitoring after a prompt
            self.update_monitoring_display()

    async def _process_feedback(self, feedback):
        """Process feedback with error handling"""
        if not self.api_key_valid or not self.agent:
            self.notify("API key not available! Please check your .env file.", severity="error")
            return
        
        if self.operation_in_progress:
            self.notify("Operation is already in progress. Please wait.", severity="warning")
            return

        self.operation_in_progress = True
        try:
            self.current_operation = "Processing feedback..."
            self.update_ui()
            # Submit feedback processing to thread pool
            self.current_task_future = self.executor.submit(self.process_feedback_threaded, feedback)
        except Exception as e:
            self.operation_in_progress = False
            self.error_output = f"Failed to process feedback: {str(e)}"
            self.current_operation = "Feedback processing failed"
            self.update_ui()
            self.notify(f"Error processing feedback: {str(e)}", severity="error")
        finally:
            # Always refresh monitoring after feedback
            self.update_monitoring_display()
            self.operation_in_progress = False

    async def on_button_pressed(self, event):
        """Handle button press events with better error handling"""
        try:
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
                
                # Mark project as complete and reset state
                self.project_active = False
                self.current_operation = "Project marked complete by user"
                self.operation_in_progress = False
                
                # Hide feedback controls
                self.query_one("#feedback_input", Input).display = False
                self.query_one("#feedback_btn", Button).display = False
                self.query_one("#complete_btn", Button).display = False
                
                # Clear the project input for next project
                self.query_one("#project_input", Input).value = ""
                
                # Update controls to allow new project creation
                self.update_project_controls()
                self.update_ui()
                
                self.notify("Project marked as complete! You can now start a new project.", severity="information")
                return
                
            if event.button.id == "create_btn":
                if self.project_active:
                    self.notify("Please complete the current project first!", severity="warning")
                    return
                    
                task = self.query_one("#project_input", Input).value.strip()
                if not task:
                    self.notify("Please enter a project description!", severity="warning")
                    return
                    
                print(f"DEBUG: About to process task: '{task}'")  # Debug output
                await self.process_task(task)
                
            elif event.button.id == "feedback_btn":
                feedback = self.query_one("#feedback_input", Input).value.strip()
                if not feedback:
                    self.notify("Please enter feedback!", severity="warning")
                    return
                await self._process_feedback(feedback)
                
            elif event.button.id == "copy_output_btn":
                self.action_copy_output()
                
            elif event.button.id == "copy_all_btn":
                self.action_copy_all()
                
            elif event.button.id == "analyze_btn":
                self.action_analyze_project()
                
            # Monitoring actions
            elif event.button.id == "refresh_monitoring_btn":
                self.action_refresh_monitoring()
                
            elif event.button.id == "generate_report_btn":
                await self.action_generate_report()
                
            elif event.button.id == "reset_stats_btn":
                await self.action_reset_stats()
                
            # New prompter action
            elif event.button.id == "prompter_btn":
                await self.action_use_prompter()
                
        except Exception as e:
            self.notify(f"Button handler error: {str(e)}", severity="error")
            print(f"DEBUG: Button handler exception: {e}")  # Debug output

    async def on_input_submitted(self, event):
        """Handle input submission (Enter key) with error handling"""
        try:
            if event.input.id == "project_input":
                if self.project_active:
                    self.notify("Please complete the current project first!", severity="warning")
                    return
                task = event.input.value.strip()
                if not task:
                    self.notify("Please enter a project description!", severity="warning")
                    return
                print(f"DEBUG: Input submitted task: '{task}'")  # Debug output
                await self.process_task(task)
            elif event.input.id == "feedback_input":
                feedback = event.input.value.strip()
                if not feedback:
                    self.notify("Please enter feedback!", severity="warning")
                    return
                await self._process_feedback(feedback)
        except Exception as e:
            self.notify(f"Input handler error: {str(e)}", severity="error")
            print(f"DEBUG: Input handler exception: {e}")  # Debug output

    def on_mount(self):
        # Initialize thread pool
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.cancel_event = threading.Event()
        
        # Initialize monitoring system
        self.initialize_monitoring()
        
        # Test monitoring integration
        if self.monitoring_enabled:
            test_result = self.test_monitoring_integration()
            print(f"Monitoring integration test result: {test_result}")
        
        # Initialize data tables for monitoring
        self._setup_monitoring_tables()
        
        self.check_and_initialize_api()
        self.main_output = ""
        self.error_output = ""
        self.project_active = False  # Initialize project state
        self.update_ui()
        self.update_monitoring_display()
        self.query_one("#feedback_input", Input).display = False
        self.query_one("#feedback_btn", Button).display = False
        self.query_one("#complete_btn", Button).display = False
        self.query_one("#copy_output_btn", Button).display = True
        self.query_one("#copy_all_btn", Button).display = True

    def update_ui(self):
        """Update all UI elements with current state"""
        try:
            # Update operation status
            if hasattr(self, 'current_operation') and self.current_operation:
                self.query_one("#operation_status", Static).update(f"Status: {self.current_operation}")
            
            # Update output and error displays
            if hasattr(self, 'main_output') and self.main_output:
                self.query_one("#output", Static).update(f"Output: {self.main_output[:100]}{'...' if len(self.main_output) > 100 else ''}")
            else:
                self.query_one("#output", Static).update("")
            
            if hasattr(self, 'error_output') and self.error_output:
                self.query_one("#error", Static).update(f"Error: {self.error_output[:100]}{'...' if len(self.error_output) > 100 else ''}")
            else:
                self.query_one("#error", Static).update("")
            
            # Update feedback display
            if hasattr(self, 'feedback') and self.feedback:
                self.query_one("#feedback_display", Static).update(f"Feedback: {self.feedback[:150]}{'...' if len(self.feedback) > 150 else ''}")
            else:
                self.query_one("#feedback_display", Static).update("")
            
            # Update project information
            if hasattr(self, 'detected_language'):
                self.query_one("#language_status", Static).update(f"Detected Language: {self.detected_language}")
            
            if hasattr(self, 'main_file'):
                self.query_one("#main_file_status", Static).update(f"Main File: {self.main_file}")
            
            if hasattr(self, 'compilation_status'):
                self.query_one("#compilation_status", Static).update(f"Compilation: {self.compilation_status}")
            
            # Update attempts counter
            if hasattr(self, 'agent') and self.agent:
                attempts = getattr(self.agent, 'attempts', 0)
                max_attempts = getattr(self.agent, 'max_attempts', 5)
                self.query_one("#attempts", Static).update(f"Attempts: {attempts}/{max_attempts}")
            
            # Update project structure tree
            if hasattr(self, 'agent') and self.agent and getattr(self.agent, 'project_files', None):
                print(f"DEBUG: Updating project structure with {len(self.agent.project_files)} files")
                tree_log = self.query_one("#tree", Log)
                tree_log.clear()
                
                # Use the new wrapped formatting
                wrapped_tree_lines = format_project_structure_wrapped(self.agent.project_files, width=70)
                print(f"DEBUG: Generated {len(wrapped_tree_lines)} tree lines")
                for line in wrapped_tree_lines:
                    tree_log.write(line)
            else:
                print("DEBUG: No project files to display")
                # Show placeholder when no project is loaded
                try:
                    tree_log = self.query_one("#tree", Log)
                    tree_log.clear()
                    tree_log.write("No project loaded yet...")
                    tree_log.write("Create a project to see its structure here")
                except Exception as e:
                    print(f"DEBUG: Error updating empty tree: {e}")
            
            # Update chat history with proper vertical formatting and wrapping
            if hasattr(self, 'agent') and self.agent and getattr(self.agent, 'chat_history', None):
                print(f"DEBUG: Updating chat history with {len(self.agent.chat_history)} messages")
                chat_log = self.query_one("#chat", Log)
                chat_log.clear()
                
                # Add header with box
                chat_log.write("┌─ 💬 CHAT HISTORY " + "─" * 45 + "┐")
                chat_log.write("│" + " " * 63 + "│")
                
                # Show last few messages with proper wrapping
                recent_messages = self.agent.chat_history[-8:] if len(self.agent.chat_history) > 8 else self.agent.chat_history
                
                for i, msg in enumerate(recent_messages):
                    role = msg['role']
                    content = msg['content']
                    
                    # Use the new wrapped formatting for each message
                    wrapped_msg_lines = format_chat_message_wrapped(role, content, width=65)
                    for line in wrapped_msg_lines:
                        chat_log.write(line)
                
                chat_log.write("└" + "─" * 63 + "┘")
            else:
                print("DEBUG: No chat history to display")
                # Show placeholder when no chat history is available
                try:
                    chat_log = self.query_one("#chat", Log)
                    chat_log.clear()
                    chat_log.write("No chat history yet...")
                    chat_log.write("Start a project to see chat messages here")
                except Exception as e:
                    print(f"DEBUG: Error updating empty chat: {e}")
        except Exception as e:
            print(f"DEBUG: UI update error: {e}")

    def _setup_monitoring_tables(self):
        """Setup monitoring display (simplified - no tables needed)"""
        # Since we simplified the UI, no table setup is needed
        # Just ensure monitoring log is ready
        try:
            log = self.query_one("#monitoring_log", Log)
            log.clear()
            log.write("Monitoring system ready")
        except Exception as e:
            print(f"Error setting up monitoring display: {e}")

    # Add missing helper methods that are called but not defined
    def _set_project_active(self, active):
        """Set project active state"""
        self.project_active = active
        self.update_project_controls()

    def _update_operation_status(self, status):
        """Update operation status"""
        self.current_operation = status
        self.update_ui()

    def _update_error(self, error):
        """Update error output"""
        self.error_output = error
        self.update_ui()

    def _update_outputs(self, output, error):
        """Update both output and error"""
        self.main_output = output
        self.error_output = error
        self.update_ui()

    def _update_compilation_status(self, status):
        """Update compilation status"""
        self.compilation_status = status
        self.update_ui()

    def _update_feedback(self, feedback):
        """Update feedback display"""
        self.feedback = feedback
        self.update_ui()

    def _update_language_detection(self, files):
        """Update detected language and main file"""
        main_file = detect_main_file(files)
        if main_file:
            self.main_file = main_file
            lang_name, _, _, _, _ = get_language_info(main_file)
            self.detected_language = lang_name
        else:
            self.main_file = ""
            self.detected_language = "Unknown"

    def _show_feedback_controls(self):
        """Show feedback input controls"""
        try:
            self.query_one("#feedback_input", Input).display = True
            self.query_one("#feedback_btn", Button).display = True
            self.query_one("#complete_btn", Button).display = True
        except Exception as e:
            print(f"DEBUG: Error showing feedback controls: {e}")

    def _clear_feedback_input(self):
        """Clear feedback input field"""
        try:
            self.query_one("#feedback_input", Input).value = ""
        except Exception as e:
            print(f"DEBUG: Error clearing feedback input: {e}")

    def _task_completed(self):
        """Mark task as completed"""
        self.operation_in_progress = False
        self.update_ui()

    def call_llm_threaded(self, model, chat_history, max_tokens):
        """Call LLM with proper monitoring integration and UI updates"""
        try:
            print(f"Making LLM call with model: {model}")
            
            # Make the LLM call
            response = LLMUtils.call_llm(model, chat_history, max_tokens)
            
            # For fallback monitoring, manually log the call
            if isinstance(self.monitor, FallbackMonitoring):
                # Estimate token usage and cost for fallback monitoring
                estimated_tokens = len(str(chat_history)) // 4 + len(str(response)) // 4
                estimated_cost = estimated_tokens * 0.00001  # Rough estimate
                self.monitor.log_api_call(model, estimated_tokens, estimated_cost)
            
            # Force monitoring update after LLM call
            if self.monitor:
                print("Triggering monitoring update after LLM call")
                try:
                    # Update monitoring display from the thread
                    self.call_from_thread(self.update_monitoring_display)
                except Exception as e:
                    print(f"Error updating monitoring from thread: {e}")
            
            return response, None
        except Exception as e:
            print(f"Error in LLM call: {e}")
            return None, str(e)

    def generate_change_summary(self, old_files, new_files, is_initial):
        """Generate a summary of changes between file versions"""
        if is_initial:
            return f"=== INITIAL PROJECT CREATION ===\n📁 Created {len(new_files)} new files"
        
        if not old_files:
            return f"=== PROJECT UPDATE ===\n📁 Generated {len(new_files)} files"
        
        changes = []
        old_names = {f['filename'] for f in old_files}
        new_names = {f['filename'] for f in new_files}
        
        # New files
        added = new_names - old_names
        if added:
            changes.append(f"➕ Added: {', '.join(sorted(added))}")
        
        # Removed files
        removed = old_names - new_names
        if removed:
            changes.append(f"➖ Removed: {', '.join(sorted(removed))}")
        
        # Modified files
        common_files = old_names & new_names
        modified = []
        for filename in common_files:
            old_content = next(f['content'] for f in old_files if f['filename'] == filename)
            new_content = next(f['content'] for f in new_files if f['filename'] == filename)
            if old_content != new_content:
                modified.append(filename)
        
        if modified:
            changes.append(f"📝 Modified: {', '.join(sorted(modified))}")
        
        if not changes:
            changes.append("🔄 No significant changes detected")
        
        return f"=== CHANGE SUMMARY ===\n" + "\n".join(changes)

    def get_language_name_from_ext(self, ext):
        """Get human-readable language name from file extension"""
        lang_map = {
            '.py': 'Python',
            '.js': 'JavaScript', 
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.html': 'HTML',
            '.css': 'CSS',
            '.json': 'JSON',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.xml': 'XML',
            '.yml': 'YAML',
            '.yaml': 'YAML',
            '.sh': 'Shell',
            '.bat': 'Batch'
        }
        return lang_map.get(ext.lower(), 'Unknown')

    def extract_dependencies(self, content, ext):
        """Extract dependencies from file content based on extension"""
        dependencies = set()
        if ext == '.py':
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    if 'import ' in line and not line.startswith('from .') and not line.startswith('from ..'):
                        parts = line.replace('from ', '').replace('import ', '').split()
                        if parts:
                            pkg = parts[0].split('.')[0]
                            if pkg not in ['os', 'sys', 'json', 're', 'datetime', 'time', 'threading']:
                                dependencies.add(f"Python: {pkg}")
        elif ext == '.js':
            for line in content.split('\n'):
                if 'require(' in line:
                    match = re.search(r"require\(['\"]([^'\"]+)['\"]", line)
                    if match:
                        pkg = match.group(1)
                        if not pkg.startswith('.') and not pkg.startswith('/'):
                            dependencies.add(f"Node.js: {pkg}")
        return dependencies

    # Action methods for monitoring and controls
    def action_reload_key(self):
        """Reload API key"""
        self.check_and_initialize_api()
        self.notify("API key reloaded", severity="information")

    def action_cancel_operation(self):
        """Cancel current operation"""
        if self.cancel_event:
            self.cancel_event.set()
        self.operation_in_progress = False
        self.notify("Operation cancelled", severity="warning")

    def action_copy_output(self):
        """Copy output to clipboard"""
        try:
            output_text = f"Output: {self.main_output}\n\nError: {self.error_output}"
            if pyperclip:
                pyperclip.copy(output_text)
                self.notify("Output copied to clipboard", severity="information")
            else:
                self.notify("pyperclip not installed for clipboard support", severity="warning")
        except Exception as e:
            self.notify(f"Error copying to clipboard: {e}", severity="error")

    def action_copy_all(self):
        """Copy all project data"""
        try:
            all_data = f"Project: {self.task_prompt}\n\nFiles: {len(self.project_files)}\n\nOutput: {self.main_output}\n\nError: {self.error_output}"
            if pyperclip:
                pyperclip.copy(all_data)
                self.notify("All project data copied to clipboard", severity="information")
            else:
                self.notify("pyperclip not installed for clipboard support", severity="warning")
        except Exception as e:
            self.notify(f"Error copying to clipboard: {e}", severity="error")

    def action_refresh_monitoring(self):
        """Refresh monitoring data (responds to F2 key)"""
        try:
            print("Manual monitoring refresh triggered")
            
            # Force a monitoring update if we have a monitor
            if self.monitor:
                print("Monitor available, updating display...")
                self.update_monitoring_display()
                
                # Also try to get fresh data from the monitor
                if hasattr(self.monitor, 'refresh_data'):
                    self.monitor.refresh_data()
                
                self.notify("Monitoring data refreshed manually", severity="information")
            else:
                print("No monitor available, trying to reinitialize...")
                # Try to reinitialize monitoring
                self.initialize_monitoring()
                if self.monitor:
                    self.update_monitoring_display()
                    self.notify("Monitoring system reinitialized and refreshed", severity="information")
                else:
                    self.notify("Monitoring system not available", severity="warning")
                    
        except Exception as e:
            print(f"Error during manual monitoring refresh: {e}")
            self.notify(f"Error refreshing monitoring: {str(e)}", severity="error")

    async def action_generate_report(self):
        """Generate simple LaTeX monitoring report"""
        try:
            if not self.monitor:
                self.notify("Monitoring system not initialized", severity="warning")
                return
                
            self._update_operation_status("Generating LaTeX report...")
            
            # Create a simple LaTeX report directly without complex integration
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"monitoring_report_{timestamp}.tex"
            
            # Get basic monitoring data
            try:
                if hasattr(self.monitor, 'get_session_summary'):
                    session_data = self.monitor.get_session_summary()
                elif hasattr(self.monitor, 'get_ui_summary'):
                    summary = self.monitor.get_ui_summary()
                    session_data = summary.get('session', {})
                else:
                    # Fallback for basic monitoring
                    session_data = {
                        'total_calls': getattr(self.monitor, 'session_data', {}).get('total_calls', 0),
                        'total_tokens': getattr(self.monitor, 'session_data', {}).get('total_tokens', 0),
                        'total_cost': getattr(self.monitor, 'session_data', {}).get('total_cost', 0.0),
                        'session_cost': getattr(self.monitor, 'session_data', {}).get('session_cost', 0.0)
                    }
            except Exception as e:
                print(f"Error getting session data: {e}")
                session_data = {'total_calls': 0, 'total_tokens': 0, 'total_cost': 0.0, 'session_cost': 0.0}
            
            # Generate simple LaTeX content
            latex_content = f"""\\documentclass{{article}}
\\usepackage{{geometry}}
\\usepackage{{booktabs}}
\\usepackage{{amsmath}}
\\geometry{{margin=1in}}

\\title{{LLM Monitoring Report}}
\\author{{LLM Coding Agent}}
\\date{{{datetime.datetime.now().strftime("%B %d, %Y")}}}

\\begin{{document}}
\\maketitle

\\section{{Session Summary}}
This report contains monitoring data for the LLM Coding Agent session.

\\begin{{table}}[h]
\\centering
\\begin{{tabular}}{{lr}}
\\toprule
Metric & Value \\\\
\\midrule
Total API Calls & {session_data.get('total_calls', 0)} \\\\
Total Tokens & {session_data.get('total_tokens', 0):,} \\\\
Total Cost & \\${session_data.get('total_cost', 0):.4f} \\\\
Session Cost & \\${session_data.get('session_cost', 0):.4f} \\\\
\\bottomrule
\\end{{tabular}}
\\caption{{API Usage Statistics}}
\\end{{table}}

\\section{{Report Details}}
\\begin{{itemize}}
\\item Report generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
\\item Monitoring system: {"Active" if self.monitoring_enabled else "Inactive"}
\\item Agent version: LLM Coding Agent v1.0
\\end{{itemize}}

\\end{{document}}"""
            
            # Write the LaTeX file
            try:
                with open(report_filename, 'w', encoding='utf-8') as f:
                    f.write(latex_content)
                
                self._update_operation_status("LaTeX report generated successfully")
                
                # Try to compile to PDF if LaTeX is available
                try:
                    result = subprocess.run(['pdflatex', '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self._update_operation_status("Compiling LaTeX to PDF...")
                        pdf_result = subprocess.run(['pdflatex', report_filename], 
                                                  capture_output=True, text=True, timeout=30)
                        if pdf_result.returncode == 0:
                            self.notify(f"PDF report generated: {report_filename.replace('.tex', '.pdf')}", severity="information")
                        else:
                            self.notify(f"LaTeX report generated: {report_filename} (PDF compilation failed)", severity="warning")
                    else:
                        self.notify(f"LaTeX report generated: {report_filename} (Install LaTeX for PDF)", severity="information")
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    self.notify(f"LaTeX report generated: {report_filename} (Install LaTeX for PDF)", severity="information")
                    
            except Exception as write_error:
                self.notify(f"Error writing LaTeX file: {write_error}", severity="error")
                
        except Exception as e:
            self._update_operation_status("Report generation error")
            self.notify(f"Error generating report: {str(e)}", severity="error")
            print(f"Report generation error: {e}")

    async def action_reset_stats(self):
        """Reset monitoring statistics"""
        try:
            if self.monitor:
                self.monitor.reset_session_stats()
                self.update_monitoring_display()
                self.notify("Session statistics reset", severity="information")
            else:
                self.notify("Monitoring not available", severity="warning")
        except Exception as e:
            self.notify(f"Error resetting stats: {e}", severity="error")

    async def action_use_prompter(self):
        """Use prompter functionality - read prompter.txt and use as feedback or create new project"""
        try:
            if self.operation_in_progress:
                self.notify("Operation already in progress. Please wait.", severity="warning")
                return
            
            # Check if prompter.txt exists
            prompter_file = os.path.join(os.path.dirname(__file__), 'prompter.txt')
            if not os.path.exists(prompter_file):
                self.notify("prompter.txt file not found", severity="error")
                return
            
            # Read the contents of prompter.txt
            with open(prompter_file, 'r', encoding='utf-8') as f:
                prompter_content = f.read().strip()
            
            if not prompter_content:
                self.notify("prompter.txt is empty", severity="warning")
                return
            
            # Check if we have an active project
            has_active_project = (self.agent and 
                                hasattr(self.agent, 'project_files') and 
                                self.agent.project_files and 
                                len(self.agent.project_files) > 0)
            
            if has_active_project:
                # Use prompter content as feedback for existing project
                self.notify("Using prompter.txt content as feedback for current project...", severity="information")
                await self._process_feedback(prompter_content)
            else:
                # Use prompter content to create a new project
                self.notify("Using prompter.txt content to create new project...", severity="information")
                await self.process_task(prompter_content)
            
        except Exception as e:
            self.notify(f"Error using prompter: {e}", severity="error")

    def action_analyze_project(self):
        """Analyze current project files - our simple new feature!"""
        try:
            if not SIMPLE_ANALYZER_AVAILABLE:
                self.notify("Simple analyzer not available", severity="warning")
                return
            
            if not self.agent or not hasattr(self.agent, 'project_files'):
                self.notify("No project loaded to analyze", severity="warning")
                return
            
            # Run our simple analysis
            analysis = analyze_project_files(self.agent.project_files)
            formatted_lines = format_analysis_for_display(analysis)
            
            # Show results in the tree area
            tree_log = self.query_one("#tree", Log)
            tree_log.clear()
            tree_log.write("=== PROJECT ANALYSIS ===")
            for line in formatted_lines:
                tree_log.write(line)
            
            self.notify("Project analysis complete!", severity="information")
            
        except Exception as e:
            self.notify(f"Error analyzing project: {str(e)}", severity="error")
            print(f"Analysis error: {e}")

    def process_task_threaded(self, task):
        """Threaded task processing that updates UI via call_from_thread"""
        if not task.strip():
            self.call_from_thread(self.notify, "Please enter a project description!", severity="warning")
            self.call_from_thread(self._task_completed)
            return

        # Clear cancel event
        self.cancel_event.clear()
        
        # Mark project as active
        self.call_from_thread(self._set_project_active, True)
        
        # Initialize task WITHOUT calling LLM yet
        self.agent.task_prompt = task
        self.agent.project_folder = safe_project_name(task)
        
        # Initialize chat history manually instead of calling get_task()
        system_prompt = """You are an expert software engineer. When asked for a project, return a JSON object with a 'files' key. Each file should be an object with 'filename' and 'content'. Example:
{'files': [{'filename': 'main.py', 'content': '...'}, {'filename': 'utils.js', 'content': '...'}, {'filename': 'App.jsx', 'content': '...'}]}
Do not include markdown or explanations. Only return the JSON."""
        
        self.agent.chat_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        # Store initial state for comparison
        initial_files = []
        
        # Update UI from thread
        self.call_from_thread(self._update_operation_status, "Calling LLM API...")

        # Main processing loop
        while self.agent.attempts < self.agent.max_attempts and not self.cancel_event.is_set():
            self.agent.attempts += 1
            self.call_from_thread(
                self._update_operation_status, 
                f"Attempt {self.agent.attempts}: Calling LLM..."
            )

            try:
                max_tokens = self.agent.estimate_max_tokens()
                llm_response, llm_error = self.call_llm_threaded(
                    self.agent.model, 
                    self.agent.chat_history, 
                    max_tokens
                )

                if self.cancel_event.is_set():
                    self.call_from_thread(self._update_operation_status, "Operation cancelled by user")
                    break

                if llm_error:
                    self.call_from_thread(self._update_error, f"LLM API error: {llm_error}")
                    self.call_from_thread(self._update_operation_status, "LLM API error occurred")
                    break

                if llm_response is None:
                    self.call_from_thread(self._update_error, "LLM returned no response")
                    self.call_from_thread(self._update_operation_status, "LLM returned no response")
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
                continue

            # Store files for comparison
            if self.agent.attempts == 1:
                initial_files = files.copy()
            
            self.agent.project_files = files
            
            # Update language detection
            self.call_from_thread(self._update_language_detection, files)
            self.call_from_thread(self.update_ui)

            # Write and execute files
            self.call_from_thread(self._update_operation_status, "Writing files and compiling/executing...")
            
            try:
                output, error, success = self.agent.write_and_execute_files(files)
                self.call_from_thread(self._update_outputs, output, error)
                self.call_from_thread(self._update_compilation_status, "Success" if success else "Failed")

            except Exception as e:
                self.call_from_thread(self._update_error, f"Execution error: {str(e)}")
                self.call_from_thread(self._update_compilation_status, "Error")
                break

            # Evaluate output and generate feedback with change summary
            if not self.cancel_event.is_set():
                change_summary = self.generate_change_summary(initial_files, files, self.agent.attempts == 1)
                
                # Generate human advice
                advice = self.generate_human_advice(files, output, error, success)
                
                # Show feedback controls and set completion status
                self.call_from_thread(self._show_feedback_controls)
                self.call_from_thread(self._update_operation_status, f"Project attempt {self.agent.attempts} completed - awaiting feedback")
                break

        # Final status update
        if not self.cancel_event.is_set():
            self.call_from_thread(self._update_operation_status, "Project processing completed")
        
        self.call_from_thread(self._task_completed)

    def process_feedback_threaded(self, feedback):
        """Threaded feedback processing"""
        # Clear cancel event
        self.cancel_event.clear()
        
        # Store current state for comparison
        old_files = self.agent.project_files.copy() if self.agent.project_files else []
        
        self.call_from_thread(self._update_operation_status, "Processing feedback...")
        
        # Check if this is a specific file fix request
        if "fix" in feedback.lower() or "update" in feedback.lower():
            feedback_with_context = f"Please fix the following issues: {feedback}\n\nCurrent project status:\nOutput: {self.main_output}\nError: {self.error_output}"
        else:
            feedback_with_context = feedback
        
        self.call_from_thread(self._update_feedback, feedback)

        # Process the feedback
        try:
            result_files = self.agent.process_feedback(feedback_with_context)
            
            if result_files:
                # Update language detection
                self.call_from_thread(self._update_language_detection, result_files)
                self.call_from_thread(self.update_ui)
                
                # Write and execute updated files
                try:
                    output, error, success = self.agent.write_and_execute_files(result_files)
                    self.call_from_thread(self._update_outputs, output, error)
                    self.call_from_thread(self._update_compilation_status, "Success" if success else "Failed")
                    
                    # Generate change summary
                    change_summary = self.generate_change_summary(old_files, result_files, False)
                    
                    # Clear feedback input and update status
                    self.call_from_thread(self._clear_feedback_input)
                    self.call_from_thread(self._update_operation_status, "Feedback processed successfully")
                    
                except Exception as e:
                    self.call_from_thread(self._update_error, f"Execution error: {str(e)}")
                    self.call_from_thread(self._update_compilation_status, "Error")
            else:
                self.call_from_thread(self._update_error, "No files generated from feedback")
                self.call_from_thread(self._update_operation_status, "Feedback processing failed")

        except Exception as e:
            self.call_from_thread(self._update_error, f"Feedback processing error: {str(e)}")
            self.call_from_thread(self._update_operation_status, "Feedback processing failed")

    def generate_human_advice(self, files, output, error, success):
        """Generate human-readable advice based on project results"""
        advice_lines = []
        
        if success:
            advice_lines.append("✅ Project executed successfully!")
            if output:
                advice_lines.append(f"📄 Output: {output[:100]}{'...' if len(output) > 100 else ''}")
        else:
            advice_lines.append("❌ Project execution failed")
            if error:
                advice_lines.append(f"🚨 Error: {error[:100]}{'...' if len(error) > 100 else ''}")
                
                # Provide specific advice based on error type
                if "ModuleNotFoundError" in error or "ImportError" in error:
                    advice_lines.append("💡 Tip: Missing dependencies. Consider adding a requirements.txt file.")
                elif "SyntaxError" in error:
                    advice_lines.append("💡 Tip: Check code syntax. Ask for a syntax review.")
                elif "FileNotFoundError" in error:
                    advice_lines.append("💡 Tip: Missing files. Ask to create missing dependencies.")
                elif "permission" in error.lower():
                    advice_lines.append("💡 Tip: Permission issues. Check file permissions or run location.")
        
        # File analysis
        main_file = detect_main_file(files)
        if main_file:
            lang_name, _, _, _, _ = get_language_info(main_file)
            advice_lines.append(f"🔍 Detected: {lang_name} project with main file: {main_file}")
        
        advice_lines.append(f"📁 Total files: {len(files)}")
        
        return "\n".join(advice_lines)

# Simple fallback monitoring class for basic functionality
class FallbackMonitoring:
    """Simple fallback monitoring implementation"""
    def __init__(self):
        self.session_data = {
            'total_calls': 0,
            'total_tokens': 0, 
            'total_cost': 0.0,
            'session_cost': 0.0
        }
        self.callback = None
    
    def log_api_call(self, model, tokens, cost):
        """Log an API call"""
        self.session_data['total_calls'] += 1
        self.session_data['total_tokens'] += tokens
        self.session_data['total_cost'] += cost
        self.session_data['session_cost'] += cost
        
        if self.callback:
            try:
                self.callback(self.get_ui_summary())
            except Exception as e:
                print(f"Error in monitoring callback: {e}")
    
    def get_ui_summary(self):
        """Get UI summary for display"""
        return {
            'session': self.session_data.copy(),
            'recent_calls': [],
            'model_usage': {}
        }
    def get_session_summary(self):
        """Get session summary"""
        return self.session_data.copy()
    
    def reset_session_stats(self):
        """Reset session statistics"""
        self.session_data = {
            'total_calls': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'session_cost': 0.0
        }
    
    def set_callback(self, callback):
        """Set callback for monitoring updates"""
        self.callback = callback

# Monitoring integration helper
class MonitoringIntegration:
    """Helper class for monitoring integration"""
    
    @staticmethod
    def setup_monitoring_for_app(app):
        """Setup monitoring for the app"""
        try:
            # Try to use the simple fallback monitoring
            app.monitor = FallbackMonitoring()
            return True
        except Exception as e:
            print(f"Failed to setup monitoring: {e}")
            return False

def main():
    """Main entry point for the Textual Agent UI"""
    try:
        app = CodingAgentApp()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())

def format_project_structure_wrapped(files, width=70):
    """Format project structure for display with wrapping."""
    if not files:
        return ["No project files yet..."]

    tree_lines = ascii_tree(files)
    wrapped_lines = []
    for line in tree_lines:
        wrapped_lines.extend(textwrap.wrap(line, width=width))
    return wrapped_lines

def format_chat_message_wrapped(role, content, width=65):
    """Format chat messages for display with wrapping."""
    header = f"[{role.upper()}]:"
    wrapped_content = textwrap.wrap(content, width=width)
    return [header] + wrapped_content