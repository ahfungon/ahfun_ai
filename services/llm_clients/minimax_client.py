"""MiniMax client for summary generation and message scoring."""
import json
import logging
import re
import time
from typing import Dict, Any, Optional
import requests

from .base_client import BaseLLMClient, LLMClientError, LLMTimeoutError, LLMRateLimitError

logger = logging.getLogger(__name__)


def _extract_json_from_response(content: str) -> str:
    """
    Extract clean JSON from MiniMax response content.
    
    MiniMax models (especially M2.5-highspeed) may return content with:
    1. <think>...</think> reasoning tags
    2. ```json ... ``` markdown code blocks
    3. Both combined
    
    This function strips those wrappers to get the raw JSON string.
    """
    if not content:
        return content
    
    # Step 1: Remove <think>...</think> blocks (including newlines)
    cleaned = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
    
    # Step 2: Extract from ```json ... ``` code blocks if present
    code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, flags=re.DOTALL)
    if code_block_match:
        cleaned = code_block_match.group(1).strip()
    
    # Step 3: If still not valid JSON, try to find a JSON object in the text
    if cleaned and not cleaned.startswith('{'):
        json_match = re.search(r'\{[^{}]*\}', cleaned, flags=re.DOTALL)
        if json_match:
            cleaned = json_match.group(0).strip()
    
    return cleaned


