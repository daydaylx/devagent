"""Tests for LLM client."""

from unittest.mock import Mock, patch

import pytest
import httpx

from devagent.llm import LLMClient


class TestLLMClient:
    """Test LLM client functionality."""

    def test_init(self, mock_config):
        """Test LLM client initialization."""
        client = LLMClient(mock_config)
        assert client.config == mock_config
        assert hasattr(client, 'logger')

    def test_generate_proposal_success(self, mock_config, mock_openrouter_response):
        """Test successful proposal generation."""
        client = LLMClient(mock_config)
        
        context = {
            "goal": "Add error handling",
            "project_structure": {"files": []},
            "checks": {"overall_status": "success"},
            "touch_files": {"src/api.ts": {"content": "export function api() {}"}},
            "relevant_summaries": {}
        }
        
        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_openrouter_response
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            result = client.generate_proposal(context)
            
            assert "patch" in result
            assert "commit_message" in result
            assert "test_plan" in result
            assert result["commit_message"] == "Add error handling and logging to API calls"

    def test_generate_proposal_with_model_override(self, mock_config, mock_openrouter_response):
        """Test proposal generation with model override."""
        client = LLMClient(mock_config)
        
        context = {
            "goal": "Test goal",
            "project_structure": {"files": []},
            "checks": {"overall_status": "success"},
            "touch_files": {},
            "relevant_summaries": {}
        }
        
        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_openrouter_response
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            result = client.generate_proposal(context, model_override="custom/model")
            
            # Verify the custom model was used
            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            payload = call_args[1]['json']
            assert payload['model'] == 'custom/model'

    def test_generate_proposal_http_error(self, mock_config):
        """Test handling of HTTP errors."""
        client = LLMClient(mock_config)
        
        context = {
            "goal": "Test goal",
            "project_structure": {"files": []},
            "checks": {"overall_status": "success"},
            "touch_files": {},
            "relevant_summaries": {}
        }
        
        with patch('httpx.Client') as mock_client:
            # Simulate HTTP error on all attempts
            mock_client.return_value.__enter__.return_value.post.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error", 
                request=Mock(), 
                response=Mock(status_code=500)
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                client.generate_proposal(context)

    def test_generate_proposal_retry_logic(self, mock_config, mock_openrouter_response):
        """Test retry logic on failures."""
        client = LLMClient(mock_config)
        
        context = {
            "goal": "Test goal",
            "project_structure": {"files": []},
            "checks": {"overall_status": "success"},
            "touch_files": {},
            "relevant_summaries": {}
        }
        
        with patch('httpx.Client') as mock_client, patch('time.sleep'):
            mock_post = mock_client.return_value.__enter__.return_value.post
            
            # First two calls fail, third succeeds
            mock_response_success = Mock()
            mock_response_success.json.return_value = mock_openrouter_response
            mock_response_success.raise_for_status.return_value = None
            
            mock_post.side_effect = [
                httpx.ConnectError("Connection failed"),
                httpx.ReadTimeout("Timeout"),
                mock_response_success
            ]
            
            result = client.generate_proposal(context)
            
            # Should have retried and succeeded
            assert mock_post.call_count == 3
            assert "patch" in result

    def test_parse_response_valid(self, mock_config):
        """Test parsing of valid AI response."""
        client = LLMClient(mock_config)
        
        content = '''**ANALYSIS**
This is the analysis.

**PLAN**
This is the plan.

**PATCH**
```diff
--- file.txt
+++ file.txt
@@ -1 +1,2 @@
 original line
+new line
```

**COMMIT MESSAGE**
Test commit message

**TEST PLAN**
Test the changes

**ROLLBACK**
Use git restore'''
        
        result = client._parse_response(content)
        
        assert result["analysis"] == "This is the analysis."
        assert result["plan"] == "This is the plan."
        assert result["commit_message"] == "Test commit message"
        assert result["test_plan"] == "Test the changes"
        assert result["rollback"] == "Use git restore"
        assert "--- file.txt" in result["patch"]

    def test_parse_response_missing_patch(self, mock_config):
        """Test handling of response without patch."""
        client = LLMClient(mock_config)
        
        content = '''**ANALYSIS**
Analysis without patch.

**COMMIT MESSAGE**
Message'''
        
        with pytest.raises(ValueError, match="No valid patch found"):
            client._parse_response(content)

    def test_parse_response_fallback_formats(self, mock_config):
        """Test parsing fallback patch formats."""
        client = LLMClient(mock_config)
        
        # Test with generic code block
        content = '''**PATCH**
```
--- file.txt
+++ file.txt
@@ -1 +1,2 @@
 original
+new line
```

**COMMIT MESSAGE**
Test'''
        
        result = client._parse_response(content)
        assert "--- file.txt" in result["patch"]

    def test_validate_payload_size(self, mock_config):
        """Test payload size validation."""
        client = LLMClient(mock_config)
        
        # Normal size payload should pass
        normal_payload = {
            "messages": [
                {"content": "short message"}
            ],
            "max_tokens": 1000
        }
        client._validate_payload(normal_payload)  # Should not raise
        
        # Extremely large payload should fail
        large_content = "x" * 500000  # Very large content
        large_payload = {
            "messages": [
                {"content": large_content}
            ],
            "max_tokens": 1000
        }
        
        with pytest.raises(ValueError, match="Context too large"):
            client._validate_payload(large_payload)

    def test_clean_patch_content(self, mock_config):
        """Test patch content cleaning."""
        client = LLMClient(mock_config)
        
        # Test removing markdown artifacts
        dirty_patch = '''```diff
--- file.txt
+++ file.txt
@@ -1 +1,2 @@
 line
+new
```'''
        
        clean = client._clean_patch_content(dirty_patch)
        assert not clean.startswith('```')
        assert not clean.endswith('```')
        assert '--- file.txt' in clean

    def test_validate_patch_format(self, mock_config):
        """Test patch format validation."""
        client = LLMClient(mock_config)
        
        # Valid diff format
        valid_patch = """--- file.txt
+++ file.txt
@@ -1 +1,2 @@
 original
+new line"""
        
        assert client._validate_patch_format(valid_patch) == True
        
        # Invalid format
        invalid_patch = "just some random text"
        assert client._validate_patch_format(invalid_patch) == False
        
        # Empty patch
        assert client._validate_patch_format("") == False

    def test_validate_response_sections(self, mock_config):
        """Test response section validation."""
        client = LLMClient(mock_config)
        
        # Valid response
        valid_response = {
            "patch": "--- file.txt\n+++ file.txt\n",
            "commit_message": "Test commit",
            "test_plan": "Test plan",
            "rollback": "Rollback plan",
            "analysis": "",
            "plan": ""
        }
        
        client._validate_response_sections(valid_response)  # Should not raise
        
        # Missing patch should raise
        invalid_response = {
            "patch": "",
            "commit_message": "Test",
            "test_plan": "",
            "rollback": "",
            "analysis": "",
            "plan": ""
        }
        
        with pytest.raises(ValueError, match="Missing required patch section"):
            client._validate_response_sections(invalid_response)

    def test_make_request_with_retry_empty_response(self, mock_config):
        """Test handling of empty API response."""
        client = LLMClient(mock_config)
        
        payload = {"messages": [{"content": "test"}]}
        
        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": ""}}]
            }
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            with pytest.raises(ValueError, match="Empty response content"):
                client._make_request_with_retry(payload)