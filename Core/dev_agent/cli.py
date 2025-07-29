"""
Command-line interface for PersonaOS DevAgent.

Provides interactive CLI for autonomous development tasks.
Integrates with existing PersonaOS CLI system.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import argparse
from datetime import datetime

from .dev_agent import DevAgent
from ..config import load_config


class DevAgentCLI:
    """
    Command-line interface for DevAgent.
    
    Provides interactive commands for autonomous development tasks:
    - dev: Execute development task
    - dev-status: Show current task status
    - dev-history: Show task history
    - dev-rollback: Rollback task changes
    - dev-cancel: Cancel current task
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd()).resolve()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load PersonaOS configuration
        try:
            self.config = load_config()
        except Exception as e:
            self.logger.warning(f"Failed to load PersonaOS config: {e}")
            self.config = {}
        
        # Initialize DevAgent
        self.agent = None
        self._init_agent()
    
    def _init_agent(self) -> None:
        """Initialize DevAgent instance."""
        try:
            agent_config = {
                'dry_run': False,
                'require_confirmation': True,
                'max_iterations': 5
            }
            
            self.agent = DevAgent(str(self.project_root), agent_config)
            self.logger.info("DevAgent CLI initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DevAgent: {e}")
            print(f"Error: Failed to initialize DevAgent: {e}")
            sys.exit(1)
    
    def handle_dev_command(self, args: List[str]) -> int:
        """Handle 'dev:' command for task execution."""
        if not args:
            print("Usage: dev: <task description>")
            print("Example: dev: Add a plugin loader registry")
            return 1
        
        task_description = " ".join(args)
        print(f"🤖 DevAgent: Executing task - {task_description}")
        
        try:
            # Check if another task is running
            current_status = self.agent.get_task_status()
            if current_status and current_status['status'] == 'in_progress':
                print(f"❌ Another task is already in progress: {current_status['task_id']}")
                print("Use 'dev-cancel' to cancel it or wait for completion.")
                return 1
            
            # Execute task
            execution = self.agent.execute_task(task_description)
            
            # Show results
            self._print_task_result(execution)
            
            return 0 if execution.success else 1
            
        except Exception as e:
            print(f"❌ Task execution failed: {e}")
            self.logger.error(f"Task execution error: {e}")
            return 1
    
    def handle_dev_status_command(self, args: List[str]) -> int:
        """Handle 'dev-status' command."""
        task_id = args[0] if args else None
        
        try:
            status = self.agent.get_task_status(task_id)
            
            if not status:
                if task_id:
                    print(f"❌ Task not found: {task_id}")
                else:
                    print("ℹ️  No current task")
                return 1
            
            self._print_task_status(status)
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get task status: {e}")
            return 1
    
    def handle_dev_history_command(self, args: List[str]) -> int:
        """Handle 'dev-history' command."""
        try:
            limit = int(args[0]) if args else 10
            tasks = self.agent.list_recent_tasks(limit)
            
            if not tasks:
                print("ℹ️  No task history available")
                return 0
            
            print(f"📋 Recent Tasks (last {len(tasks)}):")
            print("-" * 80)
            
            for task in reversed(tasks):  # Show newest first
                status_icon = "✅" if task['success'] else "❌"
                duration = f"{task['duration']:.1f}s" if task['duration'] else "running"
                
                print(f"{status_icon} {task['task_id']}")
                print(f"   Description: {task['description'][:60]}{'...' if len(task['description']) > 60 else ''}")
                print(f"   Status: {task['status']} | Duration: {duration} | Errors: {task['error_count']}")
                print(f"   Started: {datetime.fromtimestamp(task['start_time']).strftime('%Y-%m-%d %H:%M:%S')}")
                print()
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get task history: {e}")
            return 1
    
    def handle_dev_rollback_command(self, args: List[str]) -> int:
        """Handle 'dev-rollback' command."""
        if not args:
            print("Usage: dev-rollback <task_id>")
            return 1
        
        task_id = args[0]
        
        try:
            print(f"🔄 Rolling back task: {task_id}")
            success = self.agent.rollback_task(task_id)
            
            if success:
                print(f"✅ Task {task_id} rolled back successfully")
                return 0
            else:
                print(f"❌ Failed to rollback task {task_id}")
                return 1
                
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return 1
    
    def handle_dev_cancel_command(self, args: List[str]) -> int:
        """Handle 'dev-cancel' command."""
        try:
            success = self.agent.cancel_current_task()
            
            if success:
                print("✅ Current task cancelled successfully")
                return 0
            else:
                print("ℹ️  No task to cancel")
                return 0
                
        except Exception as e:
            print(f"❌ Failed to cancel task: {e}")
            return 1
    
    def handle_dev_system_command(self, args: List[str]) -> int:
        """Handle 'dev-system' command to show system status."""
        try:
            status = self.agent.get_system_status()
            
            print("🖥️  DevAgent System Status")
            print("=" * 50)
            print(f"Project Root: {status['project_root']}")
            print(f"LLM Available: {'✅' if status['llm_available'] else '❌'}")
            print(f"Current Task: {status['current_task'] or 'None'}")
            print(f"Task History: {status['task_history_count']} tasks")
            print(f"Dry Run Mode: {'✅' if status['dry_run_mode'] else '❌'}")
            print()
            
            print("📊 Project Statistics:")
            stats = status['project_stats']
            print(f"  Total Files: {stats['total_files']}")
            print(f"  Languages: {', '.join(stats['languages'].keys())}")
            print(f"  Total Size: {stats['total_size']:,} bytes")
            print()
            
            print("📁 File Manager:")
            fm_status = status['file_manager_status']
            print(f"  Session ID: {fm_status['session_id']}")
            print(f"  Operations: {fm_status['total_operations']} ({fm_status['successful_operations']} successful)")
            print(f"  Backup Files: {fm_status['backup_files']}")
            print()
            
            print("⚡ Code Executor:")
            exec_status = status['executor_status']
            print(f"  Active Processes: {exec_status['active_processes']}")
            print(f"  Execution History: {exec_status['execution_history']}")
            print(f"  Safe Mode: {'✅' if exec_status['safe_mode'] else '❌'}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Failed to get system status: {e}")
            return 1
    
    def _print_task_result(self, execution) -> None:
        """Print task execution results."""
        if execution.success:
            print("✅ Task completed successfully!")
        else:
            print("❌ Task failed!")
        
        print(f"📋 Task ID: {execution.task_id}")
        print(f"⏱️  Duration: {execution.end_time - execution.start_time:.1f}s")
        print(f"📝 Steps Completed: {len(execution.steps_completed)}/{len(execution.plan.steps)}")
        print(f"📄 File Operations: {len(execution.file_operations)}")
        print(f"⚡ Commands Run: {len(execution.command_results)}")
        
        if execution.errors:
            print(f"❌ Errors ({len(execution.errors)}):")
            for error in execution.errors[:3]:  # Show first 3 errors
                print(f"   • {error}")
            if len(execution.errors) > 3:
                print(f"   ... and {len(execution.errors) - 3} more errors")
        
        # Show file changes if any
        successful_ops = [op for op in execution.file_operations if op.success]
        if successful_ops:
            print(f"📁 Files Changed ({len(successful_ops)}):")
            for op in successful_ops[:5]:  # Show first 5 operations
                print(f"   • {op.operation_type}: {op.target_path}")
            if len(successful_ops) > 5:
                print(f"   ... and {len(successful_ops) - 5} more files")
    
    def _print_task_status(self, status: Dict[str, Any]) -> None:
        """Print detailed task status."""
        status_icon = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫'
        }.get(status['status'], '❓')
        
        print(f"{status_icon} Task Status: {status['status'].upper()}")
        print(f"📋 Task ID: {status['task_id']}")
        print(f"📝 Description: {status['description']}")
        
        if status['start_time']:
            start_time = datetime.fromtimestamp(status['start_time'])
            print(f"⏰ Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if status['end_time']:
            end_time = datetime.fromtimestamp(status['end_time'])
            duration = status['end_time'] - status['start_time']
            print(f"🏁 Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')} ({duration:.1f}s)")
        
        print(f"📊 Progress: {status['steps_completed']}/{status['total_steps']} steps")
        print(f"📄 File Operations: {status['file_operations']}")
        print(f"⚡ Commands Run: {status['command_results']}")
        
        if status['errors']:
            print(f"❌ Errors ({len(status['errors'])}):")
            for error in status['errors'][:3]:
                print(f"   • {error}")
            if len(status['errors']) > 3:
                print(f"   ... and {len(status['errors']) - 3} more errors")


def create_dev_agent_cli(project_root: str = None) -> DevAgentCLI:
    """Factory function to create DevAgent CLI instance."""
    return DevAgentCLI(project_root)


def handle_dev_command_dispatch(command: str, args: List[str], project_root: str = None) -> int:
    """
    Dispatch dev commands to appropriate handlers.
    
    This function can be called from PersonaOS main CLI to handle dev commands.
    """
    try:
        cli = create_dev_agent_cli(project_root)
        
        if command == "dev":
            return cli.handle_dev_command(args)
        elif command == "dev-status":
            return cli.handle_dev_status_command(args)
        elif command == "dev-history":
            return cli.handle_dev_history_command(args)
        elif command == "dev-rollback":
            return cli.handle_dev_rollback_command(args)
        elif command == "dev-cancel":
            return cli.handle_dev_cancel_command(args)
        elif command == "dev-system":
            return cli.handle_dev_system_command(args)
        else:
            print(f"Unknown dev command: {command}")
            print("Available commands: dev, dev-status, dev-history, dev-rollback, dev-cancel, dev-system")
            return 1
            
    except Exception as e:
        print(f"❌ DevAgent CLI error: {e}")
        return 1


def main():
    """Main entry point for standalone CLI usage."""
    parser = argparse.ArgumentParser(description="PersonaOS DevAgent CLI")
    parser.add_argument("command", help="Command to execute")
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument("--project", help="Project root directory")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    exit_code = handle_dev_command_dispatch(args.command, args.args, args.project)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()