class MiniMaxClient(BaseLLMClient):
    """
    Client for MiniMax API for summary generation and message scoring.
    
    This client is used to generate conversation summaries with LLM suggestions
    and end scores for guiding dialogue flow.
    """
    
    def __init__(
        self,
        api_key: str,
        api_url: str,
        timeout: int = 60,
        max_retries: int = 5,
        retry_delays: list[int] = None,
        model: str = "MiniMax-M2.5"
    ):
        """
        Initialize MiniMax client.
        
        Args:
            api_key: MiniMax API key
            api_url: MiniMax API endpoint URL
            timeout: Request timeout in seconds (default: 60)
            max_retries: Maximum retry attempts (default: 5)
            retry_delays: Retry delay intervals (default: [2, 4, 8, 12, 16])
            model: Model name to use (default: "MiniMax-M2.5")
        """
        super().__init__(api_key, api_url, timeout, max_retries, retry_delays or [2, 4, 8, 12, 16])
        self.model = model
    
    def generate_summary(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 2000
    ) -> Dict[str, Any]:
        """
        Generate conversation summary using MiniMax API.
        
        Args:
            prompt: Summary generation prompt
            temperature: Sampling temperature (default: 0.3 for more focused output)
            max_tokens: Maximum tokens to generate (default: 2000)
        
        Returns:
            Dictionary containing:
                - summary: Generated summary text
                - suggestion: LLM suggestion (continue/change_angle/suggest_end/force_end)
                - end_score: End score (0-100)
        
        Raises:
            LLMClientError: If API call fails
            LLMTimeoutError: If request times out
            LLMRateLimitError: If rate limit exceeded
        """
        request_params = {
            "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "model": self.model
        }
        
        start_time = time.time()
        
        try:
            response = self.call_with_retry(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful request
            self.log_request(
                operation="generate_summary",
                request_params=request_params,
                response=response,
                duration_ms=duration_ms
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log failed request
            self.log_request(
                operation="generate_summary",
                request_params=request_params,
                error=e,
                duration_ms=duration_ms
            )
            
            raise
    
    def _make_request(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 2000
    ) -> Dict[str, Any]:
        """
        Make actual API request to MiniMax.
        
        Args:
            prompt: Summary generation prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Parsed API response with summary, suggestion, and end_score
        
        Raises:
            LLMClientError: If API call fails
            LLMTimeoutError: If request times out
            LLMRateLimitError: If rate limit exceeded
        """
        if not self.api_key:
            raise LLMClientError("MiniMax API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Format as chat message
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}  # Request JSON response
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                raise LLMRateLimitError("MiniMax API rate limit exceeded")
            
            # Handle other errors
            if response.status_code != 200:
                error_detail = response.text
                raise LLMClientError(
                    f"MiniMax API error (status {response.status_code}): {error_detail}"
                )
            
            data = response.json()
            
            # Extract response content
            if "choices" not in data or not data["choices"]:
                raise LLMClientError("Invalid response format: missing choices")
            
            raw_content = data["choices"][0].get("message", {}).get("content", "")
            
            # Clean response: strip <think> tags and markdown code blocks
            content = _extract_json_from_response(raw_content)
            
            # Parse JSON response
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON after cleaning. Raw: {raw_content[:500]}")
                raise LLMClientError(f"Failed to parse JSON response: {str(e)}")
            
            # Extract and validate fields
            summary = parsed_content.get("summary", "")
            suggestion = parsed_content.get("suggestion", "continue")
            end_score = float(parsed_content.get("end_score", 0.0))
            
            # Validate suggestion
            valid_suggestions = ["continue", "change_angle", "suggest_end", "force_end"]
            if suggestion not in valid_suggestions:
                logger.warning(
                    f"Invalid suggestion '{suggestion}' from MiniMax, defaulting to 'continue'"
                )
                suggestion = "continue"
            
            # Validate end_score range
            if not (0 <= end_score <= 100):
                logger.warning(
                    f"Invalid end_score {end_score} from MiniMax, clamping to [0, 100]"
                )
                end_score = max(0.0, min(100.0, end_score))
            
            return {
                "summary": summary,
                "suggestion": suggestion,
                "end_score": end_score
            }
            
        except requests.Timeout:
            raise LLMTimeoutError(f"MiniMax API request timed out after {self.timeout}s")
        
        except requests.RequestException as e:
            raise LLMClientError(f"MiniMax API request failed: {str(e)}")
        
        except (KeyError, ValueError) as e:
            raise LLMClientError(f"Failed to parse MiniMax API response: {str(e)}")

    def evaluate_message_relevance(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 500
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate message relevance using MiniMax API.
        
        This method is designed for async scoring and returns None on failure
        instead of raising exceptions. Includes retry logic for transient errors.
        
        Args:
            prompt: Evaluation prompt
            temperature: Sampling temperature (default: 0.3)
            max_tokens: Maximum tokens to generate (default: 500)
        
        Returns:
            Dictionary containing:
                - relevance_score: Score (0-100)
                - evaluation_comment: Brief comment
            Returns None if evaluation fails
        """
        if not self.api_key:
            logger.error("MiniMax API key not configured")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }
        
        max_retries = self.max_retries
        retry_delays = self.retry_delays
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.api_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                # Retry on 5xx server errors and 429 rate limit
                if response.status_code == 429 or (500 <= response.status_code < 600):
                    if attempt < max_retries - 1:
                        delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                        logger.warning(
                            f"MiniMax scoring API error {response.status_code}, "
                            f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"MiniMax scoring failed after {max_retries} attempts. "
                            f"Last status: {response.status_code}, body: {response.text[:300]}"
                        )
                        return None
                
                if response.status_code != 200:
                    logger.error(f"MiniMax scoring API error (status {response.status_code}): {response.text}")
                    return None
                
                data = response.json()
                
                if "choices" not in data or not data["choices"]:
                    logger.error("Invalid response format: missing choices")
                    return None
                
                raw_content = data["choices"][0].get("message", {}).get("content", "")
                
                # Clean response: strip <think> tags and markdown code blocks
                content = _extract_json_from_response(raw_content)
                
                # Parse JSON response
                try:
                    parsed_content = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse scoring JSON after cleaning. Raw: {raw_content[:500]}")
                    return None
                
                # Extract and validate fields
                relevance_score = float(parsed_content.get("relevance_score", 0.0))
                evaluation_comment = parsed_content.get("evaluation_comment", "")
                
                # Validate score range
                if not (0 <= relevance_score <= 100):
                    logger.warning(f"Invalid relevance_score {relevance_score}, clamping to [0, 100]")
                    relevance_score = max(0.0, min(100.0, relevance_score))
                
                if attempt > 0:
                    logger.info(f"MiniMax scoring succeeded on attempt {attempt + 1}")
                
                return {
                    "relevance_score": relevance_score,
                    "evaluation_comment": evaluation_comment
                }
                
            except requests.Timeout:
                if attempt < max_retries - 1:
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                    logger.warning(f"MiniMax scoring timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                logger.error(f"MiniMax scoring timed out after {max_retries} attempts")
                return None
                
            except Exception as e:
                logger.error(f"Failed to evaluate message relevance: {e}", exc_info=True)
                return None
        
        return None
            
        except Exception as e:
            logger.error(f"Failed to evaluate message relevance: {e}", exc_info=True)
            return None
