"""
Code Analysis Feature for AI Coding Agent

This feature provides code analysis capabilities including:
- Dependency analysis
- Complexity metrics
- Security scanning
- Code quality assessment
"""

import ast
import re
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import subprocess

from features import BaseFeature

class CodeAnalysisFeature(BaseFeature):
    """Feature for analyzing code quality and structure"""
    
    def __init__(self):
        super().__init__("code_analysis", "1.0.0")
        self.dependencies = []
    
    async def initialize(self, agent_context: Dict[str, Any]) -> bool:
        """Initialize the code analysis feature"""
        try:
            # Check if required tools are available
            self.has_flake8 = self._check_tool_available("flake8")
            self.has_bandit = self._check_tool_available("bandit")
            self.has_mypy = self._check_tool_available("mypy")
            
            return True
        except Exception as e:
            print(f"Error initializing code analysis: {e}")
            return False
    
    def _check_tool_available(self, tool_name: str) -> bool:
        """Check if a command-line tool is available"""
        try:
            subprocess.run([tool_name, "--version"], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code analysis"""
        analysis_type = request.get("type", "all")
        files = request.get("files", [])
        project_path = request.get("project_path", ".")
        
        results = {
            "analysis_type": analysis_type,
            "files_analyzed": len(files),
            "results": {}
        }
        
        if analysis_type in ["all", "dependencies"]:
            results["results"]["dependencies"] = await self._analyze_dependencies(files)
        
        if analysis_type in ["all", "complexity"]:
            results["results"]["complexity"] = await self._analyze_complexity(files)
        
        if analysis_type in ["all", "security"]:
            results["results"]["security"] = await self._analyze_security(files, project_path)
        
        if analysis_type in ["all", "quality"]:
            results["results"]["quality"] = await self._analyze_quality(files, project_path)
        
        return results
    
    def get_capabilities(self) -> List[str]:
        """Return capabilities of this feature"""
        return [
            "dependency_analysis",
            "complexity_analysis", 
            "security_scanning",
            "code_quality_assessment",
            "import_analysis",
            "function_metrics"
        ]
    
    async def _analyze_dependencies(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze project dependencies"""
        dependencies = {
            "imports": set(),
            "external_packages": set(),
            "standard_library": set(),
            "local_imports": set(),
            "import_graph": {}
        }
        
        # Standard library modules (partial list)
        stdlib_modules = {
            'os', 'sys', 'json', 're', 'time', 'datetime', 'collections',
            'itertools', 'functools', 'threading', 'asyncio', 'subprocess',
            'pathlib', 'typing', 'abc', 'dataclasses', 'enum'
        }
        
        for file_info in files:
            if not file_info.get('filename', '').endswith('.py'):
                continue
            
            content = file_info.get('content', '')
            file_imports = self._extract_imports_from_code(content)
            
            dependencies["import_graph"][file_info['filename']] = file_imports
            
            for imp in file_imports:
                dependencies["imports"].add(imp)
                
                # Classify import
                if imp.startswith('.'):
                    dependencies["local_imports"].add(imp)
                elif imp.split('.')[0] in stdlib_modules:
                    dependencies["standard_library"].add(imp)
                else:
                    dependencies["external_packages"].add(imp)
        
        # Convert sets to lists for JSON serialization
        return {
            "total_imports": len(dependencies["imports"]),
            "external_packages": list(dependencies["external_packages"]),
            "standard_library": list(dependencies["standard_library"]),
            "local_imports": list(dependencies["local_imports"]),
            "import_graph": dependencies["import_graph"]
        }
    
    def _extract_imports_from_code(self, code: str) -> List[str]:
        """Extract imports from Python code"""
        imports = []
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if node.level > 0:  # Relative import
                            imports.append('.' * node.level + (node.module or ''))
                        else:
                            imports.append(node.module)
        except SyntaxError:
            # Fallback to regex for malformed code
            import_patterns = [
                r'^import\s+([^\s#]+)',
                r'^from\s+([^\s#]+)\s+import'
            ]
            
            for line in code.split('\n'):
                line = line.strip()
                for pattern in import_patterns:
                    match = re.match(pattern, line)
                    if match:
                        imports.append(match.group(1))
        
        return imports
    
    async def _analyze_complexity(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze code complexity"""
        complexity_results = {
            "files": {},
            "summary": {
                "total_functions": 0,
                "avg_complexity": 0,
                "high_complexity_functions": []
            }
        }
        
        total_complexity = 0
        function_count = 0
        
        for file_info in files:
            if not file_info.get('filename', '').endswith('.py'):
                continue
            
            filename = file_info['filename']
            content = file_info.get('content', '')
            
            file_complexity = self._calculate_file_complexity(content)
            complexity_results["files"][filename] = file_complexity
            
            # Update summary
            for func_data in file_complexity.get("functions", []):
                function_count += 1
                complexity = func_data.get("complexity", 0)
                total_complexity += complexity
                
                if complexity > 10:  # High complexity threshold
                    complexity_results["summary"]["high_complexity_functions"].append({
                        "file": filename,
                        "function": func_data["name"],
                        "complexity": complexity
                    })
        
        if function_count > 0:
            complexity_results["summary"]["avg_complexity"] = total_complexity / function_count
        
        complexity_results["summary"]["total_functions"] = function_count
        
        return complexity_results
    
    def _calculate_file_complexity(self, code: str) -> Dict[str, Any]:
        """Calculate complexity metrics for a file"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"error": "Syntax error in code", "functions": []}
        
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_cyclomatic_complexity(node)
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "complexity": complexity,
                    "args_count": len(node.args.args),
                    "returns_count": len([n for n in ast.walk(node) if isinstance(n, ast.Return)])
                })
        
        return {
            "total_lines": len(code.split('\n')),
            "functions": functions,
            "classes": len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
        }
    
    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity for a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
        
        return complexity
    
    async def _analyze_security(self, files: List[Dict[str, Any]], project_path: str) -> Dict[str, Any]:
        """Perform security analysis"""
        security_results = {
            "issues": [],
            "summary": {
                "total_issues": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0
            }
        }
        
        # Basic security patterns to check
        security_patterns = [
            {
                "pattern": r"eval\s*\(",
                "message": "Use of eval() can be dangerous",
                "severity": "high"
            },
            {
                "pattern": r"exec\s*\(",
                "message": "Use of exec() can be dangerous", 
                "severity": "high"
            },
            {
                "pattern": r"__import__\s*\(",
                "message": "Dynamic imports can be risky",
                "severity": "medium"
            },
            {
                "pattern": r"subprocess\.call\s*\(",
                "message": "Review subprocess calls for injection risks",
                "severity": "medium"
            },
            {
                "pattern": r"open\s*\([^)]*['\"]w['\"]",
                "message": "File write operations should be reviewed",
                "severity": "low"
            }
        ]
        
        for file_info in files:
            if not file_info.get('filename', '').endswith('.py'):
                continue
            
            filename = file_info['filename']
            content = file_info.get('content', '')
            
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern_info in security_patterns:
                    if re.search(pattern_info["pattern"], line):
                        issue = {
                            "file": filename,
                            "line": line_num,
                            "message": pattern_info["message"],
                            "severity": pattern_info["severity"],
                            "code": line.strip()
                        }
                        security_results["issues"].append(issue)
                        
                        # Update summary
                        security_results["summary"]["total_issues"] += 1
                        security_results["summary"][f"{pattern_info['severity']}_severity"] += 1
        
        # Use bandit if available
        if self.has_bandit:
            try:
                bandit_results = await self._run_bandit_analysis(project_path)
                if bandit_results:
                    security_results["bandit_results"] = bandit_results
            except Exception as e:
                security_results["bandit_error"] = str(e)
        
        return security_results
    
    async def _run_bandit_analysis(self, project_path: str) -> Optional[Dict[str, Any]]:
        """Run bandit security analysis if available"""
        try:
            result = subprocess.run(
                ["bandit", "-r", project_path, "-f", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                import json
                return json.loads(result.stdout)
        except Exception:
            pass
        
        return None
    
    async def _analyze_quality(self, files: List[Dict[str, Any]], project_path: str) -> Dict[str, Any]:
        """Analyze code quality"""
        quality_results = {
            "issues": [],
            "metrics": {
                "avg_line_length": 0,
                "long_functions": [],
                "duplicate_code": [],
                "naming_issues": []
            }
        }
        
        total_line_length = 0
        line_count = 0
        
        for file_info in files:
            if not file_info.get('filename', '').endswith('.py'):
                continue
            
            filename = file_info['filename']
            content = file_info.get('content', '')
            
            # Analyze line lengths
            for line_num, line in enumerate(content.split('\n'), 1):
                line_length = len(line)
                total_line_length += line_length
                line_count += 1
                
                if line_length > 88:  # PEP 8 recommendation
                    quality_results["issues"].append({
                        "file": filename,
                        "line": line_num,
                        "type": "long_line",
                        "message": f"Line too long ({line_length} characters)",
                        "severity": "low"
                    })
            
            # Check function lengths
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_lines = 0
                        if hasattr(node, 'end_lineno') and node.end_lineno:
                            func_lines = node.end_lineno - node.lineno + 1
                        
                        if func_lines > 50:  # Long function threshold
                            quality_results["metrics"]["long_functions"].append({
                                "file": filename,
                                "function": node.name,
                                "lines": func_lines,
                                "start_line": node.lineno
                            })
                        
                        # Check naming conventions
                        if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                            quality_results["metrics"]["naming_issues"].append({
                                "file": filename,
                                "line": node.lineno,
                                "type": "function_naming",
                                "name": node.name,
                                "message": "Function name should be lowercase with underscores"
                            })
            
            except SyntaxError:
                continue
        
        if line_count > 0:
            quality_results["metrics"]["avg_line_length"] = total_line_length / line_count
        
        # Run flake8 if available
        if self.has_flake8:
            try:
                flake8_results = await self._run_flake8_analysis(project_path)
                if flake8_results:
                    quality_results["flake8_results"] = flake8_results
            except Exception as e:
                quality_results["flake8_error"] = str(e)
        
        return quality_results
    
    async def _run_flake8_analysis(self, project_path: str) -> Optional[List[Dict[str, Any]]]:
        """Run flake8 analysis if available"""
        try:
            result = subprocess.run(
                ["flake8", project_path, "--format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                # Parse flake8 output (simplified)
                issues = []
                for line in result.stdout.split('\n'):
                    if line.strip():
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            issues.append({
                                "file": parts[0],
                                "line": int(parts[1]) if parts[1].isdigit() else 0,
                                "column": int(parts[2]) if parts[2].isdigit() else 0,
                                "message": parts[3].strip()
                            })
                return issues
        except Exception:
            pass
        
        return None
