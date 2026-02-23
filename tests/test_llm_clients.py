"""Tests for LLM client wrappers."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from services.llm_clients import (
    OpenClawClient,
    DeepSeekClient,
    LLMClientError,
    LLMTimeoutError,
    LLMRateLimitError
)


class TestOpenClawClient:
    """Tests for OpenClawClient."""
    
    def test_init(self):
        """Test OpenClawClient initialization."""
        client = OpenClawClient(
            api_key="test-key",
            api_url="https://api.test.com",
            timeout=20,
            max_retries=2
        )
        
        assert client.api_key == "test-key"
        assert client.api_url == "https://api.test.com"
        assert client.timeout == 20
        assert client.max_retries == 2
        assert client.model == "openclaw-chat"
    
    @patch('services.llm_clients.openclaw_client.requests.post')
    def test_generate_dialogue_success(self, mock_post):
        """Test successful dialogue generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Hello, how can I help you?"},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 25},
            "model": "openclaw-chat"
        }
        mock_post.return_value = mock_response
        
        client = OpenClawClient(
            api_key="test-key",
            api_url="https://api.test.com"
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        result = client.generate_dialogue(messages)
        
        assert result["content"] == "Hello, how can I help you?"
        assert result["actual_tokens"] == 25
        assert result["model"] == "openclaw-chat"
        assert result["finish_reason"] == "stop"
        
        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.test.com/chat/completions"
        assert call_args[1]["json"]["messages"] == messages
    
    @patch('services.llm_clients.openclaw_client.requests.post')
    def test_generate_dialogue_timeout(self, mock_post):
        """Test dialogue generation with timeout."""
        mock_post.side_effect = requests.Timeout("Request timed out")
        
        client = OpenClawClient(
            api_key="test-key",
            api_url="https://api.test.com",
            max_retries=1
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(LLMClientError) as exc_info:
            client.generate_dialogue(messages)
        
        assert "retry attempts failed" in str(exc_info.value)
    
    @patch('services.llm_clients.openclaw_client.requests.post')
    def test_generate_dialogue_rate_limit(self, mock_post):
        """Test dialogue generation with rate limit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        client = OpenClawClient(
            api_key="test-key",
            api_url="https://api.test.com",
            max_retries=1
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(LLMClientError) as exc_info:
            client.generate_dialogue(messages)
        
        assert "retry attempts failed" in str(exc_info.value)
    
    @patch('services.llm_clients.openclaw_client.requests.post')
    def test_generate_dialogue_retry_success(self, mock_post):
        """Test dialogue generation with retry success."""
        # First call fails, second succeeds
        mock_fail = Mock()
        mock_fail.status_code = 500
        mock_fail.text = "Internal server error"
        
        mock_success = Mock()
        mock_success.status_code = 200
        mock_success.json.return_value = {
            "choices": [{
                "message": {"content": "Success after retry"},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 30}
        }
        
        mock_post.side_effect = [mock_fail, mock_success]
        
        client = OpenClawClient(
            api_key="test-key",
            api_url="https://api.test.com",
            max_retries=2,
            retry_delays=[0.1]  # Short delay for testing
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        result = client.generate_dialogue(messages)
        
        assert result["content"] == "Success after retry"
        assert result["actual_tokens"] == 30
        assert mock_post.call_count == 2
    
    def test_generate_dialogue_no_api_key(self):
        """Test dialogue generation without API key."""
        client = OpenClawClient(
            api_key="",
            api_url="https://api.test.com"
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(LLMClientError) as exc_info:
            client.generate_dialogue(messages)
        
        assert "API key not configured" in str(exc_info.value)


class TestDeepSeekClient:
    """Tests for DeepSeekClient."""
    
    def test_init(self):
        """Test DeepSeekClient initialization."""
        client = DeepSeekClient(
            api_key="test-key",
            api_url="https://api.test.com",
            timeout=25,
            max_retries=2
        )
        
        assert client.api_key == "test-key"
        assert client.api_url == "https://api.test.com"
        assert client.timeout == 25
        assert client.max_retries == 2
        assert client.model == "deepseek-chat"
    
    @patch('services.llm_clients.deepseek_client.requests.post')
    def test_generate_summary_success(self, mock_post):
        """Test successful summary generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"summary": "Test summary", "suggestion": "continue", "end_score": 25.5}'
                },
                "finish_reason": "stop"
            }]
        }
        mock_post.return_value = mock_response
        
        client = DeepSeekClient(
            api_key="test-key",
            api_url="https://api.test.com"
        )
        
        prompt = "Summarize this conversation..."
        result = client.generate_summary(prompt)
        
        assert result["summary"] == "Test summary"
        assert result["suggestion"] == "continue"
        assert result["end_score"] == 25.5
        
        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.test.com/chat/completions"
        assert "response_format" in call_args[1]["json"]
    
    @patch('services.llm_clients.deepseek_client.requests.post')
    def test_generate_summary_invalid_suggestion(self, mock_post):
        """Test summary generation with invalid suggestion."""
        # Mock response with invalid suggestion
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"summary": "Test", "suggestion": "invalid_value", "end_score": 50}'
                }
            }]
        }
        mock_post.return_value = mock_response
        
        client = DeepSeekClient(
            api_key="test-key",
            api_url="https://api.test.com"
        )
        
        result = client.generate_summary("Test prompt")
        
        # Should default to "continue"
        assert result["suggestion"] == "continue"
        assert result["summary"] == "Test"
    
    @patch('services.llm_clients.deepseek_client.requests.post')
    def test_generate_summary_invalid_end_score(self, mock_post):
        """Test summary generation with invalid end_score."""
        # Mock response with out-of-range end_score
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"summary": "Test", "suggestion": "continue", "end_score": 150}'
                }
            }]
        }
        mock_post.return_value = mock_response
        
        client = DeepSeekClient(
            api_key="test-key",
            api_url="https://api.test.com"
        )
        
        result = client.generate_summary("Test prompt")
        
        # Should clamp to 100
        assert result["end_score"] == 100.0
    
    @patch('services.llm_clients.deepseek_client.requests.post')
    def test_generate_summary_timeout(self, mock_post):
        """Test summary generation with timeout."""
        mock_post.side_effect = requests.Timeout("Request timed out")
        
        client = DeepSeekClient(
            api_key="test-key",
            api_url="https://api.test.com",
            max_retries=1
        )
        
        with pytest.raises(LLMClientError) as exc_info:
            client.generate_summary("Test prompt")
        
        assert "retry attempts failed" in str(exc_info.value)
    
    @patch('services.llm_clients.deepseek_client.requests.post')
    def test_generate_summary_rate_limit(self, mock_post):
        """Test summary generation with rate limit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        client = DeepSeekClient(
            api_key="test-key",
            api_url="https://api.test.com",
            max_retries=1
        )
        
        with pytest.raises(LLMClientError) as exc_info:
            client.generate_summary("Test prompt")
        
        assert "retry attempts failed" in str(exc_info.value)
    
    @patch('services.llm_clients.deepseek_client.requests.post')
    def test_generate_summary_retry_success(self, mock_post):
        """Test summary generation with retry success."""
        # First call fails, second succeeds
        mock_fail = Mock()
        mock_fail.status_code = 500
        mock_fail.text = "Internal server error"
        
        mock_success = Mock()
        mock_success.status_code = 200
        mock_success.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"summary": "Retry success", "suggestion": "continue", "end_score": 40}'
                }
            }]
        }
        
        mock_post.side_effect = [mock_fail, mock_success]
        
        client = DeepSeekClient(
            api_key="test-key",
            api_url="https://api.test.com",
            max_retries=2,
            retry_delays=[0.1]  # Short delay for testing
        )
        
        result = client.generate_summary("Test prompt")
        
        assert result["summary"] == "Retry success"
        assert mock_post.call_count == 2
    
    def test_generate_summary_no_api_key(self):
        """Test summary generation without API key."""
        client = DeepSeekClient(
            api_key="",
            api_url="https://api.test.com"
        )
        
        with pytest.raises(LLMClientError) as exc_info:
            client.generate_summary("Test prompt")
        
        assert "API key not configured" in str(exc_info.value)
    
    @patch('services.llm_clients.deepseek_client.requests.post')
    def test_generate_summary_invalid_json(self, mock_post):
        """Test summary generation with invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "This is not valid JSON"
                }
            }]
        }
        mock_post.return_value = mock_response
        
        client = DeepSeekClient(
            api_key="test-key",
            api_url="https://api.test.com",
            max_retries=1
        )
        
        with pytest.raises(LLMClientError) as exc_info:
            client.generate_summary("Test prompt")
        
        assert "retry attempts failed" in str(exc_info.value)


