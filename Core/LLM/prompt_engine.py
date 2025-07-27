"""
PromptEngine module for PersonaOS - generates, routes, and evaluates prompts for external LLM collaboration.

This module enables PersonaOS to create structured prompts for various tasks,
route them to appropriate LLMs, and evaluate responses for safety and quality.
Designed for self-improvement workflows and external AI collaboration.
"""

import json
import logging
import re
import datetime
from typing import Dict, List, Optional, TypedDict, Any, Literal
from pathlib import Path


# Type definitions for structured returns
class ResponseEvaluation(TypedDict):
    """Structured evaluation result for LLM responses."""
    is_safe: bool
    contains_code: bool
    mentions_filesystem: bool
    confidence_score: float
    flagged_content: List[str]
    safety_notes: str


class PromptLogEntry(TypedDict):
    """Structured log entry for prompt/response tracking."""
    timestamp: str
    task_type: str
    prompt: str
    response: str
    success: bool
    model_used: str
    evaluation: Optional[ResponseEvaluation]


# Pre-defined prompt templates for different task types
PROMPT_TEMPLATES = {
    "generate_plugin": """
You are assisting in creating a Python plugin for PersonaOS, a modular AI assistant.

Task: Create a {plugin_name} plugin with the following requirements:
{requirements}

Guidelines:
- Use only Python standard libraries unless specified otherwise
- Include proper docstrings with intent tags (# intent: plugin_action)
- Make the plugin stateless and thread-safe
- Follow PersonaOS plugin interface: create_tool() factory function
- Include error handling and validation

Additional context:
{context}

Please provide a complete, working Python module.
""",

    "fix_code": """
You are helping debug and fix code issues in PersonaOS.

Problem description: {problem_description}

Code to fix:
```{language}
{code_snippet}
```

Error details (if any):
{error_details}

Context: {context}

Please provide:
1. Analysis of the issue
2. The corrected code
3. Explanation of changes made
4. Any additional recommendations

Focus on maintaining compatibility with PersonaOS architecture.
""",

    "explain_code": """
You are explaining code functionality within PersonaOS.

Code to analyze:
```{language}
{code_snippet}
```

Context: {context}
Focus areas: {focus_areas}

Please provide:
1. High-level overview of what this code does
2. Key components and their roles
3. How it fits into PersonaOS architecture
4. Any notable patterns or design decisions
5. Potential improvements or concerns

Make the explanation accessible for {audience_level} developers.
""",

    "generate_config": """
You are creating configuration for PersonaOS components.

Configuration type: {config_type}
Component: {component_name}

Requirements:
{requirements}

Existing configuration structure (for reference):
{existing_config}

Please generate:
1. Complete configuration structure
2. Default values with explanations
3. Validation rules or constraints
4. Documentation comments

Format: {output_format}
""",

    "self_debug": """
You are helping PersonaOS diagnose and resolve internal issues.

Issue description: {issue_description}
System state: {system_state}
Recent logs: {recent_logs}
Error traces: {error_traces}

Components involved: {components}
Environment: {environment_info}

Please provide:
1. Root cause analysis
2. Step-by-step debugging approach
3. Specific fixes or workarounds
4. Prevention strategies
5. Monitoring recommendations

Focus on maintaining system stability and user privacy.
""",

    "generate_tests": """
You are creating tests for PersonaOS components.

Component to test: {component_name}
Code to test:
```{language}
{code_snippet}
```

Test requirements:
{test_requirements}

Please generate:
1. Unit tests covering core functionality
2. Integration tests if applicable
3. Error condition tests
4. Mock objects where needed
5. Test documentation

Use Python's unittest framework and follow PersonaOS testing conventions.
""",

    "optimize_performance": """
You are optimizing performance for PersonaOS components.

Component: {component_name}
Performance issue: {performance_issue}
Current metrics: {current_metrics}

Code to optimize:
```{language}
{code_snippet}
```

Constraints:
- Maintain offline-first capability
- Preserve privacy and security
- Keep memory usage minimal
- Ensure thread safety

Please provide:
1. Performance analysis
2. Optimization strategy
3. Refactored code
4. Expected improvements
5. Monitoring suggestions
"""
}


