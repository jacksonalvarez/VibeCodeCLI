"""
Simple Project Info Feature - Our first incremental feature!

This just analyzes basic project information without complexity.
"""

def analyze_project_files(files):
    """Simple analysis of project files - no fancy stuff"""
    if not files:
        return {"message": "No files to analyze"}
    
    analysis = {
        "total_files": len(files),
        "file_types": {},
        "largest_file": None,
        "total_lines": 0
    }
    
    max_size = 0
    
    for file_info in files:
        filename = file_info.get('filename', '')
        content = file_info.get('content', '')
        
        # Count file types
        ext = filename.split('.')[-1] if '.' in filename else 'no_extension'
        analysis["file_types"][ext] = analysis["file_types"].get(ext, 0) + 1
        
        # Count lines
        lines = len(content.split('\n')) if content else 0
        analysis["total_lines"] += lines
        
        # Find largest file
        if lines > max_size:
            max_size = lines
            analysis["largest_file"] = {"name": filename, "lines": lines}
    
    return analysis

def format_analysis_for_display(analysis):
    """Format analysis results for the UI"""
    if "message" in analysis:
        return [analysis["message"]]
    
    lines = [
        f"📁 Total Files: {analysis['total_files']}",
        f"📄 Total Lines: {analysis['total_lines']:,}",
        "",
        "File Types:"
    ]
    
    for ext, count in analysis['file_types'].items():
        lines.append(f"  .{ext}: {count} files")
    
    if analysis['largest_file']:
        lines.extend([
            "",
            f"📊 Largest File: {analysis['largest_file']['name']}",
            f"   ({analysis['largest_file']['lines']} lines)"
        ])
    
    return lines