class TestBaseLLMClient:
    """Tests for base LLM client functionality."""
    
    @patch('services.llm_clients.openclaw_client.requests.post')
    def test_retry_delays(self, mock_post):
        """Test that retry delays are applied correctly."""
        mock_post.side_effect = requests.Timeout("Timeout")
        
        client = OpenClawClient(
            api_key="test-key",
            api_url="https://api.test.com",
            max_retries=3,
            retry_delays=[0.1, 0.2, 0.3]
        )
        
        import time
        start = time.time()
        
        with pytest.raises(LLMClientError):
            client.generate_dialogue([{"role": "user", "content": "test"}])
        
        elapsed = time.time() - start
        
        # Should have waited at least 0.1 + 0.2 = 0.3 seconds (not waiting after last attempt)
        assert elapsed >= 0.3
        assert mock_post.call_count == 3
    
    @patch('services.llm_clients.openclaw_client.requests.post')
    def test_logging_on_success(self, mock_post, caplog):
        """Test that successful requests are logged."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 10}
        }
        mock_post.return_value = mock_response
        
        client = OpenClawClient(
            api_key="test-key",
            api_url="https://api.test.com"
        )
        
        with caplog.at_level("INFO"):
            client.generate_dialogue([{"role": "user", "content": "test"}])
        
        # Check that success was logged
        assert any("Request successful" in record.message for record in caplog.records)
    
    @patch('services.llm_clients.openclaw_client.requests.post')
    def test_logging_on_failure(self, mock_post, caplog):
        """Test that failed requests are logged."""
        mock_post.side_effect = requests.Timeout("Timeout")
        
        client = OpenClawClient(
            api_key="test-key",
            api_url="https://api.test.com",
            max_retries=1
        )
        
        with caplog.at_level("WARNING"):
            with pytest.raises(LLMClientError):
                client.generate_dialogue([{"role": "user", "content": "test"}])
        
        # Check that failures were logged
        assert any("Timeout on attempt" in record.message for record in caplog.records)
