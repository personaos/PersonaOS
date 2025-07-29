"""
PersonaOS DevAgent integration with main CLI system.

Provides integration hooks for dev commands within PersonaOS.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any

from .cli import handle_dev_command_dispatch
from ..config import load_config


class DevAgentPrompter:
    """
    Integration class for DevAgent with PersonaOS CLI.
    
    Handles dev command parsing and execution within the main conversation loop.
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Dev command patterns
        self.dev_patterns = [
            r'^dev:\s*(.+)$',  # dev: task description
            r'^dev-(\w+)(?:\s+(.*))?$',  # dev-status, dev-history, etc.
        ]
    
    def is_dev_command(self, user_input: str) -> bool:
        """Check if user input is a dev command."""
        user_input = user_input.strip()
        
        for pattern in self.dev_patterns:
            if re.match(pattern, user_input, re.IGNORECASE):
                return True
        
        return False
    
    def parse_dev_command(self, user_input: str) -> Tuple[str, List[str]]:
        """Parse dev command into command and arguments."""
        user_input = user_input.strip()
        
        # Match dev: task description
        match = re.match(r'^dev:\s*(.+)$', user_input, re.IGNORECASE)
        if match:
            task_description = match.group(1).strip()
            return 'dev', [task_description]
        
        # Match dev-subcommand
        match = re.match(r'^dev-(\w+)(?:\s+(.*))?$', user_input, re.IGNORECASE)
        if match:
            subcommand = match.group(1).lower()
            args_str = match.group(2) or ""
            args = args_str.split() if args_str.strip() else []
            return f'dev-{subcommand}', args
        
        return '', []
    
    def handle_dev_command(self, user_input: str) -> Tuple[bool, str]:
        """
        Handle dev command execution.
        
        Returns:
            Tuple of (success, response_message)
        """
        try:
            command, args = self.parse_dev_command(user_input)
            
            if not command:
                return False, "Invalid dev command format"
            
            # Execute command using CLI handler
            exit_code = handle_dev_command_dispatch(command, args, self.project_root)
            
            if exit_code == 0:
                return True, "Dev command executed successfully"
            else:
                return False, "Dev command failed"
                
        except Exception as e:
            self.logger.error(f"Dev command execution failed: {e}")
            return False, f"Dev command error: {str(e)}"
    
    def get_dev_help(self) -> str:
        """Get help text for dev commands."""
        return """
DevAgent Commands:

• dev: <task description>       - Execute development task
  Example: dev: Add a plugin loader registry

• dev-status [task_id]          - Show current or specific task status
• dev-history [limit]           - Show recent task history (default: 10)
• dev-rollback <task_id>        - Rollback changes from a task
• dev-cancel                    - Cancel current running task
• dev-system                    - Show DevAgent system status

DevAgent can autonomously:
- Plan implementation steps using LLM
- Create and modify project files
- Run tests and validation commands
- Manage backups and rollback changes
- Execute shell commands safely

All operations support dry-run mode and maintain full history.
"""


def integrate_dev_agent_with_conversation(user_input: str, config: Dict, 
                                        project_root: str = None) -> Tuple[bool, str]:
    """
    Integration function to handle dev commands within PersonaOS conversation loop.
    
    This function can be called from the main conversation handler to check
    for and process dev commands.
    
    Args:
        user_input: User's input text
        config: PersonaOS configuration
        project_root: Project root directory
        
    Returns:
        Tuple of (handled, response) where handled indicates if this was a dev command
    """
    prompter = DevAgentPrompter(project_root)
    
    if prompter.is_dev_command(user_input):
        success, response = prompter.handle_dev_command(user_input)
        return True, response
    
    # Check for help requests
    if 'dev help' in user_input.lower() or 'dev commands' in user_input.lower():
        return True, prompter.get_dev_help()
    
    return False, ""


def setup_dev_agent_integration():
    """
    Setup function to integrate DevAgent with PersonaOS.
    
    This can be called during PersonaOS initialization to register dev commands.
    """
    try:
        config = load_config()
        
        # Log successful integration
        logger = logging.getLogger('DevAgentIntegration')
        logger.info("DevAgent integration ready")
        
        return True
        
    except Exception as e:
        logger = logging.getLogger('DevAgentIntegration')
        logger.warning(f"Failed to setup DevAgent integration: {e}")
        return False