def generate_prompt(task_type: str, parameters: Dict[str, Any]) -> str:
    """
    Generate a structured, safe prompt for a given task type.
    
    Args:
        task_type: Type of task (e.g., 'generate_plugin', 'fix_code')
        parameters: Dictionary containing task-specific parameters
        
    Returns:
        Formatted prompt string ready for LLM consumption
        
    Raises:
        ValueError: If task_type is not supported or required parameters are missing
        
    Examples:
        >>> params = {'plugin_name': 'weather', 'requirements': 'Get local weather'}
        >>> prompt = generate_prompt('generate_plugin', params)
    """
    if task_type not in PROMPT_TEMPLATES:
        available_types = ', '.join(PROMPT_TEMPLATES.keys())
        raise ValueError(f"Unsupported task type '{task_type}'. Available: {available_types}")
    
    template = PROMPT_TEMPLATES[task_type]
    
    # Validate required parameters based on template placeholders
    required_params = _extract_template_variables(template)
    missing_params = [param for param in required_params if param not in parameters]
    
    if missing_params:
        raise ValueError(f"Missing required parameters for {task_type}: {missing_params}")
    
    # Fill in default values for common optional parameters
    filled_parameters = _add_default_parameters(parameters)
    
    try:
        formatted_prompt = template.format(**filled_parameters)
        return _sanitize_prompt(formatted_prompt)
    except KeyError as e:
        raise ValueError(f"Template formatting error for {task_type}: {e}")


def route_prompt(prompt: str, destination_model: str = 'claude', 
                priority: Literal['low', 'normal', 'high'] = 'normal') -> str:
    """
    Route a prompt to the specified LLM destination.
    
    Currently a placeholder that logs routing intent.
    Future implementation will connect to actual model dispatch layer.
    
    Args:
        prompt: The formatted prompt to route
        destination_model: Target LLM ('claude', 'gpt4', 'local', 'mistral')
        priority: Request priority level
        
    Returns:
        Routing confirmation message (placeholder)
        
    TODO: Implement actual model routing with:
        - API key management
        - Rate limiting
        - Fallback model selection
        - Cost tracking
        - Response streaming
    """
    # Validate inputs
    if not prompt.strip():
        raise ValueError("Cannot route empty prompt")
    
    supported_models = ['claude', 'gpt4', 'local', 'mistral', 'ollama']
    if destination_model not in supported_models:
        raise ValueError(f"Unsupported model '{destination_model}'. Supported: {supported_models}")
    
    # Log routing intent
    timestamp = datetime.datetime.now().isoformat()
    routing_info = {
        'timestamp': timestamp,
        'destination': destination_model,
        'priority': priority,
        'prompt_length': len(prompt),
        'prompt_preview': prompt[:100] + '...' if len(prompt) > 100 else prompt
    }
    
    logging.info(f"PromptEngine: Routing prompt to {destination_model}", extra=routing_info)
    
    # Placeholder return - will be replaced with actual LLM response
    return f"[PLACEHOLDER] Prompt routed to {destination_model} with {priority} priority at {timestamp}"


