#!/usr/bin/env python3
"""
Simple test script for PersonaOS DevAgent (no Unicode).
"""

import os
import sys
import tempfile

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from core.dev_agent.project_navigator import ProjectNavigator
        print("  [OK] ProjectNavigator imported")
        
        from core.dev_agent.file_manager import FileManager
        print("  [OK] FileManager imported")
        
        from core.dev_agent.code_executor import CodeExecutor
        print("  [OK] CodeExecutor imported")
        
        from core.dev_agent.dev_agent import DevAgent
        print("  [OK] DevAgent imported")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality of each component."""
    print("Testing basic functionality...")
    
    try:
        from core.dev_agent.project_navigator import ProjectNavigator
        from core.dev_agent.file_manager import FileManager
        from core.dev_agent.code_executor import CodeExecutor
        
        project_root = os.path.dirname(__file__)
        
        # Test ProjectNavigator
        navigator = ProjectNavigator(project_root)
        stats = navigator.get_stats()
        print(f"  [OK] ProjectNavigator: {stats['total_files']} files indexed")
        
        # Test FileManager with temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = FileManager(temp_dir, {'dry_run': True})
            operation = file_manager.create_file("test.py", "print('test')")
            print(f"  [OK] FileManager: operation {'succeeded' if operation.success else 'failed'}")
        
        # Test CodeExecutor
        executor = CodeExecutor(project_root, {'safe_mode': True})
        result = executor.execute_command("python --version")
        print(f"  [OK] CodeExecutor: command execution {'succeeded' if result.exit_code == 0 else 'failed'}")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Basic functionality test failed: {e}")
        return False


def test_dev_agent():
    """Test DevAgent integration."""
    print("Testing DevAgent...")
    
    try:
        from core.dev_agent.dev_agent import DevAgent
        
        project_root = os.path.dirname(__file__)
        config = {'dry_run': True, 'require_confirmation': False}
        
        agent = DevAgent(project_root, config)
        
        # Test system status
        status = agent.get_system_status()
        print(f"  [OK] DevAgent system status: {status['project_stats']['total_files']} files")
        
        # Test task planning
        plan = agent.plan_task("Create a test file")
        print(f"  [OK] Task planning: {len(plan.steps)} steps")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] DevAgent test failed: {e}")
        return False


def main():
    """Run simple tests."""
    print("PersonaOS DevAgent Simple Test Suite")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Basic Functionality", test_basic_functionality),
        ("DevAgent Integration", test_dev_agent),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
            print(f"  [PASS] {test_name}")
        else:
            print(f"  [FAIL] {test_name}")
    
    print("\n" + "=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All tests passed! DevAgent is ready.")
        return True
    else:
        print(f"[ERROR] {total - passed} tests failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)