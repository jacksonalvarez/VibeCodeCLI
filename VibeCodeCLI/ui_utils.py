"""
UI utilities for the textual-based coding agent
"""
import time
import datetime
from rich.text import Text
from rich.console import Console


class UIStateManager:
    """Manages UI state and updates"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.console = Console()
    
    def update_status_display(self, widget_id, label, value, status_type="info"):
        """Update status displays with proper styling"""
        try:
            widget = self.app.query_one(f"#{widget_id}")
            
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
        except Exception as e:
            print(f"UI update error: {e}")
    
    def update_project_controls(self, api_key_valid, project_active):
        """Update project control states"""
        try:
            if not api_key_valid:
                self.app.query_one("#project_input").disabled = True
                self.app.query_one("#create_btn").disabled = True
                return
                
            if project_active:
                self.app.query_one("#project_input").disabled = True
                self.app.query_one("#create_btn").disabled = True
            else:
                self.app.query_one("#project_input").disabled = False
                self.app.query_one("#create_btn").disabled = False
        except Exception as e:
            print(f"Control update error: {e}")


class ClipboardManager:
    """Handles clipboard operations"""
    
    @staticmethod
    def copy_project_data(agent, main_output="", error_output="", feedback=""):
        """Copy all project data to clipboard"""
        try:
            import pyperclip
            
            data_sections = []
            data_sections.append("=== AI CODING AGENT PROJECT DATA ===")
            data_sections.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            data_sections.append("")
            
            if agent and getattr(agent, 'project_files', None):
                data_sections.append("=== PROJECT FILES ===")
                for file_data in agent.project_files:
                    data_sections.append(f"--- {file_data['filename']} ---")
                    data_sections.append(file_data['content'])
                    data_sections.append("")
            
            if main_output:
                data_sections.append("=== EXECUTION OUTPUT ===")
                data_sections.append(main_output)
                data_sections.append("")
            
            if error_output:
                data_sections.append("=== EXECUTION ERRORS ===")
                data_sections.append(error_output)
                data_sections.append("")
            
            full_data = "\n".join(data_sections)
            pyperclip.copy(full_data)
            return True, "Complete project data copied to clipboard!"
            
        except ImportError:
            return False, "pyperclip not installed! Install with: pip install pyperclip"
        except Exception as e:
            return False, f"Failed to copy data: {str(e)}"
    
    @staticmethod
    def copy_output_only(main_output="", error_output=""):
        """Copy just the execution output to clipboard"""
        try:
            import pyperclip
            
            output_data = []
            if main_output:
                output_data.append("=== EXECUTION OUTPUT ===")
                output_data.append(main_output)
            if error_output:
                output_data.append("=== EXECUTION ERRORS ===")
                output_data.append(error_output)
            
            if not output_data:
                output_data.append("No output available yet.")
            
            full_output = "\n".join(output_data)
            pyperclip.copy(full_output)
            return True, "Output copied to clipboard!"
            
        except ImportError:
            return False, "pyperclip not installed! Install with: pip install pyperclip"
        except Exception as e:
            return False, f"Failed to copy output: {str(e)}"


class HelpManager:
    """Manages help and documentation"""
    
    @staticmethod
    def get_help_text():
        """Get comprehensive help text"""
        return """
=== AI CODING AGENT HELP ===

KEYBOARD SHORTCUTS:
• Q - Quit application
• R - Reload API key from .env file
• Ctrl+C - Cancel current operation
• Ctrl+Shift+C - Copy execution output
• Ctrl+Alt+C - Copy all project data
• F1 - Show this help

HOW TO USE:
1. Set up your API key in the .env file
2. Enter a project description and press Enter or click "Create Project"
3. Wait for the AI to generate and test the code
4. Provide feedback if needed to improve the project
5. Click "Complete Project" when satisfied

SUPPORTED LANGUAGES:
• Python (.py)
• JavaScript/Node.js (.js)
• TypeScript (.ts)
• Java (.java)
• C++ (.cpp)
• C (.c)
• Go (.go)
• Rust (.rs)
• Ruby (.rb)
• PHP (.php)
• HTML (.html)

API KEY SETUP:
Create a .env file with one of:
• OPENAI_API_KEY=your_key_here
• ANTHROPIC_API_KEY=your_key_here
• API_KEY=your_key_here
• LLM_API_KEY=your_key_here
        """
    
    @staticmethod
    def get_env_instructions():
        """Get environment setup instructions"""
        return """
🔑 API KEY REQUIRED

To use this coding agent, create a .env file with your API key.

Steps:
1. Create a file named .env in the same directory as this script
2. Add one of the following lines:

   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   API_KEY=your_api_key_here
   LLM_API_KEY=your_api_key_here

3. Save the file and restart the application

Example .env file:
OPENAI_API_KEY=sk-proj-abcd1234...

Note: Never commit your .env file to version control!
        """


class ThemeManager:
    """Manages UI themes and styling"""
    
    @staticmethod
    def get_github_dark_css():
        """Get GitHub dark theme CSS"""
        return """
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
        
        Input {
            margin: 1;
            border: solid #30363d;
            background: #0d1117;
            color: #c9d1d9;
        }
        
        Log {
            border: solid #30363d;
            height: 1fr;
            background: #010409;
            color: #c9d1d9;
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
        """
