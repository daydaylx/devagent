"""OpenRouter LLM client for generating proposals."""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from .config import Config
from .logging import get_logger


class LLMClient:
    """Client for OpenRouter LLM API with retry logic and validation."""
    
    API_BASE_URL = "https://openrouter.ai/api/v1"
    TIMEOUT = 300  # 5 minutes
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff
    
    def __init__(self, config: Config) -> None:
        """Initialize LLM client.
        
        Args:
            config: Configuration instance with API keys and settings
        """
        self.config = config
        self.logger = get_logger(__name__)
    
    def generate_proposal(
        self, 
        context: Dict[str, Any], 
        model_override: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate code change proposal with retry logic.
        
        Args:
            context: Project context with files, goals, and check results
            model_override: Optional model override
            
        Returns:
            Parsed response with patch, commit message, etc.
            
        Raises:
            ValueError: If response parsing fails
            httpx.HTTPError: If API request fails after retries
        """
        model = model_override or self.config.openrouter_model
        
        self.logger.info("Generating proposal", extra={
            "model": model,
            "context_keys": list(context.keys()),
            "goal": context.get("goal", "Unknown")
        })
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(context)
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 4000,
            "temperature": 0.1,
        }
        
        # Validate payload size
        self._validate_payload(payload)
        
        # Make request with retries
        response_content = self._make_request_with_retry(payload)
        
        # Parse and validate response
        return self._parse_response(response_content)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for AI."""
        return """You are an expert software engineer. Your task is to analyze the provided context and generate precise code changes.

Your response MUST follow this exact structure:

**ANALYSIS**
Analyze the current codebase, goal, and any issues found in checks.

**PLAN** Outline the specific changes needed to achieve the goal.

**PATCH**
```diff
[Provide a single, complete unified diff with proper hunks]
COMMIT MESSAGE
Write a clear, conventional commit message.
TEST PLAN
Describe how to test the changes.
ROLLBACK
Explain how to rollback if needed.
Requirements:

The diff must be a proper unified diff format
Include complete context lines (3+ lines before/after changes)
Only modify files that are provided in the context
Be precise and minimal - only change what's necessary
Ensure all syntax is correct
Handle edge cases and error conditions"""

def _build_user_prompt(self, context: Dict[str, Any]) -> str:
    """Build user prompt from context."""
    prompt_parts = [f"Goal: {context['goal']}\n"]
  
    # Project structure
    if "error" not in context["project_structure"]:
        files = context["project_structure"].get("files", [])
        file_list = [f"- {f['path']}" for f in files[:30]]  # Limit to avoid token overflow
        prompt_parts.append(f"Project Structure ({len(files)} files):")
        prompt_parts.append("\n".join(file_list))
        if len(files) > 30:
            prompt_parts.append(f"... and {len(files) - 30} more files")
        prompt_parts.append("")
    
    # Checks results
    if "error" not in context["checks"]:
        checks = context["checks"]
        prompt_parts.append(f"Project Health: {checks['overall_status']}")
        if checks.get("summary"):
            prompt_parts.append(f"Issues: {checks['summary']}")
        prompt_parts.append("")
    
    # Touch files content
    if "error" not in context["touch_files"]:
        prompt_parts.append("Files to modify:")
        for file_path, file_info in context["touch_files"].items():
            if "error" in file_info:
                prompt_parts.append(f"{file_path}: {file_info['error']}")
            else:
                prompt_parts.append(f"\n--- {file_path} ---")
                prompt_parts.append(file_info["content"])
    
    # Relevant summaries
    if context["relevant_summaries"]:
        prompt_parts.append("\nRelated Files Context:")
        for file_path, summary in context["relevant_summaries"].items():
            prompt_parts.append(f"- {file_path}: {summary}")
    
    return "\n".join(prompt_parts)

    def _make_request_with_retry(self, payload: Dict[str, Any]) -> str:
        """Make HTTP request with exponential backoff retry.
        
        Args:
            payload: Request payload
            
        Returns:
            Response content
            
        Raises:
            httpx.HTTPError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                self.logger.debug(f"API request attempt {attempt + 1}/{self.MAX_RETRIES}")
                
                with httpx.Client(timeout=self.TIMEOUT) as client:
                    response = client.post(
                        f"{self.API_BASE_URL}/chat/completions",
                        headers=self.config.openrouter_headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Validate response structure
                    if "choices" not in data or not data["choices"]:
                        raise ValueError("Invalid API response: missing choices")
                    
                    content = data["choices"][0]["message"]["content"]
                    if not content:
                        raise ValueError("Empty response content")
                    
                    self.logger.info("API request successful", extra={
                        "attempt": attempt + 1,
                        "response_length": len(content)
                    })
                    
                    return content
                    
            except (httpx.HTTPError, ValueError) as e:
                last_exception = e
                self.logger.warning(f"API request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt]
                    self.logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        # All retries failed
        self.logger.error(f"All API request attempts failed. Last error: {last_exception}")
        raise last_exception
    
    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        """Validate request payload.
        
        Args:
            payload: Request payload to validate
            
        Raises:
            ValueError: If payload is invalid
        """
        # Estimate token count (rough approximation: 4 chars = 1 token)
        total_chars = 0
        for message in payload["messages"]:
            total_chars += len(message["content"])
        
        estimated_tokens = total_chars // 4
        max_context_tokens = 100000  # Conservative estimate
        
        if estimated_tokens > max_context_tokens:
            raise ValueError(
                f"Context too large: {estimated_tokens} estimated tokens "
                f"(max {max_context_tokens})"
            )
        
        self.logger.debug("Payload validated", extra={
            "estimated_tokens": estimated_tokens,
            "max_tokens": payload["max_tokens"]
        })

    def _parse_response(self, content: str) -> Dict[str, str]:
        """Parse AI response into structured format with enhanced validation.
        
        Args:
            content: Raw AI response content
            
        Returns:
            Parsed response sections
            
        Raises:
            ValueError: If response cannot be parsed or is invalid
        """
        self.logger.debug("Parsing AI response", extra={
            "content_length": len(content)
        })
        
        result = {
            "analysis": "",
            "plan": "",
            "patch": "",
            "commit_message": "",
            "test_plan": "",
            "rollback": "",
        }
        
        # Enhanced section patterns with more flexibility
        sections = {
            "analysis": r"\*\*ANALYSIS\*\*\s*(.*?)(?=\*\*(?:PLAN|PATCH)\*\*|$)",
            "plan": r"\*\*PLAN\*\*\s*(.*?)(?=\*\*(?:PATCH|COMMIT MESSAGE)\*\*|$)",
            "commit_message": r"\*\*COMMIT MESSAGE\*\*\s*(.*?)(?=\*\*(?:TEST PLAN|ROLLBACK)\*\*|$)",
            "test_plan": r"\*\*TEST PLAN\*\*\s*(.*?)(?=\*\*ROLLBACK\*\*|$)",
            "rollback": r"\*\*ROLLBACK\*\*\s*(.*?)$",
        }
        
        # Extract patch with multiple fallback strategies
        patch_patterns = [
            r"```diff\s*\n(.*?)\n```",  # Standard diff block
            r"```patch\s*\n(.*?)\n```",  # Patch block
            r"```\s*\n(.*?)\n```",     # Generic code block
            r"\*\*PATCH\*\*\s*(.*?)(?=\*\*COMMIT MESSAGE\*\*|$)",  # Fallback
        ]
        
        patch_found = False
        for pattern in patch_patterns:
            patch_match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if patch_match:
                patch_content = patch_match.group(1).strip()
                
                # Clean up patch content
                patch_content = self._clean_patch_content(patch_content)
                
                if patch_content and self._validate_patch_format(patch_content):
                    result["patch"] = patch_content
                    patch_found = True
                    break
        
        if not patch_found:
            self.logger.error("No valid patch found in response")
            raise ValueError("No valid patch found in AI response")
        
        # Extract other sections
        for section, pattern in sections.items():
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                result[section] = match.group(1).strip()
        
        # Validate required sections
        self._validate_response_sections(result)
        
        self.logger.info("Response parsed successfully", extra={
            "sections_found": [k for k, v in result.items() if v],
            "patch_lines": len(result["patch"].split("\n"))
        })
        
        return result
    
    def _clean_patch_content(self, content: str) -> str:
        """Clean and normalize patch content.
        
        Args:
            content: Raw patch content
            
        Returns:
            Cleaned patch content
        """
        # Remove markdown code fence artifacts
        content = re.sub(r"```[a-zA-Z]*\n?", "", content)
        content = re.sub(r"\n?```", "", content)
        
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Normalize line endings
        content = content.replace("\r\n", "\n")
        
        return content
    
    def _validate_patch_format(self, patch: str) -> bool:
        """Validate patch format.
        
        Args:
            patch: Patch content to validate
            
        Returns:
            True if patch format is valid
        """
        if not patch:
            return False
        
        lines = patch.split("\n")
        
        # Look for diff headers
        has_diff_headers = any(
            line.startswith(("---", "+++", "@@", "diff", "Index:"))
            for line in lines
        )
        
        # Look for diff content
        has_diff_content = any(
            line.startswith(("+", "-", " "))
            for line in lines
        )
        
        return has_diff_headers or has_diff_content
    
    def _validate_response_sections(self, result: Dict[str, str]) -> None:
        """Validate parsed response sections.
        
        Args:
            result: Parsed response sections
            
        Raises:
            ValueError: If validation fails
        """
        # Check for required sections
        if not result["patch"]:
            raise ValueError("Missing required patch section")
        
        # Warn about missing optional sections
        if not result["commit_message"]:
            self.logger.warning("Missing commit message in AI response")
            result["commit_message"] = "AI-generated changes"
        
        if not result["test_plan"]:
            self.logger.warning("Missing test plan in AI response")
            result["test_plan"] = "Manual testing recommended"
        
        if not result["rollback"]:
            self.logger.warning("Missing rollback plan in AI response")
            result["rollback"] = "Use `git restore` to revert changes"
