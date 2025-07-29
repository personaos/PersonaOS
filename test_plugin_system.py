"""
Comprehensive Plugin System Test Suite

This script provides comprehensive testing and validation of the PersonaOS
plugin system including all components and integrations.
"""

import sys
import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import traceback
import time

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("plugin_system_test")

class PluginSystemTester:
    """
    Comprehensive tester for the PersonaOS plugin system.
    
    Tests all major components and integration points:
    - Plugin discovery and loading
    - Plugin lifecycle management
    - Security and sandboxing
    - Tool integration
    - System integration
    """
    
    def __init__(self):
        """Initialize the plugin system tester."""
        self.test_results = []
        self.failed_tests = []
        self.passed_tests = []
        
        # Test configuration
        self.test_config = {
            "plugin_system_enabled": True,
            "plugin_auto_load": True,
            "plugin_security_enabled": True,
            "plugin_sandboxing_enabled": True,
            "plugin_directories": ["plugins"],
            "debug_mode": True,
            "log_level": "INFO"
        }
        
        logger.info("PluginSystemTester initialized")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all plugin system tests."""
        logger.info("Starting comprehensive plugin system tests")
        start_time = time.time()
        
        try:
            # Test 1: Import Tests
            self.test_imports()
            
            # Test 2: Component Initialization Tests
            self.test_component_initialization()
            
            # Test 3: Plugin Discovery Tests
            self.test_plugin_discovery()
            
            # Test 4: Plugin Loading Tests
            self.test_plugin_loading()
            
            # Test 5: Plugin Lifecycle Tests
            self.test_plugin_lifecycle()
            
            # Test 6: Security Integration Tests
            self.test_security_integration()
            
            # Test 7: Tool Integration Tests
            self.test_tool_integration()
            
            # Test 8: System Integration Tests
            self.test_system_integration()
            
            # Test 9: CLI Interface Tests
            self.test_cli_interface()
            
            # Test 10: Web API Tests (basic validation)
            self.test_web_api_structure()
            
            # Test 11: Example Plugin Tests
            self.test_example_plugin()
            
            end_time = time.time()
            
            # Generate final report
            return self.generate_test_report(end_time - start_time)
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "total_tests": len(self.test_results),
                "passed": len(self.passed_tests),
                "failed": len(self.failed_tests)
            }
    
    def test_imports(self):
        """Test that all plugin system modules can be imported."""
        logger.info("Testing plugin system imports...")
        
        import_tests = [
            ("core.plugins", "Main plugin package"),
            ("core.plugins.base_plugin", "Base plugin classes"),
            ("core.plugins.plugin_manager", "Plugin manager"),
            ("core.plugins.plugin_registry", "Plugin registry"),
            ("core.plugins.plugin_loader", "Plugin loader"),
            ("core.plugins.plugin_scanner", "Plugin scanner"),
            ("core.plugins.security_manager", "Security manager"),
            ("core.plugins.sandbox_controller", "Sandbox controller"),
            ("core.plugins.plugin_tool_bridge", "Tool bridge"),
            ("core.plugins.system_integration_manager", "System integration"),
            ("core.plugins.plugin_cli_manager", "CLI manager"),
            ("core.plugins.plugin_web_api", "Web API"),
        ]
        
        for module_name, description in import_tests:
            try:
                __import__(module_name)
                self.record_test_result(f"Import {module_name}", True, description)
            except Exception as e:
                self.record_test_result(f"Import {module_name}", False, f"Import failed: {e}")
    
    def test_component_initialization(self):
        """Test that all major components can be initialized."""
        logger.info("Testing component initialization...")
        
        try:
            # Test PluginManager initialization
            from core.plugins.plugin_manager import PluginManager
            plugin_manager = PluginManager(self.test_config)
            self.record_test_result("PluginManager init", True, "Successfully initialized")
            
            # Test initialization
            init_result = plugin_manager.initialize()
            self.record_test_result("PluginManager initialize", 
                                  init_result.get("success", False), 
                                  init_result.get("message", "Unknown"))
            
            # Test SecurityManager initialization
            from core.plugins.security_manager import SecurityManager
            security_manager = SecurityManager(self.test_config)
            self.record_test_result("SecurityManager init", True, "Successfully initialized")
            
            # Test SandboxController initialization
            from core.plugins.sandbox_controller import SandboxController
            sandbox_controller = SandboxController(self.test_config)
            self.record_test_result("SandboxController init", True, "Successfully initialized")
            
            # Test SystemIntegrationManager initialization
            from core.plugins.system_integration_manager import SystemIntegrationManager
            integration_manager = SystemIntegrationManager(self.test_config)
            self.record_test_result("SystemIntegrationManager init", True, "Successfully initialized")
            
        except Exception as e:
            self.record_test_result("Component initialization", False, f"Failed: {e}")
    
    def test_plugin_discovery(self):
        """Test plugin discovery functionality."""
        logger.info("Testing plugin discovery...")
        
        try:
            from core.plugins.plugin_scanner import PluginScanner
            
            scanner = PluginScanner(self.test_config)
            
            # Test directory scanning
            plugins = scanner.scan_all_plugins()
            plugin_count = len(plugins)
            
            self.record_test_result("Plugin discovery", plugin_count > 0, 
                                  f"Found {plugin_count} plugin(s)")
            
            # Test validation of discovered plugins
            valid_plugins = [p for p in plugins if p.get("validation_result", {}).get("valid", False)]
            self.record_test_result("Plugin validation", len(valid_plugins) > 0,
                                  f"Validated {len(valid_plugins)}/{plugin_count} plugins")
            
        except Exception as e:
            self.record_test_result("Plugin discovery", False, f"Discovery failed: {e}")
    
    def test_plugin_loading(self):
        """Test plugin loading functionality."""
        logger.info("Testing plugin loading...")
        
        try:
            from core.plugins.plugin_manager import PluginManager
            
            plugin_manager = PluginManager(self.test_config)
            plugin_manager.initialize()
            
            # Test discovery and loading
            load_result = plugin_manager.loader.discover_and_load_all_plugins()
            
            success = load_result.get("success", False)
            loaded_count = load_result.get("loaded_count", 0)
            
            self.record_test_result("Plugin loading", success and loaded_count > 0,
                                  f"Loaded {loaded_count} plugin(s)")
            
            # Test plugin listing
            plugins = plugin_manager.list_plugins()
            self.record_test_result("Plugin listing", len(plugins) == loaded_count,
                                  f"Listed {len(plugins)} plugin(s)")
            
        except Exception as e:
            self.record_test_result("Plugin loading", False, f"Loading failed: {e}")
    
    def test_plugin_lifecycle(self):
        """Test plugin lifecycle management."""
        logger.info("Testing plugin lifecycle...")
        
        try:
            from core.plugins.plugin_manager import PluginManager
            
            plugin_manager = PluginManager(self.test_config)
            plugin_manager.initialize()
            
            # Load plugins first
            load_result = plugin_manager.loader.discover_and_load_all_plugins()
            if not load_result.get("success", False):
                self.record_test_result("Plugin lifecycle", False, "No plugins to test lifecycle")
                return
            
            plugins = plugin_manager.list_plugins()
            if not plugins:
                self.record_test_result("Plugin lifecycle", False, "No plugins loaded for lifecycle test")
                return
            
            test_plugin_id = plugins[0]
            
            # Test activation
            activate_result = plugin_manager.activate_plugin(test_plugin_id)
            self.record_test_result("Plugin activation", activate_result,
                                  f"Plugin {test_plugin_id} activation")
            
            # Test deactivation
            deactivate_result = plugin_manager.deactivate_plugin(test_plugin_id)
            self.record_test_result("Plugin deactivation", deactivate_result,
                                  f"Plugin {test_plugin_id} deactivation")
            
            # Test unloading
            unload_result = plugin_manager.unload_plugin(test_plugin_id)
            self.record_test_result("Plugin unloading", unload_result,
                                  f"Plugin {test_plugin_id} unloading")
            
        except Exception as e:
            self.record_test_result("Plugin lifecycle", False, f"Lifecycle test failed: {e}")
    
    def test_security_integration(self):
        """Test security and sandboxing integration."""
        logger.info("Testing security integration...")
        
        try:
            from core.plugins.plugin_manager import PluginManager
            from core.plugins.security_manager import SecurityManager
            
            plugin_manager = PluginManager(self.test_config)
            plugin_manager.initialize()
            
            # Check if security manager is available
            if not plugin_manager.loader.security_manager:
                self.record_test_result("Security integration", False, "Security manager not available")
                return
            
            # Test security manager functionality
            security_stats = plugin_manager.loader.security_manager.get_security_stats()
            self.record_test_result("Security stats", isinstance(security_stats, dict),
                                  f"Retrieved security statistics")
            
            # Test sandbox controller if available
            if plugin_manager.loader.sandbox_controller:
                sandbox_status = plugin_manager.loader.sandbox_controller.get_sandbox_status()
                self.record_test_result("Sandbox status", isinstance(sandbox_status, dict),
                                      f"Retrieved sandbox status")
            else:
                self.record_test_result("Sandbox controller", False, "Sandbox controller not available")
            
        except Exception as e:
            self.record_test_result("Security integration", False, f"Security test failed: {e}")
    
    def test_tool_integration(self):
        """Test tool integration functionality."""
        logger.info("Testing tool integration...")
        
        try:
            from core.plugins.plugin_manager import PluginManager
            from core.tools.tool_registry import ToolRegistry
            
            # Create a mock tool registry
            tool_registry = ToolRegistry()
            
            plugin_manager = PluginManager(self.test_config, tool_registry=tool_registry)
            plugin_manager.initialize()
            
            # Test tool bridge availability
            tool_bridge_available = plugin_manager.tool_bridge is not None
            self.record_test_result("Tool bridge creation", tool_bridge_available,
                                  "Tool bridge initialized")
            
            if tool_bridge_available:
                # Test tool bridge statistics
                bridge_stats = plugin_manager.get_tool_bridge_statistics()
                self.record_test_result("Tool bridge stats", isinstance(bridge_stats, dict),
                                      "Retrieved tool bridge statistics")
            
        except Exception as e:
            self.record_test_result("Tool integration", False, f"Tool integration failed: {e}")
    
    def test_system_integration(self):
        """Test system integration manager."""
        logger.info("Testing system integration...")
        
        try:
            from core.plugins.system_integration_manager import SystemIntegrationManager
            from core.tools.tool_registry import ToolRegistry
            
            # Create mock core services
            core_services = {
                "tool_registry": ToolRegistry(),
                "memory_manager": None,
                "intent_processor": None
            }
            
            integration_manager = SystemIntegrationManager(self.test_config)
            init_result = integration_manager.initialize(core_services)
            
            self.record_test_result("System integration init", init_result.get("success", False),
                                  init_result.get("message", "Unknown"))
            
            if init_result.get("success", False):
                # Test integration status
                status = integration_manager.get_integration_status()
                self.record_test_result("Integration status", isinstance(status, dict),
                                      f"Active integrations: {status.get('active_integrations', [])}")
            
        except Exception as e:
            self.record_test_result("System integration", False, f"Integration test failed: {e}")
    
    def test_cli_interface(self):
        """Test CLI interface structure."""
        logger.info("Testing CLI interface...")
        
        try:
            from core.plugins.plugin_cli_manager import PluginCLIManager
            
            cli_manager = PluginCLIManager(self.test_config)
            
            # Test parser creation
            parser = cli_manager.create_parser()
            self.record_test_result("CLI parser creation", parser is not None,
                                  "CLI argument parser created")
            
            # Test CLI manager initialization
            init_success = cli_manager.initialize()
            self.record_test_result("CLI manager init", init_success,
                                  "CLI manager initialized")
            
        except Exception as e:
            self.record_test_result("CLI interface", False, f"CLI test failed: {e}")
    
    def test_web_api_structure(self):
        """Test web API structure and initialization."""
        logger.info("Testing web API structure...")
        
        try:
            from core.plugins.plugin_web_api import PluginWebAPI
            
            web_api = PluginWebAPI(self.test_config)
            
            # Test router creation
            router = web_api.get_router()
            self.record_test_result("Web API router", router is not None,
                                  "FastAPI router created")
            
            # Test API initialization
            init_success = web_api.initialize()
            self.record_test_result("Web API init", init_success,
                                  "Web API initialized")
            
        except Exception as e:
            self.record_test_result("Web API structure", False, f"Web API test failed: {e}")
    
    def test_example_plugin(self):
        """Test the example HelloWorld plugin."""
        logger.info("Testing example plugin...")
        
        try:
            # Check if example plugin exists
            plugin_path = Path("plugins/example_hello_world")
            plugin_exists = plugin_path.exists() and (plugin_path / "plugin.py").exists()
            
            self.record_test_result("Example plugin exists", plugin_exists,
                                  f"Plugin found at {plugin_path}")
            
            if plugin_exists:
                # Test plugin import
                sys.path.insert(0, str(plugin_path.parent))
                try:
                    from example_hello_world.plugin import HelloWorldPlugin
                    
                    # Test plugin instantiation
                    plugin = HelloWorldPlugin()
                    self.record_test_result("Example plugin import", True,
                                          "HelloWorldPlugin imported successfully")
                    
                    # Test metadata
                    metadata = plugin.get_metadata()
                    self.record_test_result("Example plugin metadata", metadata is not None,
                                          f"Plugin: {metadata.name} v{metadata.version}")
                    
                    # Test tool execution
                    result = plugin.execute_tool(name="World", language="en")
                    success = result.get("success", False)
                    self.record_test_result("Example plugin execution", success,
                                          f"Tool result: {result.get('data', {}).get('message', 'N/A')}")
                    
                except Exception as e:
                    self.record_test_result("Example plugin test", False, f"Plugin test failed: {e}")
            
        except Exception as e:
            self.record_test_result("Example plugin", False, f"Example plugin test failed: {e}")
    
    def record_test_result(self, test_name: str, success: bool, details: str = ""):
        """Record a test result."""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": time.time()
        }
        
        self.test_results.append(result)
        
        if success:
            self.passed_tests.append(result)
            logger.info(f"✓ PASS: {test_name} - {details}")
        else:
            self.failed_tests.append(result)
            logger.error(f"✗ FAIL: {test_name} - {details}")
    
    def generate_test_report(self, execution_time: float) -> Dict[str, Any]:
        """Generate final test report."""
        total_tests = len(self.test_results)
        passed_count = len(self.passed_tests)
        failed_count = len(self.failed_tests)
        success_rate = (passed_count / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "success": failed_count == 0,
            "execution_time_seconds": round(execution_time, 2),
            "total_tests": total_tests,
            "passed": passed_count,
            "failed": failed_count,
            "success_rate_percent": round(success_rate, 1),
            "test_results": self.test_results,
            "failed_tests": [test["test_name"] for test in self.failed_tests]
        }
        
        # Log summary
        logger.info("=" * 60)
        logger.info("PLUGIN SYSTEM TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Execution Time: {execution_time:.2f} seconds")
        
        if failed_count > 0:
            logger.error("FAILED TESTS:")
            for test in self.failed_tests:
                logger.error(f"  - {test['test_name']}: {test['details']}")
        else:
            logger.info("🎉 ALL TESTS PASSED!")
        
        logger.info("=" * 60)
        
        return report

def main():
    """Main test execution function."""
    logger.info("PersonaOS Plugin System Test Suite")
    logger.info("=" * 60)
    
    tester = PluginSystemTester()
    report = tester.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if report["success"] else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()