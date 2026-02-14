"""Structured logging configuration for the application."""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add extra fields from the record
        # These are fields added via logger.info(..., extra={...})
        extra_fields = {}
        for key, value in record.__dict__.items():
            # Skip standard logging fields
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
            ]:
                extra_fields[key] = value
        
        if extra_fields:
            log_data.update(extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structured JSON logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create JSON formatter
    json_formatter = JSONFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


def log_llm_call(
    logger: logging.Logger,
    provider: str,
    operation: str,
    request_params: Dict[str, Any],
    response: Dict[str, Any] = None,
    error: Exception = None,
    duration_ms: float = None
) -> None:
    """
    Log LLM API call with structured data.
    
    Args:
        logger: Logger instance
        provider: LLM provider name (e.g., "OpenClaw", "DeepSeek")
        operation: Operation name (e.g., "generate_dialogue", "generate_summary")
        request_params: Request parameters sent to LLM
        response: Response from LLM (if successful)
        error: Exception if call failed
        duration_ms: Call duration in milliseconds
    """
    log_data = {
        "event_type": "llm_call",
        "provider": provider,
        "operation": operation,
        "request_params": request_params,
        "duration_ms": duration_ms
    }
    
    if response:
        log_data["response"] = response
        log_data["status"] = "success"
        logger.info(
            f"LLM call to {provider}.{operation} succeeded",
            extra=log_data
        )
    elif error:
        log_data["status"] = "error"
        log_data["error"] = str(error)
        logger.error(
            f"LLM call to {provider}.{operation} failed: {error}",
            extra=log_data,
            exc_info=True
        )
    else:
        log_data["status"] = "initiated"
        logger.debug(
            f"LLM call to {provider}.{operation} initiated",
            extra=log_data
        )


def log_retry_attempt(
    logger: logging.Logger,
    job_id: str,
    topic_id: str,
    retry_count: int,
    max_retries: int,
    error: str,
    next_delay: int = None
) -> None:
    """
    Log retry attempt for failed task.
    
    Args:
        logger: Logger instance
        job_id: Summary job ID
        topic_id: Topic ID
        retry_count: Current retry count
        max_retries: Maximum retry count
        error: Error message from failed attempt
        next_delay: Delay before next retry in seconds
    """
    log_data = {
        "event_type": "retry_attempt",
        "job_id": job_id,
        "topic_id": topic_id,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "error": error
    }
    
    if next_delay is not None:
        log_data["next_delay_seconds"] = next_delay
        logger.warning(
            f"Retry attempt {retry_count}/{max_retries} for job {job_id}, "
            f"next retry in {next_delay}s",
            extra=log_data
        )
    else:
        logger.error(
            f"Final retry attempt {retry_count}/{max_retries} failed for job {job_id}",
            extra=log_data
        )


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: Dict[str, Any],
    message: str = None
) -> None:
    """
    Log error with full context and traceback.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context information
        message: Optional custom error message
    """
    log_data = {
        "event_type": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
        **context
    }
    
    error_msg = message or f"Error occurred: {error}"
    logger.error(error_msg, extra=log_data, exc_info=True)
