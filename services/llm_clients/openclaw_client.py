"""OpenClaw client for dialogue generation with actual token counting."""
import json
import logging
import time
from typing import Dict, Any, Optional
import requests

from .base_client import BaseLLMClient, LLMClientError, LLMTimeoutError, LLMRateLimitError

logger = logging.getLogger(__name__)


class OpenClawClient(BaseLLMClient):
    """
    Client for OpenClaw API for dialogue generation.
    
    This client is used to generate agent dialogues and returns actual token counts
    from the LLM response, ensuring accurate token tracking for summary triggers.
    """
    
    def __init__(
        self,
        api_key: str,
        api_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delays: list[int] = None,
        model: str = "openclaw-chat"
    ):
        """
        Initialize OpenClaw client.
        
        Args:
            api_key: OpenClaw API key
            api_url: OpenClaw API endpoint URL
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
            retry_delays: Retry delay intervals (default: [1, 2, 4])
            model: Model name to use (default: "openclaw-chat")
        """
        super().__init__(api_key, api_url, timeout, max_retries, retry_delays)
        self.model = model
    
    def generate_dialogue(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate dialogue using OpenClaw API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (default: 0.7)
            max_tokens: Maximum tokens to generate (optional)
        
        Returns:
            Dictionary containing:
                - content: Generated text
                - actual_tokens: Actual token count from LLM
                - model: Model used
                - finish_reason: Reason for completion
        
        Raises:
            LLMClientError: If API call fails
            LLMTimeoutError: If request times out
            LLMRateLimitError: If rate limit exceeded
        """
        request_params = {
            "messages": messages,
            "temperature": temperature,
            "model": self.model
        }
        
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        
        start_time = time.time()
        
        try:
            response = self.call_with_retry(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful request
            self.log_request(
                operation="generate_dialogue",
                request_params=request_params,
                response=response,
                duration_ms=duration_ms
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log failed request
            self.log_request(
                operation="generate_dialogue",
                request_params=request_params,
                error=e,
                duration_ms=duration_ms
            )
            
            raise
    
    def _make_request(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make actual API request to OpenClaw.
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Parsed API response with actual token count
        
        Raises:
            LLMClientError: If API call fails
            LLMTimeoutError: If request times out
            LLMRateLimitError: If rate limit exceeded
        """
        if not self.api_key:
            raise LLMClientError("OpenClaw API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                raise LLMRateLimitError("OpenClaw API rate limit exceeded")
            
            # Handle other errors
            if response.status_code != 200:
                error_detail = response.text
                raise LLMClientError(
                    f"OpenClaw API error (status {response.status_code}): {error_detail}"
                )
            
            data = response.json()
            
            # Extract response data
            # Expected format similar to OpenAI API:
            # {
            #   "choices": [{"message": {"content": "..."}}],
            #   "usage": {"total_tokens": 123}
            # }
            
            if "choices" not in data or not data["choices"]:
                raise LLMClientError("Invalid response format: missing choices")
            
            content = data["choices"][0].get("message", {}).get("content", "")
            
            # Get actual token count from usage field
            usage = data.get("usage", {})
            actual_tokens = usage.get("total_tokens", 0)
            
            if actual_tokens == 0:
                logger.warning("OpenClaw API did not return token count, estimating...")
                # Fallback: estimate tokens (rough approximation)
                actual_tokens = len(content) // 4
            
            return {
                "content": content,
                "actual_tokens": actual_tokens,
                "model": data.get("model", self.model),
                "finish_reason": data["choices"][0].get("finish_reason", "stop")
            }
            
        except requests.Timeout:
            raise LLMTimeoutError(f"OpenClaw API request timed out after {self.timeout}s")
        
        except requests.RequestException as e:
            raise LLMClientError(f"OpenClaw API request failed: {str(e)}")
        
        except (KeyError, json.JSONDecodeError) as e:
            raise LLMClientError(f"Failed to parse OpenClaw API response: {str(e)}")
