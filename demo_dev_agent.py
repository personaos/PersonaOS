#!/usr/bin/env python3
"""
DevAgent demonstration script for PersonaOS.

Shows how to use the DevAgent for autonomous development tasks.
"""

import os
import sys

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from core.dev_agent.dev_agent import DevAgent
from core.dev_agent.cli import DevAgentCLI
from core.dev_agent.promptline_integration import DevAgentPrompter


def demo_dev_agent_basic():
    """Demonstrate basic DevAgent usage."""
    print("=== DevAgent Basic Usage Demo ===")
    
    # Initialize DevAgent
    project_root = os.path.dirname(__file__)
    config = {
        'dry_run': True,  # Safe mode for demo
        'require_confirmation': False,
        'max_iterations': 3
    }
    
    agent = DevAgent(project_root, config)
    
    # Show system status
    print("\n1. System Status:")
    status = agent.get_system_status()
    print(f"   Project: {status['project_root']}")
    print(f"   Files indexed: {status['project_stats']['total_files']}")
    print(f"   Languages: {', '.join(status['project_stats']['languages'].keys())}")
    print(f"   LLM available: {status['llm_available']}")
    
    # Plan a development task
    print("\n2. Task Planning:")
    task_description = "Add a logging utility module with different log levels"
    plan = agent.plan_task(task_description)
    print(f"   Task: {task_description}")
    print(f"   Steps planned: {len(plan.steps)}")
    for i, step in enumerate(plan.steps, 1):
        print(f"     {i}. {step}")
    print(f"   Files to create: {plan.files_to_create}")
    print(f"   Files to modify: {plan.files_to_modify}")
    print(f"   Commands to run: {plan.commands_to_run}")
    
    # Execute the task (dry run)
    print("\n3. Task Execution (Dry Run):")
    execution = agent.execute_task(task_description, dry_run=True)
    print(f"   Task ID: {execution.task_id}")
    print(f"   Status: {execution.status}")
    print(f"   Steps completed: {len(execution.steps_completed)}/{len(execution.plan.steps)}")
    print(f"   File operations: {len(execution.file_operations)}")
    print(f"   Commands run: {len(execution.command_results)}")
    if execution.errors:
        print(f"   Errors: {len(execution.errors)}")
        for error in execution.errors[:2]:
            print(f"     - {error}")
    
    # Show task history
    print("\n4. Task History:")
    history = agent.list_recent_tasks(limit=3)
    for task in history:
        print(f"   {task['task_id']}: {task['status']} - {task['description'][:50]}...")
    
    return agent


def demo_cli_integration():
    """Demonstrate CLI integration."""
    print("\n=== CLI Integration Demo ===")
    
    project_root = os.path.dirname(__file__)
    prompter = DevAgentPrompter(project_root)
    
    # Test command recognition
    test_inputs = [
        "dev: create a simple calculator function",
        "dev-status",
        "dev-history 5",
        "help me with something else",
        "dev help"
    ]
    
    print("\nCommand Recognition:")
    for input_text in test_inputs:
        is_dev_cmd = prompter.is_dev_command(input_text)
        print(f"   '{input_text}' -> {'DevAgent command' if is_dev_cmd else 'Regular input'}")
    
    # Parse commands
    print("\nCommand Parsing:")
    dev_commands = [cmd for cmd in test_inputs if prompter.is_dev_command(cmd)]
    for cmd in dev_commands:
        command, args = prompter.parse_dev_command(cmd)
        print(f"   '{cmd}' -> command='{command}', args={args}")
    
    # Show help
    print("\nDevAgent Help:")
    help_text = prompter.get_dev_help()
    print(help_text)


def demo_project_navigation():
    """Demonstrate project navigation capabilities."""
    print("\n=== Project Navigation Demo ===")
    
    project_root = os.path.dirname(__file__)
    
    # Initialize DevAgent to get navigator
    agent = DevAgent(project_root, {'dry_run': True})
    navigator = agent.navigator
    
    # Show project statistics
    print("\n1. Project Statistics:")
    stats = navigator.get_stats()
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total modules: {stats['total_modules']}")
    print(f"   Total size: {stats['total_size']:,} bytes")
    print(f"   Languages:")
    for lang, count in stats['languages'].items():
        print(f"     {lang}: {count} files")
    
    # Search for Python files
    print("\n2. File Search (Python files):")
    python_files = navigator.find_files(language='python')[:5]
    for file_info in python_files:
        print(f"   {file_info.path} ({file_info.size} bytes)")
        if file_info.classes:
            print(f"     Classes: {', '.join(file_info.classes[:3])}")
        if file_info.functions:
            print(f"     Functions: {', '.join(file_info.functions[:3])}")
    
    # Show modules
    print("\n3. Module Index (first 5):")
    modules = list(navigator.module_index.items())[:5]
    for module_name, module_info in modules:
        print(f"   {module_name}:")
        print(f"     Files: {len(module_info.files)}")
        print(f"     Dependencies: {len(module_info.dependencies)}")
        if module_info.description:
            print(f"     Description: {module_info.description[:60]}...")
    
    # Show dependencies for a specific file
    print("\n4. Dependencies (core/dev_agent/dev_agent.py):")
    target_file = "core/dev_agent/dev_agent.py"
    if target_file in navigator.file_index:
        deps = navigator.get_dependencies(target_file)
        print(f"   Direct dependencies: {len(deps)}")
        for dep in list(deps)[:5]:
            print(f"     - {dep}")
        
        related = navigator.get_related_files(target_file, depth=1)
        print(f"   Related files: {len(related)}")
        for rel_file in list(related)[:3]:
            print(f"     - {rel_file}")


def main():
    """Run DevAgent demonstration."""
    print("PersonaOS DevAgent Demonstration")
    print("=" * 50)
    
    try:
        # Basic DevAgent demo
        agent = demo_dev_agent_basic()
        
        # CLI integration demo
        demo_cli_integration()
        
        # Project navigation demo
        demo_project_navigation()
        
        print("\n" + "=" * 50)
        print("DevAgent demonstration completed successfully!")
        print("\nTo use DevAgent in PersonaOS:")
        print("1. Run: python core/main.py")
        print("2. Type: dev: <your task description>")
        print("3. Or use: dev-status, dev-history, dev-system, etc.")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)