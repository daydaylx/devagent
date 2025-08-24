"""Input validation and security utilities for DevAgent."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .logging import get_logger

logger = get_logger(__name__)


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_file_path(file_path: Union[str, Path], base_path: Optional[Path] = None) -> Path:
    """Validate and sanitize file path.
    
    Args:
        file_path: Path to validate
        base_path: Base path to restrict access to
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If path is invalid
        SecurityError: If path is outside allowed area
    """
    if isinstance(file_path, str):
        path = Path(file_path)
    else:
        path = file_path
    
    # Basic validation
    if not path:
        raise ValidationError("Empty file path")
    
    # Convert to absolute path
    try:
        path = path.resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid path: {e}")
    
    # Security checks
    path_str = str(path)
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r"\.\./",  # Directory traversal
        r"\.\.\\" if os.name == "nt" else "",  # Windows directory traversal
        r"/etc/",  # System directories
        r"/proc/",
        r"/sys/",
        r"C:\\Windows\\" if os.name == "nt" else "",  # Windows system dirs
    ]
    
    for pattern in dangerous_patterns:
        if pattern and re.search(pattern, path_str, re.IGNORECASE):
            raise SecurityError(f"Dangerous path pattern detected: {path}")
    
    # Restrict to base path if provided
    if base_path:
        try:
            base_resolved = base_path.resolve()
            path.relative_to(base_resolved)
        except ValueError:
            raise SecurityError(f"Path outside allowed area: {path}")
    
    return path


def validate_api_key(api_key: str) -> str:
    """Validate API key format.
    
    Args:
        api_key: API key to validate
        
    Returns:
        Validated API key
        
    Raises:
        ValidationError: If API key is invalid
    """
    if not api_key:
        raise ValidationError("API key is required")
    
    if not isinstance(api_key, str):
        raise ValidationError("API key must be a string")
    
    # Basic format checks
    api_key = api_key.strip()
    
    if len(api_key) < 10:
        raise ValidationError("API key too short")
    
    if len(api_key) > 500:
        raise ValidationError("API key too long")
    
    # Check for obviously invalid keys
    if api_key.lower() in ["your_api_key_here", "replace_me", "example", "test"]:
        raise ValidationError("Invalid placeholder API key")
    
    return api_key


def validate_model_name(model: str) -> str:
    """Validate LLM model name.
    
    Args:
        model: Model name to validate
        
    Returns:
        Validated model name
        
    Raises:
        ValidationError: If model name is invalid
    """
    if not model:
        raise ValidationError("Model name is required")
    
    if not isinstance(model, str):
        raise ValidationError("Model name must be a string")
    
    model = model.strip()
    
    # Basic format validation
    if not re.match(r"^[a-zA-Z0-9/_\-\.]+$", model):
        raise ValidationError(f"Invalid model name format: {model}")
    
    if len(model) > 200:
        raise ValidationError("Model name too long")
    
    return model


def validate_file_content(content: str, max_size_mb: int = 10) -> str:
    """Validate file content for security and size limits.
    
    Args:
        content: File content to validate
        max_size_mb: Maximum size in megabytes
        
    Returns:
        Validated content
        
    Raises:
        ValidationError: If content is invalid
        SecurityError: If content contains dangerous patterns
    """
    if not isinstance(content, str):
        raise ValidationError("Content must be a string")
    
    # Size check
    size_mb = len(content.encode('utf-8')) / (1024 * 1024)
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", str(max_size_mb)))
    
    if size_mb > max_size:
        raise ValidationError(f"File too large: {size_mb:.1f}MB (max {max_size}MB)")
    
    # Security patterns to detect
    security_patterns = [
        r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"]?[^'\"\s]+",  # Password patterns
        r"(?i)(api[_-]?key|secret|token)\s*[=:]\s*['\"]?[^'\"\s]+",  # API keys
        r"(?i)(private[_-]?key|priv[_-]?key)\s*[=:]\s*['\"]?[^'\"\s]+",  # Private keys
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",  # PEM private keys
        r"ssh-rsa [A-Za-z0-9+/]+",  # SSH keys
    ]
    
    for pattern in security_patterns:
        if re.search(pattern, content):
            logger.warning("Potentially sensitive data detected in file content")
            # Don't raise error, just log warning
            break
    
    return content


def sanitize_patch_content(patch: str) -> str:
    """Sanitize patch content to prevent injection attacks.
    
    Args:
        patch: Patch content to sanitize
        
    Returns:
        Sanitized patch content
        
    Raises:
        SecurityError: If patch contains dangerous content
    """
    if not isinstance(patch, str):
        raise ValidationError("Patch must be a string")
    
    # Check for potentially dangerous shell commands in patches
    dangerous_commands = [
        r"rm\s+-rf",  # Destructive file operations
        r"sudo\s+",   # Privilege escalation
        r"curl\s+.*\|.*sh",  # Download and execute
        r"wget\s+.*\|.*sh",  # Download and execute
        r"eval\s*\(",  # Code evaluation
        r"exec\s*\(",  # Code execution
        r"system\s*\(",  # System calls
        r"`[^`]*`",   # Command substitution
        r"\$\([^)]*\)",  # Command substitution
    ]
    
    for pattern in dangerous_commands:
        if re.search(pattern, patch, re.IGNORECASE):
            raise SecurityError(f"Dangerous command detected in patch: {pattern}")
    
    # Size limit
    max_patch_size = int(os.getenv("MAX_PATCH_SIZE_KB", "1000")) * 1024
    if len(patch.encode('utf-8')) > max_patch_size:
        raise ValidationError("Patch too large")
    
    return patch


def validate_environment_config() -> Dict[str, Any]:
    """Validate environment configuration.
    
    Returns:
        Dictionary of validated config values
        
    Raises:
        ValidationError: If configuration is invalid
    """
    config = {}
    errors = []
    
    # Required settings
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if api_key:
        try:
            config["api_key"] = validate_api_key(api_key)
        except ValidationError as e:
            errors.append(f"OPENROUTER_API_KEY: {e}")
    else:
        errors.append("OPENROUTER_API_KEY is required")
    
    # Optional model validation
    model = os.getenv("OPENROUTER_MODEL", "")
    if model:
        try:
            config["model"] = validate_model_name(model)
        except ValidationError as e:
            errors.append(f"OPENROUTER_MODEL: {e}")
    
    # Timeout validation
    try:
        timeout = int(os.getenv("OPENROUTER_TIMEOUT", "300"))
        if timeout < 10 or timeout > 3600:
            errors.append("OPENROUTER_TIMEOUT must be between 10 and 3600 seconds")
        else:
            config["timeout"] = timeout
    except ValueError:
        errors.append("OPENROUTER_TIMEOUT must be an integer")
    
    # Rate limiting
    try:
        rate_limit = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
        if rate_limit < 1 or rate_limit > 1000:
            errors.append("RATE_LIMIT_REQUESTS_PER_MINUTE must be between 1 and 1000")
        else:
            config["rate_limit"] = rate_limit
    except ValueError:
        errors.append("RATE_LIMIT_REQUESTS_PER_MINUTE must be an integer")
    
    if errors:
        raise ValidationError("Configuration validation failed: " + "; ".join(errors))
    
    return config


def validate_command_args(command: str, args: List[str]) -> tuple[str, List[str]]:
    """Validate shell command and arguments for safety.
    
    Args:
        command: Command to validate
        args: Command arguments
        
    Returns:
        Tuple of validated command and args
        
    Raises:
        SecurityError: If command is dangerous
    """
    if not command:
        raise ValidationError("Command cannot be empty")
    
    # Whitelist of allowed commands
    allowed_commands = {
        "npm", "npx", "node", "yarn", "pnpm",  # Node.js
        "python", "python3", "pip", "pytest", "pyright",  # Python
        "tsc", "eslint", "prettier",  # TypeScript/JavaScript tools
        "git", "diff", "patch",  # Version control
        "ls", "cat", "head", "tail", "grep", "find",  # Basic utilities (read-only)
    }
    
    command_name = Path(command).name.lower()
    
    if command_name not in allowed_commands:
        raise SecurityError(f"Command not allowed: {command}")
    
    # Check arguments for dangerous patterns
    dangerous_arg_patterns = [
        r"--eval",
        r"--exec",
        r"-e\s*['\"]",  # Inline code execution
        r">\s*/",      # Writing to system directories
        r"\|\s*sh",    # Piping to shell
        r"\|\s*bash",  # Piping to bash
        r"&&\s*rm",    # Chaining with destructive commands
    ]
    
    for arg in args:
        for pattern in dangerous_arg_patterns:
            if re.search(pattern, arg, re.IGNORECASE):
                raise SecurityError(f"Dangerous argument pattern: {arg}")
    
    return command, args