def evaluate_response(prompt: str, response: str, task_type: str = '') -> ResponseEvaluation:
    """
    Perform basic safety and quality evaluation of LLM responses.
    
    Args:
        prompt: Original prompt sent to LLM
        response: Response received from LLM
        task_type: Type of task for context-aware evaluation
        
    Returns:
        ResponseEvaluation dict with safety and quality metrics
        
    TODO: Enhance with:
        - ML-based content classification
        - Context-aware safety rules
        - Code execution safety analysis
        - Bias detection
        - Factual accuracy checking
    """
    evaluation: ResponseEvaluation = {
        'is_safe': True,
        'contains_code': False,
        'mentions_filesystem': False,
        'confidence_score': 0.0,
        'flagged_content': [],
        'safety_notes': ''
    }
    
    if not response.strip():
        evaluation['is_safe'] = False
        evaluation['safety_notes'] = 'Empty response received'
        evaluation['confidence_score'] = 0.0
        return evaluation
    
    # Check for code content
    code_patterns = [
        r'```[\w]*\n.*?\n```',  # Code blocks
        r'`[^`]+`',             # Inline code
        r'def\s+\w+\(',         # Function definitions
        r'class\s+\w+[:\(]',    # Class definitions
        r'import\s+\w+',        # Import statements
    ]
    
    for pattern in code_patterns:
        if re.search(pattern, response, re.DOTALL | re.IGNORECASE):
            evaluation['contains_code'] = True
            break
    
    # Check for filesystem operations
    filesystem_patterns = [
        r'\b(open|read|write|delete|rm|mkdir|rmdir)\b',
        r'[\'"]\/[^\'\"]*[\'"]',  # Absolute paths
        r'\.\.\/|\.\/|\~\/',     # Relative paths
        r'\b(file|directory|folder|path)\b',
    ]
    
    for pattern in filesystem_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            evaluation['mentions_filesystem'] = True
            break
    
    # Safety flag checks
    safety_flags = [
        (r'\b(execute|exec|eval|subprocess|system|shell)\b', 'Code execution detected'),
        (r'\b(password|secret|key|token|credential)\b', 'Potential secrets mentioned'),
        (r'\b(delete|remove|destroy|wipe|format)\b', 'Destructive operations mentioned'),
        (r'\b(network|http|url|download|upload)\b', 'Network operations mentioned'),
        (r'\b(sudo|admin|root|privilege)\b', 'Elevated privileges mentioned'),
    ]
    
    for pattern, flag_reason in safety_flags:
        if re.search(pattern, response, re.IGNORECASE):
            evaluation['flagged_content'].append(flag_reason)
    
    # Calculate confidence score
    base_score = 0.8
    
    # Reduce score for safety flags
    score_penalty = len(evaluation['flagged_content']) * 0.1
    
    # Adjust for task type context
    if task_type in ['fix_code', 'generate_plugin'] and evaluation['contains_code']:
        base_score += 0.1  # Code is expected for these tasks
    
    if task_type == 'self_debug' and evaluation['mentions_filesystem']:
        base_score += 0.05  # Filesystem mentions are normal for debugging
    
    evaluation['confidence_score'] = max(0.0, min(1.0, base_score - score_penalty))
    
    # Final safety determination
    if len(evaluation['flagged_content']) > 2:
        evaluation['is_safe'] = False
        evaluation['safety_notes'] = f"Multiple safety flags: {', '.join(evaluation['flagged_content'])}"
    elif evaluation['confidence_score'] < 0.3:
        evaluation['is_safe'] = False
        evaluation['safety_notes'] = 'Low confidence in response safety'
    else:
        evaluation['safety_notes'] = 'Response appears safe for PersonaOS use'
    
    return evaluation


def log_prompt_response(prompt: str, response: str, task_type: str, 
                       success: bool, model_used: str = 'unknown',
                       evaluation: Optional[ResponseEvaluation] = None) -> None:
    """
    Log prompt/response pairs for audit, learning, and debugging.
    
    Args:
        prompt: Original prompt sent
        response: Response received
        task_type: Type of task performed
        success: Whether the interaction was successful
        model_used: Which LLM was used
        evaluation: Optional response evaluation results
        
    TODO: Implement persistent logging with:
        - Structured log files (JSON)
        - Log rotation and cleanup
        - Privacy-preserving anonymization
        - Search and analysis tools
        - Export capabilities
    """
    timestamp = datetime.datetime.now().isoformat()
    
    log_entry: PromptLogEntry = {
        'timestamp': timestamp,
        'task_type': task_type,
        'prompt': prompt[:500] + '...' if len(prompt) > 500 else prompt,  # Truncate for logs
        'response': response[:1000] + '...' if len(response) > 1000 else response,
        'success': success,
        'model_used': model_used,
        'evaluation': evaluation
    }
    
    # Log to Python logging system
    log_level = logging.INFO if success else logging.WARNING
    logging.log(log_level, f"PromptEngine: {task_type} interaction", extra=log_entry)
    
    # TODO: Write to structured log file for persistence
    # TODO: Implement privacy filtering before logging
    # TODO: Add log analysis and reporting features


