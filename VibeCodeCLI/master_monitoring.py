#!/usr/bin/env python3
"""
MASTER MONITORING UTILITY
==========================
Comprehensive token usage and cost tracking for LLM Coding Agent

Features:
- Real-time token and cost tracking
- Historical usage analysis
- Model comparison charts
- Cost optimization recommendations
- Integration with existing tools
"""

import os
import sys
import json
import sqlite3
import datetime
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import re

# Data visualization libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print("Warning: Matplotlib not available. Install with: pip install matplotlib numpy")

# Import existing tools
sys.path.append('.')
try:
    from agent import LLMCodingAgent
    from llm_utils import LLMUtils
except ImportError as e:
    print(f"Warning: Could not import existing modules: {e}")

@dataclass
class APICall:
    """Represents a single API call record"""
    timestamp: datetime.datetime
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    duration: float
    cost: float
    task_type: str
    success: bool

class MonitoringDatabase:
    """SQLite database for storing API call records"""
    
    def __init__(self, db_path: str = "api_monitoring.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cached_tokens INTEGER DEFAULT 0,
                    duration REAL NOT NULL,
                    cost REAL NOT NULL,
                    task_type TEXT,
                    success BOOLEAN NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON api_calls(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model ON api_calls(model)
            """)
    
    def record_api_call(self, api_call: APICall):
        """Record a new API call"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO api_calls 
                (timestamp, model, input_tokens, output_tokens, cached_tokens, 
                 duration, cost, task_type, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                api_call.timestamp.isoformat(),
                api_call.model,
                api_call.input_tokens,
                api_call.output_tokens,
                api_call.cached_tokens,
                api_call.duration,
                api_call.cost,
                api_call.task_type,
                api_call.success
            ))
    
    def get_calls_in_range(self, days: int = 30) -> List[APICall]:
        """Get API calls from the last N days"""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, model, input_tokens, output_tokens, cached_tokens,
                       duration, cost, task_type, success
                FROM api_calls 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (cutoff.isoformat(),))
            
            calls = []
            for row in cursor.fetchall():
                calls.append(APICall(
                    timestamp=datetime.datetime.fromisoformat(row[0]),
                    model=row[1],
                    input_tokens=row[2],
                    output_tokens=row[3],
                    cached_tokens=row[4],
                    duration=row[5],
                    cost=row[6],
                    task_type=row[7],
                    success=bool(row[8])
                ))
            
            return calls
    
    def get_model_usage_summary(self, days: int = 30) -> Dict[str, Dict]:
        """Get usage summary grouped by model"""
        calls = self.get_calls_in_range(days)
        
        summary = defaultdict(lambda: {
            'calls': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'cached_tokens': 0,
            'total_cost': 0.0,
            'avg_duration': 0.0,
            'success_rate': 0.0
        })
        
        for call in calls:
            model_data = summary[call.model]
            model_data['calls'] += 1
            model_data['input_tokens'] += call.input_tokens
            model_data['output_tokens'] += call.output_tokens
            model_data['cached_tokens'] += call.cached_tokens
            model_data['total_cost'] += call.cost
            model_data['avg_duration'] += call.duration
            if call.success:
                model_data['success_rate'] += 1
        
        # Calculate averages
        for model_data in summary.values():
            if model_data['calls'] > 0:
                model_data['avg_duration'] /= model_data['calls']
                model_data['success_rate'] = (model_data['success_rate'] / model_data['calls']) * 100
        
        return dict(summary)
    
    def get_daily_usage(self, days: int = 30) -> Dict[str, Dict]:
        """Get daily usage statistics"""
        calls = self.get_calls_in_range(days)
        
        daily_usage = defaultdict(lambda: {
            'calls': 0,
            'tokens': 0,
            'cost': 0.0
        })
        
        for call in calls:
            day = call.timestamp.date().isoformat()
            daily_usage[day]['calls'] += 1
            daily_usage[day]['tokens'] += call.input_tokens + call.output_tokens
            daily_usage[day]['cost'] += call.cost
        
        return dict(daily_usage)
    
    def get_total_calls(self) -> int:
        """Get total number of recorded API calls"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM api_calls")
            return cursor.fetchone()[0]

class MasterMonitoring:
    """Main monitoring class with real-time UI updates"""
    
    def __init__(self, db_path: str = "api_monitoring.db"):
        self.db = MonitoringDatabase(db_path)
        self.ui_callback = None  # Callback function for UI updates
        self.session_stats = {
            'calls': 0,
            'tokens': 0,
            'cost': 0.0,
            'start_time': datetime.datetime.now()
        }
        self.model_costs = {
            'gpt-4o': {'input': 5.00, 'output': 15.00, 'cached': 2.50},
            'gpt-4o-2024-08-06': {'input': 5.00, 'output': 15.00, 'cached': 2.50},
            'gpt-4o-mini': {'input': 0.15, 'output': 0.60, 'cached': 0.075},
            'gpt-4o-mini-2024-07-18': {'input': 0.15, 'output': 0.60, 'cached': 0.075},
            'gpt-4': {'input': 30.00, 'output': 60.00, 'cached': 15.00},
            'gpt-4-turbo': {'input': 10.00, 'output': 30.00, 'cached': 5.00},
            'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50, 'cached': 0.25}
        }
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
        """Calculate cost for a given API call"""
        if model not in self.model_costs:
            # Default to gpt-4o-mini pricing if model not found
            costs = self.model_costs['gpt-4o-mini']
        else:
            costs = self.model_costs[model]
        
        input_cost = (input_tokens / 1_000_000) * costs['input']
        output_cost = (output_tokens / 1_000_000) * costs['output']
        cached_cost = (cached_tokens / 1_000_000) * costs['cached']
        
        return input_cost + output_cost + cached_cost
    
    def record_api_call(self, model: str, input_tokens: int, output_tokens: int, 
                       duration: float, cached_tokens: int = 0, task_type: str = "unknown", 
                       success: bool = True):
        """Record a new API call with real-time UI updates"""
        cost = self.calculate_cost(model, input_tokens, output_tokens, cached_tokens)
        
        api_call = APICall(
            timestamp=datetime.datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            duration=duration,
            cost=cost,
            task_type=task_type,
            success=success
        )
        
        self.db.record_api_call(api_call)
        
        # Update session statistics
        self.session_stats['calls'] += 1
        self.session_stats['tokens'] += input_tokens + output_tokens
        self.session_stats['cost'] += cost
        
        # Print real-time monitoring info
        print(f"API Call Recorded: {model} | {input_tokens+output_tokens:,} tokens | ${cost:.4f}")
        print(f"Session: {self.session_stats['calls']} calls | {self.session_stats['tokens']:,} tokens | ${self.session_stats['cost']:.4f}")
        
        # Trigger UI update
        self._trigger_ui_update()
    
    def generate_usage_report(self, days: int = 30) -> str:
        """Generate a comprehensive usage report"""
        calls = self.db.get_calls_in_range(days)
        
        if not calls:
            return f"No API usage recorded in the last {days} days."
        
        summary = self.db.get_model_usage_summary(days)
        report = []
        
        report.append(f"MASTER MONITORING REPORT - Last {days} Days")
        report.append("=" * 60)
        
        # Overall statistics
        total_calls = sum(data['calls'] for data in summary.values())
        total_tokens = sum(data['input_tokens'] + data['output_tokens'] for data in summary.values())
        total_cost = sum(data['total_cost'] for data in summary.values())
        avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
        
        report.append(f"\nOVERALL STATISTICS:")
        report.append(f"  Total API Calls: {total_calls:,}")
        report.append(f"  Total Tokens Used: {total_tokens:,}")
        report.append(f"  Total Cost: ${total_cost:.2f}")
        report.append(f"  Average Cost per Call: ${avg_cost_per_call:.4f}")
        
        # Model breakdown
        report.append(f"\nMODEL BREAKDOWN:")
        for model, data in sorted(summary.items(), key=lambda x: x[1]['total_cost'], reverse=True):
            report.append(f"  {model}:")
            report.append(f"    Calls: {data['calls']:,}")
            report.append(f"    Input Tokens: {data['input_tokens']:,}")
            report.append(f"    Output Tokens: {data['output_tokens']:,}")
            report.append(f"    Total Cost: ${data['total_cost']:.2f}")
            report.append(f"    Avg Duration: {data['avg_duration']:.2f}s")
            report.append(f"    Success Rate: {data['success_rate']:.1f}%")
            report.append("")
        
        # Cost optimization recommendations
        report.append(f"\nCOST OPTIMIZATION RECOMMENDATIONS:")
        
        gpt4o_usage = summary.get('gpt-4o', {}).get('total_cost', 0) + summary.get('gpt-4o-2024-08-06', {}).get('total_cost', 0)
        gpt4o_mini_usage = summary.get('gpt-4o-mini', {}).get('total_cost', 0) + summary.get('gpt-4o-mini-2024-07-18', {}).get('total_cost', 0)
        
        if gpt4o_usage > gpt4o_mini_usage and gpt4o_usage > 1.0:
            potential_savings = gpt4o_usage * 0.96  # 96% savings with gpt-4o-mini
            report.append(f"  Consider switching to gpt-4o-mini for most tasks")
            report.append(f"  Potential savings: ${potential_savings:.2f} ({96}% reduction)")
        elif gpt4o_mini_usage > gpt4o_usage:
            report.append(f"   Good! Using cost-effective gpt-4o-mini for most tasks")
        
        return "\n".join(report)
    
    def generate_usage_chart(self, days: int = 30, save_path: str = "usage_chart.png") -> str:
        """Generate a usage chart showing daily token usage and costs"""
        if not VISUALIZATION_AVAILABLE:
            return "Matplotlib not available for charts. Install with: pip install matplotlib numpy"
        
        daily_usage = self.db.get_daily_usage(days)
        
        if not daily_usage:
            return f"No data available for chart generation (last {days} days)"
        
        # Prepare data for plotting
        dates = []
        tokens = []
        costs = []
        
        # Fill in missing days with zeros
        start_date = datetime.date.today() - datetime.timedelta(days=days)
        for i in range(days):
            current_date = start_date + datetime.timedelta(days=i)
            date_str = current_date.isoformat()
            
            dates.append(current_date)
            if date_str in daily_usage:
                tokens.append(daily_usage[date_str]['tokens'])
                costs.append(daily_usage[date_str]['cost'])
            else:
                tokens.append(0)
                costs.append(0.0)
        
        # Create the chart
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f'API Usage - Last {days} Days', fontsize=16, fontweight='bold')
        
        # Token usage chart
        ax1.plot(dates, tokens, marker='o', linewidth=2, markersize=4)
        ax1.set_title('Daily Token Usage')
        ax1.set_ylabel('Tokens')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//10)))
        
        # Cost chart
        ax2.plot(dates, costs, marker='s', color='red', linewidth=2, markersize=4)
        ax2.set_title('Daily Cost')
        ax2.set_ylabel('Cost ($)')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//10)))
        
        # Rotate x-axis labels for better readability
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return f"Chart saved to: {save_path}"
    
    def generate_model_comparison_chart(self, days: int = 30, save_path: str = "model_comparison.png") -> str:
        """Generate a chart comparing gpt-4o vs gpt-4o-mini usage and costs"""
        if not VISUALIZATION_AVAILABLE:
            return "Matplotlib not available for charts. Install with: pip install matplotlib numpy"
        
        calls = self.db.get_calls_in_range(days)
        
        # Filter for gpt-4o and gpt-4o-mini calls
        gpt4o_calls = [c for c in calls if 'gpt-4o' in c.model and 'mini' not in c.model]
        gpt4o_mini_calls = [c for c in calls if 'gpt-4o-mini' in c.model]
        
        if not gpt4o_calls and not gpt4o_mini_calls:
            return f"No GPT-4o or GPT-4o-mini usage found (last {days} days)"
        
        # Daily data for both models
        daily_gpt4o = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})
        daily_gpt4o_mini = defaultdict(lambda: {'tokens': 0, 'cost': 0.0, 'calls': 0})
        
        for call in gpt4o_calls:
            day = call.timestamp.date().isoformat()
            daily_gpt4o[day]['tokens'] += call.input_tokens + call.output_tokens
            daily_gpt4o[day]['cost'] += call.cost
            daily_gpt4o[day]['calls'] += 1
        
        for call in gpt4o_mini_calls:
            day = call.timestamp.date().isoformat()
            daily_gpt4o_mini[day]['tokens'] += call.input_tokens + call.output_tokens
            daily_gpt4o_mini[day]['cost'] += call.cost
            daily_gpt4o_mini[day]['calls'] += 1
        
        # Prepare data for plotting
        start_date = datetime.date.today() - datetime.timedelta(days=days)
        dates = []
        gpt4o_costs = []
        gpt4o_mini_costs = []
        gpt4o_tokens = []
        gpt4o_mini_tokens = []
        
        for i in range(days):
            current_date = start_date + datetime.timedelta(days=i)
            date_str = current_date.isoformat()
            
            dates.append(current_date)
            gpt4o_costs.append(daily_gpt4o[date_str]['cost'])
            gpt4o_mini_costs.append(daily_gpt4o_mini[date_str]['cost'])
            gpt4o_tokens.append(daily_gpt4o[date_str]['tokens'])
            gpt4o_mini_tokens.append(daily_gpt4o_mini[date_str]['tokens'])
        
        # Create comparison chart
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'GPT-4o vs GPT-4o-mini Comparison - Last {days} Days', fontsize=16, fontweight='bold')
        
        # Daily costs comparison
        ax1.plot(dates, gpt4o_costs, marker='o', label='GPT-4o', color='red', linewidth=2)
        ax1.plot(dates, gpt4o_mini_costs, marker='s', label='GPT-4o-mini', color='green', linewidth=2)
        ax1.set_title('Daily Costs Comparison')
        ax1.set_ylabel('Cost ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        
        # Daily tokens comparison
        ax2.plot(dates, gpt4o_tokens, marker='o', label='GPT-4o', color='red', linewidth=2)
        ax2.plot(dates, gpt4o_mini_tokens, marker='s', label='GPT-4o-mini', color='green', linewidth=2)
        ax2.set_title('Daily Tokens Comparison')
        ax2.set_ylabel('Tokens')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        
        # Total cost pie chart
        total_gpt4o_cost = sum(gpt4o_costs)
        total_gpt4o_mini_cost = sum(gpt4o_mini_costs)
        
        if total_gpt4o_cost > 0 or total_gpt4o_mini_cost > 0:
            costs = [total_gpt4o_cost, total_gpt4o_mini_cost]
            labels = [f'GPT-4o\n${total_gpt4o_cost:.2f}', f'GPT-4o-mini\n${total_gpt4o_mini_cost:.2f}']
            colors = ['red', 'green']
            
            ax3.pie(costs, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax3.set_title('Total Cost Distribution')
        
        # Total tokens pie chart
        total_gpt4o_tokens = sum(gpt4o_tokens)
        total_gpt4o_mini_tokens = sum(gpt4o_mini_tokens)
        
        if total_gpt4o_tokens > 0 or total_gpt4o_mini_tokens > 0:
            tokens = [total_gpt4o_tokens, total_gpt4o_mini_tokens]
            labels = [f'GPT-4o\n{total_gpt4o_tokens:,}', f'GPT-4o-mini\n{total_gpt4o_mini_tokens:,}']
            colors = ['red', 'green']
            
            ax4.pie(tokens, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax4.set_title('Total Tokens Distribution')
        
        # Rotate x-axis labels
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return f"GPT-4o comparison chart saved to: {save_path}"
    
    def check_integration_status(self) -> List[str]:
        """Check the status of integration with existing tools"""
        results = []
        
        # Check agent.py
        try:
            agent = LLMCodingAgent()
            results.append(f"agent.py: Default model is '{agent.model}'")
            
            if hasattr(agent, '_estimate_max_tokens'):
                max_tokens = agent._estimate_max_tokens()
                results.append(f"agent.py: Max tokens estimation available ({max_tokens:,})")
            else:
                results.append("agent.py: Max tokens estimation method not found")
                
        except Exception as e:
            results.append(f"agent.py: Error - {e}")
        
        # Check check_model_usage.py
        if Path('check_model_usage.py').exists():
            results.append("check_model_usage.py: Available for integration")
        else:
            results.append("check_model_usage.py: Not found")
        
        # Check llm_utils.py
        try:
            from llm_utils import LLMUtils
            results.append("llm_utils.py: Available for API call monitoring")
        except Exception as e:
            results.append(f"llm_utils.py: Error - {e}")
        
        # Check database status
        try:
            count = self.db.get_total_calls()
            if count > 0:
                results.append(f"Database: {count:,} API calls recorded")
            else:
                results.append("Database: New database will be created")
        except Exception as e:
            results.append(f"Database: Error - {e}")
        
        return results
    
    def cleanup_deprecated_files(self) -> List[str]:
        """Remove deprecated monitoring files"""
        results = []
        deprecated_files = [
            'monitoring_wrapper.py'
        ]
        
        for file_path in deprecated_files:
            if Path(file_path).exists():
                try:
                    os.remove(file_path)
                    results.append(f"Removed deprecated file: {file_path}")
                except Exception as e:
                    results.append(f"Could not remove {file_path}: {e}")
            else:
                results.append(f"Deprecated file not found: {file_path}")
        
        return results

    def set_ui_callback(self, callback_function):
        """Set the UI update callback function"""
        self.ui_callback = callback_function
        print("UI callback registered for real-time monitoring updates")
    
    def _trigger_ui_update(self):
        """Trigger UI update if callback is set"""
        if self.ui_callback:
            try:
                # Get current session stats
                summary = self.get_session_summary()
                self.ui_callback(summary)
            except Exception as e:
                print(f"UI update error: {e}")
    
    def get_session_summary(self) -> dict:
        """Get current session statistics for UI display"""
        return {
            'session_calls': self.session_stats['calls'],
            'session_tokens': self.session_stats['tokens'],
            'session_cost': self.session_stats['cost'],
            'session_duration': (datetime.datetime.now() - self.session_stats['start_time']).total_seconds(),
            'total_calls': self.db.get_total_calls(),
            'recent_model_usage': self.db.get_model_usage_summary(1),  # Last 24 hours
            'daily_cost': sum(data['total_cost'] for data in self.db.get_model_usage_summary(1).values())
        }
    
    def get_real_time_metrics(self) -> dict:
        """Get real-time metrics for UI display"""
        recent_calls = self.db.get_calls_in_range(1)  # Last 24 hours
        
        # Calculate metrics
        total_calls_today = len(recent_calls)
        total_tokens_today = sum(call.input_tokens + call.output_tokens for call in recent_calls)
        total_cost_today = sum(call.cost for call in recent_calls)
        
        # Model breakdown for today
        model_breakdown = {}
        for call in recent_calls:
            if call.model not in model_breakdown:
                model_breakdown[call.model] = {'calls': 0, 'tokens': 0, 'cost': 0.0}
            model_breakdown[call.model]['calls'] += 1
            model_breakdown[call.model]['tokens'] += call.input_tokens + call.output_tokens
            model_breakdown[call.model]['cost'] += call.cost
        
        # Average response time
        avg_duration = sum(call.duration for call in recent_calls) / len(recent_calls) if recent_calls else 0
        
        return {
            'session': self.session_stats,
            'today': {
                'calls': total_calls_today,
                'tokens': total_tokens_today,
                'cost': total_cost_today,
                'avg_duration': avg_duration
            },
            'models': model_breakdown,
            'last_call': recent_calls[0] if recent_calls else None
        }
    
    def format_ui_summary(self) -> list:
        """Format monitoring data for UI display"""
        metrics = self.get_real_time_metrics()
        lines = []
        
        # Session statistics
        lines.append("📊 SESSION STATISTICS")
        lines.append(f"   Calls: {metrics['session']['calls']}")
        lines.append(f"   Tokens: {metrics['session']['tokens']:,}")
        lines.append(f"   Cost: ${metrics['session']['cost']:.4f}")
        
        session_duration = (datetime.datetime.now() - self.session_stats['start_time']).total_seconds() / 60
        lines.append(f"   Duration: {session_duration:.1f} min")
        lines.append("")
        
        # Today's statistics
        lines.append("📈 TODAY'S USAGE")
        lines.append(f"   Total Calls: {metrics['today']['calls']}")
        lines.append(f"   Total Tokens: {metrics['today']['tokens']:,}")
        lines.append(f"   Total Cost: ${metrics['today']['cost']:.4f}")
        lines.append(f"   Avg Response: {metrics['today']['avg_duration']:.2f}s")
        lines.append("")
        
        # Model breakdown
        if metrics['models']:
            lines.append("🤖 MODEL USAGE TODAY")
            for model, data in sorted(metrics['models'].items(), key=lambda x: x[1]['cost'], reverse=True):
                lines.append(f"   {model}:")
                lines.append(f"     • {data['calls']} calls, {data['tokens']:,} tokens")
                lines.append(f"     • ${data['cost']:.4f}")
            lines.append("")
        
        # Last call info
        if metrics['last_call']:
            last_call = metrics['last_call']
            time_ago = (datetime.datetime.now() - last_call.timestamp).total_seconds()
            if time_ago < 60:
                time_str = f"{time_ago:.0f}s ago"
            elif time_ago < 3600:
                time_str = f"{time_ago/60:.0f}m ago"
            else:
                time_str = f"{time_ago/3600:.1f}h ago"
            
            lines.append("🔍 LAST API CALL")
            lines.append(f"   Model: {last_call.model}")
            lines.append(f"   Tokens: {last_call.input_tokens + last_call.output_tokens:,}")
            lines.append(f"   Cost: ${last_call.cost:.4f}")
            lines.append(f"   Time: {time_str}")
        
        return lines
    
    def reset_session_stats(self):
        """Reset session statistics"""
        self.session_stats = {
            'calls': 0,
            'tokens': 0,
            'cost': 0.0,
            'start_time': datetime.datetime.now()
        }
        self._trigger_ui_update()

def create_sample_data(monitor: MasterMonitoring, days: int = 7):
    """Create sample API call data for demonstration"""
    print(f"Creating sample data for last {days} days...")
    
    models = ['gpt-4o-mini', 'gpt-4o', 'gpt-4o-mini']
    task_types = ['code_generation', 'debugging', 'explanation', 'optimization']
    
    # Generate sample data
    base_time = datetime.datetime.now() - datetime.timedelta(days=days)
    
    for day in range(days):
        # Random number of calls per day (1-5)
        num_calls = np.random.randint(1, 6) if VISUALIZATION_AVAILABLE else 3
        
        for call_num in range(num_calls):
            # Random time during the day
            call_time = base_time + datetime.timedelta(
                days=day,
                hours=np.random.randint(8, 20) if VISUALIZATION_AVAILABLE else 12,
                minutes=np.random.randint(0, 60) if VISUALIZATION_AVAILABLE else 30
            )
            
            # Random model selection (bias toward gpt-4o-mini)
            model = models[np.random.randint(0, len(models))] if VISUALIZATION_AVAILABLE else 'gpt-4o-mini'
            
            # Random token counts based on model
            if 'mini' in model:
                input_tokens = np.random.randint(500, 3000) if VISUALIZATION_AVAILABLE else 1500
                output_tokens = np.random.randint(200, 1500) if VISUALIZATION_AVAILABLE else 800
            else:
                input_tokens = np.random.randint(1000, 5000) if VISUALIZATION_AVAILABLE else 2500
                output_tokens = np.random.randint(500, 2000) if VISUALIZATION_AVAILABLE else 1200
            
            duration = np.random.uniform(0.5, 3.0) if VISUALIZATION_AVAILABLE else 1.5
            task_type = task_types[np.random.randint(0, len(task_types))] if VISUALIZATION_AVAILABLE else 'code_generation'
            
            # Create API call record with the specific timestamp
            api_call = APICall(
                timestamp=call_time,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=0,
                duration=duration,
                cost=monitor.calculate_cost(model, input_tokens, output_tokens),
                task_type=task_type,
                success=True
            )
            
            monitor.db.record_api_call(api_call)
    
    print(f"Sample data created: {days * 3} API calls")

def main():
    """Main function to run the monitoring utility"""
    print("MASTER MONITORING UTILITY")
    print("=" * 50)
    
    # Initialize monitoring
    monitor = MasterMonitoring()
    
    # Clean up deprecated files
    cleanup_results = monitor.cleanup_deprecated_files()
    for result in cleanup_results:
        if "Could not remove" in result:
            print(f"Warning: {result}")
    
    # Check integration status
    print("\nINTEGRATION STATUS:")
    integration_status = monitor.check_integration_status()
    for status in integration_status:
        print(f"   {status}")
    
    # Check if we have any data
    total_calls = monitor.db.get_total_calls()
    
    if total_calls == 0:
        print(f"\nNo API call data found. Creating sample data for demonstration...")
        create_sample_data(monitor, days=7)
        total_calls = monitor.db.get_total_calls()
    
    print(f"\nGENERATING REPORTS:")
    
    # Generate text report
    report = monitor.generate_usage_report(30)
    print(report)
    
    # Generate charts if matplotlib is available
    if VISUALIZATION_AVAILABLE:
        print(f"\nGENERATING CHARTS:")
        
        chart_result = monitor.generate_usage_chart(30)
        print(f"   {chart_result}")
        
        comparison_result = monitor.generate_model_comparison_chart(30)
        print(f"   {comparison_result}")
    else:
        print(f"\nCHARTS:")
        print("   Install matplotlib and numpy to generate usage charts")
        print("   Run: pip install matplotlib numpy")
    
    print(f"\nMONITORING SETUP COMPLETE!")
    print("=" * 50)
    print("To integrate with your existing code:")
    print("1. Import: from master_monitoring import MasterMonitoring")
    print("2. Initialize: monitor = MasterMonitoring()")
    print("3. Record calls: monitor.record_api_call(model, input_tokens, output_tokens, duration)")
    print("4. Generate reports: monitor.generate_usage_report()")

if __name__ == "__main__":
    main()
