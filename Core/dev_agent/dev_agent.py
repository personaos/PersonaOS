"""
DevAgent - Autonomous Developer Tool for PersonaOS.

A Claude Code-style autonomous developer that accepts natural language tasks
and executes code changes, tests, and development operations.
"""

import os
import json
import logging
import traceback
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

from .project_navigator import ProjectNavigator
from .file_manager import FileManager, FileOperation
from .code_executor import CodeExecutor, ExecutionResult, ExecutionConfig


@dataclass
class TaskPlan:
    """Plan for executing a development task."""
    task_description: str
    steps: List[str]
    files_to_modify: List[str]
    files_to_create: List[str]
    commands_to_run: List[str]
    estimated_time: float
    risk_level: str  # 'low', 'medium', 'high'
    dependencies: List[str]


@dataclass
class TaskExecution:
    """Record of task execution."""
    task_id: str
    description: str
    plan: TaskPlan
    start_time: float
    end_time: Optional[float] = None
    status: str = 'pending'  # 'pending', 'in_progress', 'completed', 'failed', 'cancelled'
    steps_completed: List[str] = None
    file_operations: List[FileOperation] = None
    command_results: List[ExecutionResult] = None
    errors: List[str] = None
    success: bool = False
    
    def __post_init__(self):
        if self.steps_completed is None:
            self.steps_completed = []
        if self.file_operations is None:
            self.file_operations = []
        if self.command_results is None:
            self.command_results = []
        if self.errors is None:
            self.errors = []


