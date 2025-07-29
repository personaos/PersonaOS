# PersonaOS DevAgent

A Claude Code-style autonomous developer tool integrated into PersonaOS. The DevAgent accepts natural language development tasks and executes them by planning implementation steps, modifying files, running tests, and iterating based on feedback.

## Features

### 🤖 Autonomous Development
- **Natural Language Tasks**: Accept development requests in plain English
- **LLM-Powered Planning**: Use PersonaOS's LLM system to plan implementation steps
- **Iterative Execution**: Automatically retry and improve based on test results and errors
- **Context-Aware**: Understand project structure and existing code patterns

### 🛡️ Safe Operation
- **Dry Run Mode**: Test changes without modifying files
- **Automatic Backups**: Create backups before modifying files
- **Rollback Capability**: Undo changes from any completed task
- **Command Safety**: Block dangerous commands and operations
- **File Validation**: Verify file integrity against checksums

### 📊 Project Intelligence  
- **Code Indexing**: Map project structure, dependencies, and relationships
- **Smart Context**: Provide relevant files and context for development tasks
- **Dependency Tracking**: Understand how files relate to each other
- **Module Analysis**: Extract classes, functions, and imports automatically

### 💻 CLI Integration
- **PersonaOS Integration**: Works seamlessly within PersonaOS conversation flow
- **Command Interface**: Direct CLI commands for advanced usage
- **Task Management**: Track, status, and manage development tasks
- **History Tracking**: Full audit trail of all operations

## Architecture

```
core/dev_agent/
├── __init__.py                    # Module exports
├── dev_agent.py                   # Main DevAgent class
├── project_navigator.py           # Project structure mapping
├── file_manager.py               # Safe file operations with backups
├── code_executor.py              # Command execution with safety
├── cli.py                        # Command-line interface
├── promptline_integration.py     # PersonaOS integration
└── README.md                     # This file
```

### Core Components

1. **DevAgent**: Main orchestrator that coordinates planning and execution
2. **ProjectNavigator**: Maps project structure and tracks dependencies  
3. **FileManager**: Handles file operations with backup and rollback
4. **CodeExecutor**: Executes commands safely with timeout and sandboxing
5. **CLI**: Command-line interface for direct interaction
6. **Integration**: Hooks for PersonaOS conversation system

## Usage

### Within PersonaOS

Start PersonaOS and use dev commands in the conversation:

```bash
python core/main.py
```

```
You: dev: Add a logging utility module with different log levels

PersonaOS: [DevAgent executes the task with full planning and implementation]

You: dev-status
PersonaOS: [Shows current task status and progress]

You: dev-history
PersonaOS: [Shows recent development tasks]
```

### Standalone CLI

Use the DevAgent CLI directly:

```bash
python -m core.dev_agent.cli dev "Create a simple calculator function"
python -m core.dev_agent.cli dev-status
python -m core.dev_agent.cli dev-system
```

### Programmatic Usage

```python
from core.dev_agent import DevAgent

# Initialize with project root
agent = DevAgent("/path/to/project", {
    'dry_run': False,
    'require_confirmation': True
})

# Execute a development task
execution = agent.execute_task("Add error handling to the API endpoints")

# Check results
if execution.success:
    print(f"Task completed: {execution.task_id}")
    print(f"Files modified: {len(execution.file_operations)}")
else:
    print(f"Task failed: {execution.errors}")

# Get system status  
status = agent.get_system_status()
print(f"Project has {status['project_stats']['total_files']} files")
```

## Commands

### Development Commands

- `dev: <description>` - Execute a development task
  - Example: `dev: Add input validation to user registration`
  - Example: `dev: Refactor the database connection handling`
  - Example: `dev: Create unit tests for the authentication module`

### Management Commands

- `dev-status [task_id]` - Show current or specific task status
- `dev-history [limit]` - Show recent task history (default: 10)  
- `dev-rollback <task_id>` - Rollback changes from a specific task
- `dev-cancel` - Cancel the currently running task
- `dev-system` - Show DevAgent system status and statistics

## Configuration

