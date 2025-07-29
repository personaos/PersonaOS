"""
Multi-Step Tool Workflow Manager

This module manages complex tool workflows that require multiple user interactions,
parameter collection, and state tracking across voice conversations.
"""

import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from .tool_registry import VoiceToolContext, ToolResult

class WorkflowState(Enum):
    """States of workflow execution."""
    INITIATED = "initiated"
    COLLECTING_PARAMETERS = "collecting_parameters"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

@dataclass
class WorkflowStep:
    """Individual step in a workflow."""
    step_id: str
    tool_name: str
    required_parameters: List[str]
    optional_parameters: List[str] = field(default_factory=list)
    collected_parameters: Dict[str, Any] = field(default_factory=dict)
    confirmation_required: bool = False
    confirmation_message: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Step IDs this depends on
    completed: bool = False
    result: Optional[ToolResult] = None

@dataclass
class ToolWorkflow:
    """Multi-step tool workflow definition."""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    current_step_index: int = 0
    state: WorkflowState = WorkflowState.INITIATED
    voice_context: Optional[VoiceToolContext] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completion_callback: Optional[Callable] = None
    
    def get_current_step(self) -> Optional[WorkflowStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def advance_step(self) -> bool:
        """Advance to the next step if possible."""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.updated_at = time.time()
            return True
        return False
    
    def is_complete(self) -> bool:
        """Check if all steps are completed."""
        return all(step.completed for step in self.steps)

class WorkflowManager:
    """
    Manages multi-step tool workflows with voice interaction support.
    """
    
    def __init__(self, tool_registry, audio_feedback=None, config: Optional[Dict] = None):
        """
        Initialize workflow manager.
        
        Args:
            tool_registry: ToolRegistry instance
            audio_feedback: ToolAudioFeedback instance
            config: Configuration dictionary
        """
        self.tool_registry = tool_registry
        self.audio_feedback = audio_feedback
        self.config = config or {}
        self.logger = logging.getLogger("workflow_manager")
        
        # Active workflows
        self.active_workflows: Dict[str, ToolWorkflow] = {}
        
        # Workflow templates
        self.workflow_templates = self._load_workflow_templates()
        
        # Voice interaction patterns
        self.parameter_collection_patterns = self._load_parameter_patterns()
        
        # Settings
        self.workflow_timeout = self.config.get("workflow_timeout", 300)  # 5 minutes
        self.max_parameter_attempts = self.config.get("max_parameter_collection_attempts", 3)
        
        self.logger.info("WorkflowManager initialized")
    
    def _load_workflow_templates(self) -> Dict[str, Dict]:
        """Load predefined workflow templates."""
        return {
            "web_research": {
                "name": "Web Research Workflow",
                "description": "Search for information and get weather for location",
                "steps": [
                    {
                        "step_id": "search",
                        "tool_name": "web_search",
                        "required_parameters": ["query"],
                        "confirmation_required": False
                    },
                    {
                        "step_id": "weather_check",
                        "tool_name": "weather",
                        "required_parameters": ["location"],
                        "confirmation_required": False,
                        "dependencies": ["search"]
                    }
                ]
            },
            
            "calculation_with_timer": {
                "name": "Calculate and Set Timer",
                "description": "Perform calculation and set a timer based on result",
                "steps": [
                    {
                        "step_id": "calculate",
                        "tool_name": "calculator",
                        "required_parameters": ["expression"],
                        "confirmation_required": False
                    },
                    {
                        "step_id": "set_timer",
                        "tool_name": "timer",
                        "required_parameters": ["duration", "unit"],
                        "confirmation_required": True,
                        "confirmation_message": "Set timer based on calculation result?",
                        "dependencies": ["calculate"]
                    }
                ]
            },
            
            "search_and_summarize": {
                "name": "Search and Summarize",
                "description": "Search for information and provide summary",
                "steps": [
                    {
                        "step_id": "web_search",
                        "tool_name": "web_search",
                        "required_parameters": ["query"],
                        "confirmation_required": False
                    },
                    {
                        "step_id": "time_check",
                        "tool_name": "time",
                        "required_parameters": [],
                        "confirmation_required": False,
                        "dependencies": ["web_search"]
                    }
                ]
            }
        }
    
    def _load_parameter_patterns(self) -> Dict[str, List[str]]:
        """Load patterns for collecting parameters via voice."""
        return {
            "query": [
                r"search for (.+)",
                r"look up (.+)",
                r"find information about (.+)",
                r"(.+) is what I want to search for"
            ],
            "location": [
                r"(?:in |for |at )(.+)",
                r"the location is (.+)",
                r"(.+) is the place"
            ],
            "expression": [
                r"calculate (.+)",
                r"the math problem is (.+)",
                r"compute (.+)"
            ],
            "duration": [
                r"for (\\d+)",
                r"(\\d+) is the time",
                r"duration of (\\d+)"
            ]
        }
    
    def initiate_workflow(self, template_name: str, voice_context: VoiceToolContext, initial_params: Optional[Dict] = None) -> str:
        """
        Initiate a new workflow from a template.
        
        Args:
            template_name: Name of workflow template
            voice_context: Voice execution context
            initial_params: Initial parameters if any
            
        Returns:
            Workflow ID
        """
        if template_name not in self.workflow_templates:
            raise ValueError(f"Unknown workflow template: {template_name}")
        
        template = self.workflow_templates[template_name]
        workflow_id = str(uuid.uuid4())
        
        # Create workflow steps
        steps = []
        for step_config in template["steps"]:
            step = WorkflowStep(
                step_id=step_config["step_id"],
                tool_name=step_config["tool_name"],
                required_parameters=step_config["required_parameters"],
                optional_parameters=step_config.get("optional_parameters", []),
                confirmation_required=step_config.get("confirmation_required", False),
                confirmation_message=step_config.get("confirmation_message"),
                dependencies=step_config.get("dependencies", [])
            )
            
            # Apply initial parameters if provided
            if initial_params:
                for param_name, param_value in initial_params.items():
                    if param_name in step.required_parameters or param_name in step.optional_parameters:
                        step.collected_parameters[param_name] = param_value
            
            steps.append(step)
        
        # Create workflow
        workflow = ToolWorkflow(
            workflow_id=workflow_id,
            name=template["name"],
            description=template["description"],
            steps=steps,
            voice_context=voice_context
        )
        
        self.active_workflows[workflow_id] = workflow
        
        self.logger.info(f"Initiated workflow '{template_name}' with ID: {workflow_id}")
        
        # Announce workflow start
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(
                f"Starting {workflow.name}. This will involve multiple steps.",
                "normal", True
            )
        
        # Begin parameter collection for first step
        self._begin_step_execution(workflow_id)
        
        return workflow_id
    
    def continue_workflow(self, workflow_id: str, voice_input: str, voice_context: VoiceToolContext) -> Dict[str, Any]:
        """
        Continue workflow execution with voice input.
        
        Args:
            workflow_id: Workflow ID
            voice_input: Voice input text
            voice_context: Voice execution context
            
        Returns:
            Workflow continuation result
        """
        if workflow_id not in self.active_workflows:
            return {
                "success": False,
                "error": "Workflow not found",
                "action": "workflow_not_found"
            }
        
        workflow = self.active_workflows[workflow_id]
        workflow.updated_at = time.time()
        
        try:
            if workflow.state == WorkflowState.COLLECTING_PARAMETERS:
                return self._handle_parameter_collection(workflow, voice_input, voice_context)
            
            elif workflow.state == WorkflowState.AWAITING_CONFIRMATION:
                return self._handle_confirmation_response(workflow, voice_input, voice_context)
            
            elif workflow.state == WorkflowState.PAUSED:
                return self._handle_workflow_resumption(workflow, voice_input, voice_context)
            
            else:
                return {
                    "success": False,
                    "error": f"Cannot continue workflow in state: {workflow.state.value}",
                    "action": "invalid_state"
                }
        
        except Exception as e:
            self.logger.error(f"Error continuing workflow {workflow_id}: {e}")
            workflow.state = WorkflowState.FAILED
            
            return {
                "success": False,
                "error": str(e),
                "action": "workflow_error"
            }
    
    def _begin_step_execution(self, workflow_id: str) -> Dict[str, Any]:
        """Begin execution of current workflow step."""
        workflow = self.active_workflows[workflow_id]
        current_step = workflow.get_current_step()
        
        if not current_step:
            # Workflow complete
            workflow.state = WorkflowState.COMPLETED
            return self._complete_workflow(workflow_id)
        
        # Check dependencies
        if not self._check_step_dependencies(workflow, current_step):
            workflow.state = WorkflowState.FAILED
            error_msg = f"Step dependencies not met for: {current_step.step_id}"
            
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    f"Cannot proceed with {current_step.step_id}. Required previous steps not completed.",
                    "high", True
                )
            
            return {
                "success": False,
                "error": error_msg,
                "action": "dependency_failure"
            }
        
        # Check if we have all required parameters
        missing_params = self._get_missing_parameters(current_step)
        
        if missing_params:
            # Need to collect parameters
            workflow.state = WorkflowState.COLLECTING_PARAMETERS
            return self._request_parameter_collection(workflow, current_step, missing_params)
        
        # Check if confirmation required
        if current_step.confirmation_required:
            workflow.state = WorkflowState.AWAITING_CONFIRMATION
            return self._request_confirmation(workflow, current_step)
        
        # Execute the step
        return self._execute_step(workflow, current_step)
    
    def _handle_parameter_collection(self, workflow: ToolWorkflow, voice_input: str, voice_context: VoiceToolContext) -> Dict[str, Any]:
        """Handle parameter collection from voice input."""
        current_step = workflow.get_current_step()
        if not current_step:
            return {"success": False, "error": "No current step"}
        
        # Try to extract parameters from voice input
        extracted_params = self._extract_parameters_from_voice(voice_input, current_step)
        
        if extracted_params:
            # Update collected parameters
            current_step.collected_parameters.update(extracted_params)
            
            # Check if we have all required parameters now
            missing_params = self._get_missing_parameters(current_step)
            
            if missing_params:
                # Still need more parameters
                return self._request_parameter_collection(workflow, current_step, missing_params)
            else:
                # All parameters collected, proceed to next phase
                if current_step.confirmation_required:
                    workflow.state = WorkflowState.AWAITING_CONFIRMATION
                    return self._request_confirmation(workflow, current_step)
                else:
                    return self._execute_step(workflow, current_step)
        else:
            # Could not extract parameters, ask again
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    "I didn't understand that. Could you please provide the information again?",
                    "normal", True
                )
            
            return {
                "success": True,
                "action": "parameter_collection_retry",
                "message": "Please provide the required information again"
            }
    
    def _handle_confirmation_response(self, workflow: ToolWorkflow, voice_input: str, voice_context: VoiceToolContext) -> Dict[str, Any]:
        """Handle user confirmation response."""
        current_step = workflow.get_current_step()
        if not current_step:
            return {"success": False, "error": "No current step"}
        
        # Parse confirmation response
        voice_lower = voice_input.lower().strip()
        
        positive_responses = ["yes", "yeah", "yep", "okay", "ok", "sure", "proceed", "continue", "do it", "go ahead"]
        negative_responses = ["no", "nope", "cancel", "stop", "abort", "don't", "skip"]
        
        is_positive = any(response in voice_lower for response in positive_responses)
        is_negative = any(response in voice_lower for response in negative_responses)
        
        if is_positive and not is_negative:
            # User confirmed, execute step
            return self._execute_step(workflow, current_step)
        
        elif is_negative:
            # User declined, skip step or cancel workflow
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    "Okay, skipping this step.",
                    "normal", True
                )
            
            current_step.completed = True  # Mark as completed but not executed
            workflow.advance_step()
            return self._begin_step_execution(workflow.workflow_id)
        
        else:
            # Unclear response, ask for clarification
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    "Please say yes to continue or no to skip this step.",
                    "normal", True
                )
            
            return {
                "success": True,
                "action": "confirmation_clarification",
                "message": "Please confirm with yes or no"
            }
    
    def _execute_step(self, workflow: ToolWorkflow, step: WorkflowStep) -> Dict[str, Any]:
        """Execute a workflow step."""
        workflow.state = WorkflowState.EXECUTING
        
        try:
            # Execute tool with collected parameters
            result = self.tool_registry.execute_tool_with_voice(
                step.tool_name, 
                workflow.voice_context, 
                **step.collected_parameters
            )
            
            step.result = result
            step.completed = True
            
            if result.success:
                self.logger.info(f"Step {step.step_id} completed successfully")
                
                # Advance to next step
                if workflow.advance_step():
                    return self._begin_step_execution(workflow.workflow_id)
                else:
                    # Workflow complete
                    workflow.state = WorkflowState.COMPLETED
                    return self._complete_workflow(workflow.workflow_id)
            
            else:
                # Step failed
                workflow.state = WorkflowState.FAILED
                error_msg = f"Step {step.step_id} failed: {result.error}"
                
                if self.audio_feedback:
                    self.audio_feedback._queue_audio_feedback(
                        f"Step {step.step_id} failed. {result.voice_response or result.error}",
                        "high", True
                    )
                
                return {
                    "success": False,
                    "error": error_msg,
                    "action": "step_failure",
                    "step_result": result.__dict__
                }
        
        except Exception as e:
            workflow.state = WorkflowState.FAILED
            error_msg = f"Error executing step {step.step_id}: {str(e)}"
            self.logger.error(error_msg)
            
            if self.audio_feedback:
                self.audio_feedback._queue_audio_feedback(
                    f"An error occurred during {step.step_id}.",
                    "high", True
                )
            
            return {
                "success": False,
                "error": error_msg,
                "action": "execution_error"
            }
    
    def _complete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Complete a workflow."""
        workflow = self.active_workflows[workflow_id]
        workflow.state = WorkflowState.COMPLETED
        
        self.logger.info(f"Workflow {workflow_id} completed: {workflow.name}")
        
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(
                f"Workflow {workflow.name} completed successfully!",
                "normal", True
            )
        
        # Call completion callback if set
        if workflow.completion_callback:
            try:
                workflow.completion_callback(workflow)
            except Exception as e:
                self.logger.error(f"Error in workflow completion callback: {e}")
        
        # Clean up completed workflow after delay
        self._schedule_workflow_cleanup(workflow_id, delay=60)  # 1 minute
        
        return {
            "success": True,
            "action": "workflow_completed",
            "workflow_name": workflow.name,
            "total_steps": len(workflow.steps),
            "completed_steps": sum(1 for step in workflow.steps if step.completed)
        }
    
    def _request_parameter_collection(self, workflow: ToolWorkflow, step: WorkflowStep, missing_params: List[str]) -> Dict[str, Any]:
        """Request parameter collection from user."""
        param_name = missing_params[0]  # Request one parameter at a time
        
        # Generate friendly parameter request
        request_messages = {
            "query": "What would you like me to search for?",
            "location": "Which location are you interested in?",
            "expression": "What calculation would you like me to perform?",
            "duration": "How long should the timer be?",
            "unit": "What unit of time? (seconds, minutes, or hours)",
        }
        
        message = request_messages.get(param_name, f"Please provide the {param_name} for {step.tool_name}")
        
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(message, "normal", False)
        
        return {
            "success": True,
            "action": "parameter_collection_requested",
            "requested_parameter": param_name,
            "message": message,
            "step_name": step.step_id
        }
    
    def _request_confirmation(self, workflow: ToolWorkflow, step: WorkflowStep) -> Dict[str, Any]:
        """Request user confirmation for step execution."""
        message = step.confirmation_message or f"Should I proceed with {step.tool_name}?"
        
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(message, "urgent", False)
        
        return {
            "success": True,
            "action": "confirmation_requested",
            "confirmation_message": message,
            "step_name": step.step_id
        }
    
    def _extract_parameters_from_voice(self, voice_input: str, step: WorkflowStep) -> Dict[str, Any]:
        """Extract parameters from voice input for a step."""
        extracted = {}
        voice_lower = voice_input.lower().strip()
        
        # Try tool-specific parameter extraction first
        tool = self.tool_registry.get_tool(step.tool_name)
        if tool and hasattr(tool, 'parse_voice_parameters'):
            tool_params = tool.parse_voice_parameters(voice_input)
            extracted.update(tool_params)
        
        # Try pattern-based extraction for missing parameters
        for param_name in step.required_parameters + step.optional_parameters:
            if param_name not in extracted and param_name in self.parameter_collection_patterns:
                patterns = self.parameter_collection_patterns[param_name]
                
                import re
                for pattern in patterns:
                    match = re.search(pattern, voice_lower)
                    if match:
                        extracted[param_name] = match.group(1).strip()
                        break
        
        # For simple cases, use the entire input as the main parameter
        if not extracted and step.required_parameters:
            main_param = step.required_parameters[0]
            if main_param in ["query", "expression"]:
                extracted[main_param] = voice_input.strip()
        
        return extracted
    
    def _get_missing_parameters(self, step: WorkflowStep) -> List[str]:
        """Get list of missing required parameters for a step."""
        return [param for param in step.required_parameters 
                if param not in step.collected_parameters or not step.collected_parameters[param]]
    
    def _check_step_dependencies(self, workflow: ToolWorkflow, step: WorkflowStep) -> bool:
        """Check if step dependencies are satisfied."""
        if not step.dependencies:
            return True
        
        for dep_step_id in step.dependencies:
            dep_step = next((s for s in workflow.steps if s.step_id == dep_step_id), None)
            if not dep_step or not dep_step.completed:
                return False
        
        return True
    
    def pause_workflow(self, workflow_id: str, reason: str = "User requested pause") -> bool:
        """Pause an active workflow."""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        workflow.state = WorkflowState.PAUSED
        
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(
                f"Workflow {workflow.name} has been paused.",
                "normal", True
            )
        
        self.logger.info(f"Workflow {workflow_id} paused: {reason}")
        return True
    
    def cancel_workflow(self, workflow_id: str, reason: str = "User cancelled") -> bool:
        """Cancel an active workflow."""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        workflow.state = WorkflowState.CANCELLED
        
        if self.audio_feedback:
            self.audio_feedback._queue_audio_feedback(
                f"Workflow {workflow.name} has been cancelled.",
                "normal", True
            )
        
        self.logger.info(f"Workflow {workflow_id} cancelled: {reason}")
        
        # Clean up cancelled workflow
        self._schedule_workflow_cleanup(workflow_id, delay=5)
        return True
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow."""
        if workflow_id not in self.active_workflows:
            return None
        
        workflow = self.active_workflows[workflow_id]
        current_step = workflow.get_current_step()
        
        return {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "state": workflow.state.value,
            "current_step": current_step.step_id if current_step else None,
            "progress": f"{workflow.current_step_index + 1}/{len(workflow.steps)}",
            "completed_steps": [s.step_id for s in workflow.steps if s.completed],
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at
        }
    
    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows."""
        return [self.get_workflow_status(wf_id) for wf_id in self.active_workflows.keys()]
    
    def _schedule_workflow_cleanup(self, workflow_id: str, delay: int = 60):
        """Schedule workflow cleanup after delay."""
        import threading
        
        def cleanup():
            time.sleep(delay)
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
                self.logger.info(f"Cleaned up workflow {workflow_id}")
        
        threading.Thread(target=cleanup, daemon=True).start()
    
    def cleanup_expired_workflows(self):
        """Clean up expired workflows."""
        current_time = time.time()
        expired_ids = []
        
        for workflow_id, workflow in self.active_workflows.items():
            if current_time - workflow.updated_at > self.workflow_timeout:
                expired_ids.append(workflow_id)
        
        for workflow_id in expired_ids:
            self.logger.info(f"Cleaning up expired workflow: {workflow_id}")
            if self.audio_feedback:
                workflow = self.active_workflows[workflow_id]
                self.audio_feedback._queue_audio_feedback(
                    f"Workflow {workflow.name} has timed out and was cancelled.",
                    "low", True
                )
            del self.active_workflows[workflow_id]
        
        return len(expired_ids)