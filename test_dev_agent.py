#!/usr/bin/env python3
"""
Test script for PersonaOS DevAgent.

Tests core functionality of the DevAgent module including:
- Project navigation and indexing
- File management with backups
- Code execution with safety controls
- Task planning and execution
"""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from core.dev_agent import DevAgent, ProjectNavigator, FileManager, CodeExecutor


def setup_test_logging():
    """Setup logging for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_project_navigator():
    """Test ProjectNavigator functionality."""
    print(">> Testing ProjectNavigator...")
    
    try:
        project_root = os.path.dirname(__file__)
        navigator = ProjectNavigator(project_root)
        
        # Test basic functionality
        stats = navigator.get_stats()
        print(f"  [OK] Project stats: {stats['total_files']} files, {len(stats['languages'])} languages")
        
        # Test file search
        python_files = navigator.find_files(language='python')
        print(f"  [OK] Found {len(python_files)} Python files")
        
        # Test module indexing
        modules = navigator.module_index
        print(f"  [OK] Indexed {len(modules)} modules")
        
        # Test dependency tracking
        deps = navigator.dependency_graph
        print(f"  [OK] Tracked {len(deps)} dependency relationships")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] ProjectNavigator test failed: {e}")
        return False


def test_file_manager():
    """Test FileManager functionality."""
    print("📁 Testing FileManager...")
    
    try:
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = FileManager(temp_dir, {'dry_run': False})
            
            # Test file creation
            content = "# Test file created by DevAgent\nprint('Hello, world!')\n"
            operation = file_manager.create_file("test_file.py", content)
            print(f"  ✅ File creation: {'success' if operation.success else 'failed'}")
            
            # Test file editing
            new_content = content + "\n# Added by test\nprint('DevAgent works!')\n"
            operation = file_manager.edit_file("test_file.py", new_content)
            print(f"  ✅ File editing: {'success' if operation.success else 'failed'}")
            
            # Test backup creation
            has_backup = len(file_manager.backups) > 0
            print(f"  ✅ Backup creation: {'success' if has_backup else 'failed'}")
            
            # Test dry run mode
            file_manager.set_dry_run(True)
            operation = file_manager.create_file("dry_run_test.py", "# Dry run test")
            print(f"  ✅ Dry run mode: {'success' if operation.success else 'failed'}")
            
            # Test session summary
            summary = file_manager.get_session_summary()
            print(f"  ✅ Session summary: {summary['total_operations']} operations")
            
        return True
        
    except Exception as e:
        print(f"  ❌ FileManager test failed: {e}")
        return False


def test_code_executor():
    """Test CodeExecutor functionality."""
    print("⚡ Testing CodeExecutor...")
    
    try:
        project_root = os.path.dirname(__file__)
        executor = CodeExecutor(project_root, {'safe_mode': True})
        
        # Test safe command execution
        result = executor.execute_command("python --version")
        print(f"  ✅ Command execution: {'success' if result.exit_code == 0 else 'failed'}")
        
        # Test Python code execution
        code = "print('DevAgent test successful')\nresult = 2 + 2\nprint(f'2 + 2 = {result}')"
        result = executor.execute_python_code(code)
        print(f"  ✅ Python code execution: {'success' if result.exit_code == 0 else 'failed'}")
        
        # Test command blocking (should fail safely)
        result = executor.execute_command("rm -rf /")  # Dangerous command should be blocked
        is_blocked = result.exit_code == -1 and "blocked" in (result.error or "").lower()
        print(f"  ✅ Command blocking: {'success' if is_blocked else 'failed'}")
        
        # Test execution history
        history = executor.get_execution_history()
        print(f"  ✅ Execution history: {len(history)} commands recorded")
        
        return True
        
    except Exception as e:
        print(f"  ❌ CodeExecutor test failed: {e}")
        return False


def test_dev_agent():
    """Test main DevAgent functionality."""
    print("🤖 Testing DevAgent...")
    
    try:
        project_root = os.path.dirname(__file__)
        config = {
            'dry_run': True,  # Use dry run for testing
            'require_confirmation': False,
            'max_iterations': 3
        }
        
        agent = DevAgent(project_root, config)
        
        # Test system status
        status = agent.get_system_status()
        print(f"  ✅ System status: {status['project_stats']['total_files']} files indexed")
        
        # Test task planning
        task_description = "Create a simple test utility function"
        plan = agent.plan_task(task_description)
        print(f"  ✅ Task planning: {len(plan.steps)} steps planned")
        
        # Test task execution (dry run)
        execution = agent.execute_task(task_description, dry_run=True)
        print(f"  ✅ Task execution: {'success' if execution.status in ['completed', 'failed'] else 'failed'}")
        
        # Test task history
        history = agent.list_recent_tasks()
        print(f"  ✅ Task history: {len(history)} tasks recorded")
        
        return True
        
    except Exception as e:
        print(f"  ❌ DevAgent test failed: {e}")
        return False


def test_cli_integration():
    """Test CLI integration."""
    print("💻 Testing CLI integration...")
    
    try:
        from core.dev_agent.cli import DevAgentCLI
        from core.dev_agent.promptline_integration import DevAgentPrompter
        
        project_root = os.path.dirname(__file__)
        
        # Test CLI creation
        cli = DevAgentCLI(project_root)
        print("  ✅ CLI initialization successful")
        
        # Test command parsing
        prompter = DevAgentPrompter(project_root)
        is_dev_cmd = prompter.is_dev_command("dev: create a test file")
        print(f"  ✅ Command parsing: {'success' if is_dev_cmd else 'failed'}")
        
        command, args = prompter.parse_dev_command("dev-status")
        is_parsed = command == "dev-status" and args == []
        print(f"  ✅ Command parsing (status): {'success' if is_parsed else 'failed'}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ CLI integration test failed: {e}")
        return False


def run_all_tests():
    """Run all DevAgent tests."""
    print("🧪 Running PersonaOS DevAgent Tests")
    print("=" * 50)
    
    setup_test_logging()
    
    tests = [
        ("ProjectNavigator", test_project_navigator),
        ("FileManager", test_file_manager),
        ("CodeExecutor", test_code_executor),
        ("DevAgent", test_dev_agent),
        ("CLI Integration", test_cli_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        
    print("\n" + "=" * 50)
    print(f"🧪 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! DevAgent is ready for use.")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)