def get_available_task_types() -> List[str]:
    """
    Get list of available task types for prompt generation.
    
    Returns:
        List of supported task type strings
    """
    return list(PROMPT_TEMPLATES.keys())


def validate_prompt_parameters(task_type: str, parameters: Dict[str, Any]) -> bool:
    """
    Validate parameters for a given task type without generating the prompt.
    
    Args:
        task_type: Type of task to validate parameters for
        parameters: Parameters to validate
        
    Returns:
        True if parameters are valid, False otherwise
    """
    try:
        generate_prompt(task_type, parameters)
        return True
    except ValueError:
        return False


# Helper functions
def _extract_template_variables(template: str) -> List[str]:
    """Extract variable names from a template string."""
    import re
    pattern = r'\{(\w+)\}'
    return list(set(re.findall(pattern, template)))


def _add_default_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Add default values for common optional parameters."""
    defaults = {
        'context': parameters.get('context', 'No additional context provided'),
        'language': parameters.get('language', 'python'),
        'audience_level': parameters.get('audience_level', 'intermediate'),
        'output_format': parameters.get('output_format', 'JSON'),
        'environment_info': parameters.get('environment_info', 'PersonaOS v0.1.0'),
    }
    
    # Merge with original parameters, keeping original values
    result = {**defaults, **parameters}
    return result


def _sanitize_prompt(prompt: str) -> str:
    """Sanitize prompt content for safety."""
    # Remove potential injection attempts
    sanitized = prompt.replace('```system', '```text')
    sanitized = re.sub(r'<\|.*?\|>', '', sanitized)  # Remove special tokens
    
    # Limit prompt length
    max_length = 10000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + '\n\n[Prompt truncated for safety]'
    
    return sanitized


# Plugin interface for PersonaOS
class PromptEngineTool:
    """
    PromptEngine tool plugin interface for PersonaOS.
    Provides prompt generation and evaluation capabilities.
    """
    
    def __init__(self):
        self.name = "prompt_engine"
        self.description = "Generate, route, and evaluate prompts for LLM collaboration"
        self.version = "1.0.0"
    
    def generate(self, task_type: str, **kwargs) -> str:
        """Generate a prompt for the specified task type."""
        return generate_prompt(task_type, kwargs)
    
    def route(self, prompt: str, model: str = 'claude') -> str:
        """Route a prompt to the specified model."""
        return route_prompt(prompt, model)
    
    def evaluate(self, prompt: str, response: str, task_type: str = '') -> ResponseEvaluation:
        """Evaluate a response for safety and quality."""
        return evaluate_response(prompt, response, task_type)
    
    def log_interaction(self, prompt: str, response: str, task_type: str, success: bool) -> None:
        """Log a prompt/response interaction."""
        log_prompt_response(prompt, response, task_type, success)
    
    def get_task_types(self) -> List[str]:
        """Get available task types."""
        return get_available_task_types()


# Factory function for plugin loading
def create_tool():
    """Factory function to create the prompt engine tool instance."""
    return PromptEngineTool()


# Module initialization
if __name__ == "__main__":
    # Example usage
    params = {
        'plugin_name': 'calculator',
        'requirements': 'Basic arithmetic operations with error handling'
    }
    
    prompt = generate_prompt('generate_plugin', params)
    print("Generated prompt:")
    print(prompt)
    
    # Mock response evaluation
    mock_response = "Here's a calculator plugin with add, subtract, multiply functions..."
    evaluation = evaluate_response(prompt, mock_response, 'generate_plugin')
    print(f"\nResponse evaluation: {evaluation}")