DevAgent respects PersonaOS configuration and supports additional options:

```python
config = {
    # Execution settings
    'dry_run': False,                    # Test mode - don't modify files
    'require_confirmation': True,        # Ask before dangerous operations
    'max_iterations': 5,                 # Maximum retry attempts
    'auto_commit': False,               # Automatically commit changes
    
    # Safety limits
    'max_files_per_task': 20,           # Limit files modified per task
    'max_commands_per_task': 10,        # Limit commands run per task
    
    # Component-specific settings
    'navigator': {...},                  # ProjectNavigator settings
    'file_manager': {...},              # FileManager settings  
    'executor': {...}                   # CodeExecutor settings
}
```

## Safety Features

### File Operations
- **Automatic Backups**: All file modifications create timestamped backups
- **Dry Run Mode**: Test operations without making actual changes
- **Rollback Support**: Undo any task's changes completely
- **Integrity Checking**: Verify files against checksums

### Command Execution  
- **Safe Mode**: Block dangerous commands (rm, format, sudo, etc.)
- **Timeout Protection**: Prevent runaway processes
- **Output Limiting**: Prevent memory exhaustion from large outputs
- **Process Tracking**: Monitor and control active processes

### Task Management
- **History Tracking**: Full audit trail of all operations
- **Error Recovery**: Automatic retry with different approaches
- **Session Isolation**: Separate backup namespaces per session
- **Concurrent Limits**: Prevent resource exhaustion

## Examples

### Example 1: Add a New Feature

```
You: dev: Add a rate limiting middleware for the API

DevAgent will:
1. Analyze the existing API structure
2. Plan the rate limiting implementation
3. Create middleware files
4. Update route configurations  
5. Add tests
6. Run the test suite
7. Report results
```

### Example 2: Refactor Code

```
You: dev: Refactor the user authentication to use dependency injection

DevAgent will:
1. Map current authentication implementation
2. Plan dependency injection pattern
3. Create new interfaces and implementations
4. Update existing code to use DI
5. Ensure tests still pass
6. Update documentation if needed
```

### Example 3: Fix Issues

```  
You: dev: Fix the memory leak in the image processing pipeline

DevAgent will:
1. Analyze the image processing code
2. Identify potential memory leak sources
3. Plan fixes (resource cleanup, etc.)
4. Implement the fixes
5. Add memory monitoring
6. Run tests to verify the fix
```

## Integration with PersonaOS

DevAgent integrates seamlessly with PersonaOS:

- **LLM Integration**: Uses PersonaOS's LLM system for planning
- **Configuration**: Respects PersonaOS config files and environment
- **Memory System**: Can store conversation context about development tasks
- **Tool System**: Registered as a PersonaOS tool for voice/CLI access
- **Safety System**: Integrates with PersonaOS intent processing and safety validation

## Testing

Run the test suite to verify installation:

```bash
python test_dev_agent_simple.py
```

Run the demonstration:

```bash  
python demo_dev_agent.py
```

## Limitations

- **LLM Dependency**: Advanced planning requires LLM access
- **Language Support**: Optimized for Python projects (supports others)
- **Windows Compatibility**: Some shell operations may need adjustment
- **Resource Usage**: Large projects may require significant memory
- **Test Framework**: Assumes pytest for testing (configurable)

## Future Enhancements

- **Multi-Language Support**: Better support for non-Python projects
- **Visual Diff**: Show changes before applying them
- **Collaborative Mode**: Multiple developers working with same agent
- **Plugin System**: Custom development workflow plugins
- **Integration**: GitHub, GitLab, and other platform integrations
- **Performance**: Optimization for very large codebases

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure PersonaOS dependencies are installed
2. **Permission Errors**: Check file permissions in project directory
3. **LLM Errors**: Verify PersonaOS LLM configuration
4. **Unicode Issues**: Use UTF-8 encoding in terminal/IDE
5. **Command Blocked**: Check safe mode settings in configuration

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Reset Agent State

If needed, clear agent backups and history:

```bash
rm -rf .dev_agent_backups/
```