class DevAgent:
    """
    Autonomous Developer Agent for PersonaOS.
    
    Accepts natural language development tasks and executes them by:
    1. Planning the implementation steps
    2. Modifying/creating files as needed
    3. Running tests and validation commands
    4. Iterating based on feedback and errors
    """
    
    def __init__(self, project_root: str, config: Optional[Dict] = None):
        self.project_root = Path(project_root).resolve()
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize core components
        self.navigator = ProjectNavigator(str(self.project_root), config.get('navigator', {}))
        self.file_manager = FileManager(str(self.project_root), config.get('file_manager', {}))
        self.executor = CodeExecutor(str(self.project_root), config.get('executor', {}))
        
        # LLM integration
        self.llm_manager = None
        self._init_llm()
        
        # Task tracking
        self.current_task: Optional[TaskExecution] = None
        self.task_history: List[TaskExecution] = []
        self.max_history_size = config.get('max_history_size', 50)
        
        # Configuration
        self.dry_run = config.get('dry_run', False)
        self.auto_commit = config.get('auto_commit', False)
        self.max_iterations = config.get('max_iterations', 5)
        self.require_confirmation = config.get('require_confirmation', True)
        
        # Safety limits
        self.max_files_per_task = config.get('max_files_per_task', 20)
        self.max_commands_per_task = config.get('max_commands_per_task', 10)
        
        self.logger.info(f"DevAgent initialized for project: {self.project_root}")
    
    def _init_llm(self) -> None:
        """Initialize LLM connection using PersonaOS LLM system."""
        try:
            # Import PersonaOS LLM components
            from ..config import load_config
            from ..llm.llm_handler import LLMManager
            
            # Load PersonaOS config
            personas_config = load_config()
            
            # Initialize LLM manager
            self.llm_manager = LLMManager(personas_config)
            
            self.logger.info("LLM integration initialized successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize LLM integration: {e}")
            self.logger.warning("DevAgent will work without LLM-powered planning")
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"task_{timestamp}_{len(self.task_history)}"
    
    def _create_planning_prompt(self, task_description: str, context: Dict[str, Any]) -> str:
        """Create prompt for LLM-based task planning."""
        project_stats = self.navigator.get_stats()
        recent_files = [info.path for info in self.navigator.find_files()[:10]]
        
        prompt = f'''
You are an autonomous developer agent working on the PersonaOS project. 
Analyze the following development task and create a detailed implementation plan.

Project Context:
- Project: PersonaOS (AI personality operating system)
- Total files: {project_stats.get('total_files', 0)}
- Languages: {', '.join(project_stats.get('languages', {}).keys())}
- Recent files: {', '.join(recent_files[:5])}

Task Description:
{task_description}

Additional Context:
{json.dumps(context, indent=2)}

Please provide a structured plan with:
1. Step-by-step implementation approach
2. Files that need to be modified or created
3. Commands to run (tests, linting, etc.)
4. Estimated complexity/risk level
5. Dependencies or prerequisites

Format your response as JSON with the following structure:
{{
    "steps": ["step 1", "step 2", ...],
    "files_to_modify": ["path/to/file1.py", ...],
    "files_to_create": ["path/to/new_file.py", ...],
    "commands_to_run": ["python -m pytest tests/", ...],
    "estimated_time": 30.0,
    "risk_level": "medium",
    "dependencies": ["requirement1", ...]
}}

Be specific about file paths and command syntax. Consider the existing PersonaOS architecture.
'''
        return prompt.strip()
    
    def _parse_llm_plan(self, llm_response: str) -> Optional[TaskPlan]:
        """Parse LLM response into TaskPlan object."""
        try:
            # Try to extract JSON from response
            response_clean = llm_response.strip()
            
            # Handle markdown code blocks
            if '```json' in response_clean:
                start = response_clean.find('```json') + 7
                end = response_clean.find('```', start)
                response_clean = response_clean[start:end].strip()
            elif '```' in response_clean:
                start = response_clean.find('```') + 3
                end = response_clean.find('```', start)
                response_clean = response_clean[start:end].strip()
            
            # Parse JSON
            plan_data = json.loads(response_clean)
            
            return TaskPlan(
                task_description="",  # Will be set by caller
                steps=plan_data.get('steps', []),
                files_to_modify=plan_data.get('files_to_modify', []),
                files_to_create=plan_data.get('files_to_create', []),
                commands_to_run=plan_data.get('commands_to_run', []),
                estimated_time=plan_data.get('estimated_time', 30.0),
                risk_level=plan_data.get('risk_level', 'medium'),
                dependencies=plan_data.get('dependencies', [])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse LLM plan response: {e}")
            self.logger.debug(f"Raw LLM response: {llm_response}")
            return None
    
    def _create_fallback_plan(self, task_description: str) -> TaskPlan:
        """Create a basic fallback plan when LLM is not available."""
        return TaskPlan(
            task_description=task_description,
            steps=[
                "Analyze task requirements",
                "Identify files to modify",
                "Implement changes",
                "Run tests",
                "Validate implementation"
            ],
            files_to_modify=[],
            files_to_create=[],
            commands_to_run=["python -m pytest", "python -m flake8"],
            estimated_time=30.0,
            risk_level='medium',
            dependencies=[]
        )
    
    def plan_task(self, task_description: str, context: Optional[Dict] = None) -> TaskPlan:
        """Plan a development task using LLM or fallback logic."""
        self.logger.info(f"Planning task: {task_description}")
        
        if context is None:
            context = {}
        
        # Try LLM-based planning first
        if self.llm_manager:
            try:
                prompt = self._create_planning_prompt(task_description, context)
                llm_response = self.llm_manager.query(prompt)
                
                plan = self._parse_llm_plan(llm_response)
                if plan:
                    plan.task_description = task_description
                    self.logger.info(f"Created LLM-based plan with {len(plan.steps)} steps")
                    return plan
                    
            except Exception as e:
                self.logger.warning(f"LLM planning failed: {e}")
        
        # Fallback to basic planning
        self.logger.info("Using fallback planning approach")
        plan = self._create_fallback_plan(task_description)
        
        return plan
    
    def execute_task(self, task_description: str, context: Optional[Dict] = None, 
                    dry_run: Optional[bool] = None) -> TaskExecution:
        """Execute a development task end-to-end."""
        if self.current_task and self.current_task.status == 'in_progress':
            raise RuntimeError("Another task is already in progress. Complete or cancel it first.")
        
        # Use provided dry_run setting or default
        actual_dry_run = dry_run if dry_run is not None else self.dry_run
        self.file_manager.set_dry_run(actual_dry_run)
        
        # Create task execution record
        task_id = self._generate_task_id()
        plan = self.plan_task(task_description, context)
        
        task_execution = TaskExecution(
            task_id=task_id,
            description=task_description,
            plan=plan,
            start_time=datetime.now().timestamp(),
            status='in_progress'
        )
        
        self.current_task = task_execution
        
        try:
            self.logger.info(f"Starting task execution: {task_id}")
            self.logger.info(f"Plan: {len(plan.steps)} steps, {len(plan.files_to_modify)} modifications, {len(plan.files_to_create)} new files")
            
            # Execute plan steps
            for i, step in enumerate(plan.steps):
                try:
                    self.logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step}")
                    
                    # This is where we would use LLM to generate specific actions for each step
                    # For now, we'll execute based on the plan structure
                    if i == 0:  # Analysis step
                        self._execute_analysis_step(step, task_execution)
                    elif "implement" in step.lower() or "modify" in step.lower():
                        self._execute_implementation_step(step, task_execution)
                    elif "test" in step.lower():
                        self._execute_testing_step(step, task_execution)
                    else:
                        self._execute_generic_step(step, task_execution)
                    
                    task_execution.steps_completed.append(step)
                    
                except Exception as e:
                    error_msg = f"Step failed: {step} - {str(e)}"
                    self.logger.error(error_msg)
                    task_execution.errors.append(error_msg)
                    
                    # Stop on critical errors
                    if "critical" in error_msg.lower() or len(task_execution.errors) > 3:
                        break
            
            # Run planned commands
            for command in plan.commands_to_run:
                try:
                    self.logger.info(f"Running command: {command}")
                    config = ExecutionConfig(timeout=120.0)
                    result = self.executor.execute_command(command, config)
                    task_execution.command_results.append(result)
                    
                    if result.exit_code != 0:
                        error_msg = f"Command failed: {command} (exit code: {result.exit_code})"
                        task_execution.errors.append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Command execution error: {command} - {str(e)}"
                    task_execution.errors.append(error_msg)
            
            # Determine final status
            if len(task_execution.errors) == 0:
                task_execution.status = 'completed'
                task_execution.success = True
                self.logger.info(f"Task completed successfully: {task_id}")
            else:
                task_execution.status = 'failed'
                self.logger.warning(f"Task failed with {len(task_execution.errors)} errors: {task_id}")
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            self.logger.error(error_msg)
            task_execution.errors.append(error_msg)
            task_execution.status = 'failed'
        
        finally:
            task_execution.end_time = datetime.now().timestamp()
            self.current_task = None
            
            # Add to history
            self.task_history.append(task_execution)
            if len(self.task_history) > self.max_history_size:
                self.task_history.pop(0)
        
        return task_execution
    
    def _execute_analysis_step(self, step: str, task_execution: TaskExecution) -> None:
        """Execute analysis step - gather context and understand requirements."""
        self.logger.debug("Executing analysis step")
        
        # Refresh project index
        self.navigator.refresh_index()
        
        # Log project statistics
        stats = self.navigator.get_stats()
        self.logger.info(f"Project stats: {stats}")
    
    def _execute_implementation_step(self, step: str, task_execution: TaskExecution) -> None:
        """Execute implementation step - modify/create files."""
        self.logger.debug("Executing implementation step")
        
        # For demonstration, create/modify files from the plan
        for file_path in task_execution.plan.files_to_create:
            if not file_path:
                continue
                
            # Generate basic file content (in real implementation, this would use LLM)
            content = self._generate_file_content(file_path, task_execution.description)
            
            operation = self.file_manager.create_file(file_path, content, 
                                                    f"Created for task: {task_execution.task_id}")
            task_execution.file_operations.append(operation)
        
        for file_path in task_execution.plan.files_to_modify:
            if not file_path:
                continue
                
            # Generate modified content (in real implementation, this would use LLM)
            content = self._generate_modified_content(file_path, task_execution.description)
            if content:
                operation = self.file_manager.edit_file(file_path, content, 
                                                      description=f"Modified for task: {task_execution.task_id}")
                task_execution.file_operations.append(operation)
    
    def _execute_testing_step(self, step: str, task_execution: TaskExecution) -> None:
        """Execute testing step - run tests and validation."""
        self.logger.debug("Executing testing step")
        
        # Run tests
        config = ExecutionConfig(timeout=180.0)
        test_result = self.executor.run_tests(config=config)
        task_execution.command_results.append(test_result)
        
        if test_result.exit_code != 0:
            task_execution.errors.append(f"Tests failed: {test_result.stderr}")
    
    def _execute_generic_step(self, step: str, task_execution: TaskExecution) -> None:
        """Execute generic step."""
        self.logger.debug(f"Executing generic step: {step}")
        # Generic step execution logic
        pass
    
    def _generate_file_content(self, file_path: str, task_description: str) -> str:
        """Generate content for new file (placeholder implementation)."""
        file_name = Path(file_path).name
        
        if file_path.endswith('.py'):
            return f'''"""
{file_name} - Generated for PersonaOS DevAgent task.

Task: {task_description}
"""

# TODO: Implement functionality for {task_description}

def main():
    pass

if __name__ == "__main__":
    main()
'''
        else:
            return f"# {file_name}\n\n# Generated for task: {task_description}\n\nTODO: Add content\n"
    
    def _generate_modified_content(self, file_path: str, task_description: str) -> Optional[str]:
        """Generate modified content for existing file (placeholder implementation)."""
        try:
            full_path = self.project_root / file_path
            if not full_path.exists():
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Simple modification: add a comment about the task
            comment_line = f"# Modified for task: {task_description}\n"
            
            if file_path.endswith('.py'):
                # Add comment after imports or at the beginning
                lines = original_content.split('\n')
                for i, line in enumerate(lines):
                    if not line.strip().startswith('import') and not line.strip().startswith('from'):
                        lines.insert(i, comment_line.rstrip())
                        break
                else:
                    lines.insert(0, comment_line.rstrip())
                
                return '\n'.join(lines)
            else:
                return comment_line + original_content
                
        except Exception as e:
            self.logger.warning(f"Failed to modify {file_path}: {e}")
            return None
    
    def cancel_current_task(self) -> bool:
        """Cancel the currently executing task."""
        if not self.current_task or self.current_task.status != 'in_progress':
            return False
        
        self.logger.info(f"Cancelling task: {self.current_task.task_id}")
        
        # Stop any running processes
        self.executor.kill_all_processes()
        
        # Update task status
        self.current_task.status = 'cancelled'
        self.current_task.end_time = datetime.now().timestamp()
        
        # Add to history
        self.task_history.append(self.current_task)
        self.current_task = None
        
        return True
    
    def rollback_task(self, task_id: str) -> bool:
        """Rollback changes made by a specific task."""
        # Find task in history
        target_task = None
        for task in self.task_history:
            if task.task_id == task_id:
                target_task = task
                break
        
        if not target_task:
            self.logger.error(f"Task not found: {task_id}")
            return False
        
        self.logger.info(f"Rolling back task: {task_id}")
        
        # Rollback file operations in reverse order
        success_count = 0
        for operation in reversed(target_task.file_operations):
            if self.file_manager.rollback_operation(operation):
                success_count += 1
        
        self.logger.info(f"Rolled back {success_count}/{len(target_task.file_operations)} file operations")
        return success_count == len(target_task.file_operations)
    
    def get_task_status(self, task_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get status of current or specified task."""
        target_task = None
        
        if task_id:
            for task in self.task_history:
                if task.task_id == task_id:
                    target_task = task
                    break
        else:
            target_task = self.current_task
        
        if not target_task:
            return None
        
        return {
            'task_id': target_task.task_id,
            'description': target_task.description,
            'status': target_task.status,
            'start_time': target_task.start_time,
            'end_time': target_task.end_time,
            'steps_completed': len(target_task.steps_completed),
            'total_steps': len(target_task.plan.steps),
            'file_operations': len(target_task.file_operations),
            'command_results': len(target_task.command_results),
            'errors': target_task.errors,
            'success': target_task.success
        }
    
    def list_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent task executions."""
        recent_tasks = self.task_history[-limit:]
        
        return [
            {
                'task_id': task.task_id,
                'description': task.description,
                'status': task.status,
                'start_time': task.start_time,
                'duration': (task.end_time - task.start_time) if task.end_time else None,
                'success': task.success,
                'error_count': len(task.errors)
            }
            for task in recent_tasks
        ]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            'project_root': str(self.project_root),
            'llm_available': self.llm_manager is not None,
            'current_task': self.current_task.task_id if self.current_task else None,
            'task_history_count': len(self.task_history),
            'dry_run_mode': self.dry_run,
            'project_stats': self.navigator.get_stats(),
            'file_manager_status': self.file_manager.get_session_summary(),
            'executor_status': {
                'active_processes': len(self.executor.active_processes),
                'execution_history': len(self.executor.execution_history),
                'safe_mode': self.executor.safe_mode
            }
        }
    
    def cleanup(self) -> None:
        """Clean up agent resources."""
        if self.current_task and self.current_task.status == 'in_progress':
            self.cancel_current_task()
        
        self.executor.cleanup()
        self.logger.info("DevAgent cleaned up")