"""Base LLM client with common functionality."""
import time
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Base exception for LLM client errors."""
    pass


class LLMTimeoutError(LLMClientError):
    """Exception raised when LLM API call times out."""
    pass


class LLMRateLimitError(LLMClientError):
    """Exception raised when LLM API rate limit is exceeded."""
    pass


class BaseLLMClient(ABC):
    """Base class for LLM clients with retry and timeout logic."""
    
    def __init__(
        self,
        api_key: str,
        api_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delays: list[int] = None
    ):
        """
        Initialize base LLM client.
        
        Args:
            api_key: API key for authentication
            api_url: Base URL for API endpoint
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delays: List of delays between retries in seconds (default: [1, 2, 4])
        """
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delays = retry_delays or [1, 2, 4]
        
        if not api_key:
            logger.warning(f"{self.__class__.__name__}: API key not configured")
    
    @abstractmethod
    def _make_request(self, **kwargs) -> Dict[str, Any]:
        """
        Make the actual API request.
        
        This method should be implemented by subclasses to handle
        the specific API call logic.
        
        Args:
            **kwargs: Request parameters
        
        Returns:
            API response as dictionary
        
        Raises:
            LLMClientError: If API call fails
        """
        pass
    
    def call_with_retry(self, **kwargs) -> Dict[str, Any]:
        """
        Call LLM API with retry logic and exponential backoff.
        
        Args:
            **kwargs: Request parameters to pass to _make_request
        
        Returns:
            API response as dictionary
        
        Raises:
            LLMClientError: If all retry attempts fail
            LLMTimeoutError: If request times out
            LLMRateLimitError: If rate limit is exceeded
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"{self.__class__.__name__}: Attempt {attempt + 1}/{self.max_retries}"
                )
                
                start_time = time.time()
                response = self._make_request(**kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"{self.__class__.__name__}: Request successful "
                    f"(duration: {duration:.2f}s)"
                )
                
                return response
                
            except LLMTimeoutError as e:
                last_error = e
                logger.warning(
                    f"{self.__class__.__name__}: Timeout on attempt {attempt + 1}: {e}"
                )
                
            except LLMRateLimitError as e:
                last_error = e
                logger.warning(
                    f"{self.__class__.__name__}: Rate limit on attempt {attempt + 1}: {e}"
                )
                
            except LLMClientError as e:
                last_error = e
                logger.warning(
                    f"{self.__class__.__name__}: Error on attempt {attempt + 1}: {e}"
                )
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                logger.info(f"{self.__class__.__name__}: Retrying in {delay}s...")
                time.sleep(delay)
        
        # All retries failed
        error_msg = f"All {self.max_retries} retry attempts failed. Last error: {last_error}"
        logger.error(f"{self.__class__.__name__}: {error_msg}")
        raise LLMClientError(error_msg)
    
    def log_request(
        self,
        operation: str,
        request_params: Dict[str, Any],
        response: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """
        Log LLM API request and response.
        
        Args:
            operation: Operation name (e.g., "generate_dialogue", "generate_summary")
            request_params: Request parameters
            response: API response (if successful)
            error: Exception (if failed)
            duration_ms: Request duration in milliseconds
        """
        log_data = {
            "provider": self.__class__.__name__.replace("Client", ""),
            "operation": operation,
            "request_params": request_params,
            "duration_ms": duration_ms
        }
        
        if error:
            log_data["error"] = str(error)
            log_data["status"] = "error"
            logger.error(f"LLM API call failed: {log_data}")
        else:
            log_data["response"] = response
            log_data["status"] = "success"
            logger.info(f"LLM API call succeeded: {log_data}")
