# LLM Client Wrappers Usage Guide

## Overview

The LLM client wrappers provide a robust interface for interacting with OpenClaw and DeepSeek APIs. They include:

- **Automatic retry logic** with exponential backoff
- **Timeout handling** for long-running requests
- **Rate limit detection** and retry
- **Comprehensive logging** of all requests and responses
- **Error handling** with custom exceptions

## Architecture

```
services/llm_clients/
├── __init__.py           # Package exports
├── base_client.py        # Base class with retry logic
├── openclaw_client.py    # OpenClaw client for dialogue generation
└── deepseek_client.py    # DeepSeek client for summary generation
```

## OpenClaw Client

### Purpose
Used for generating agent dialogues with **actual token counting** from the LLM response.

### Usage

```python
from services.llm_clients import OpenClawClient

# Initialize client
client = OpenClawClient(
    api_key="your-api-key",
    api_url="https://api.openclaw.example.com/v1",
    timeout=30,           # Request timeout in seconds
    max_retries=3,        # Maximum retry attempts
    retry_delays=[1, 2, 4]  # Retry delays in seconds
)

# Generate dialogue
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you?"}
]

result = client.generate_dialogue(
    messages=messages,
    temperature=0.7,
    max_tokens=1000  # Optional
)

# Result contains:
# - content: Generated text
# - actual_tokens: Actual token count from LLM
# - model: Model used
# - finish_reason: Completion reason
print(f"Generated: {result['content']}")
print(f"Tokens used: {result['actual_tokens']}")
```

### Key Features

1. **Actual Token Counting**: Returns the exact token count from the LLM API, ensuring accurate tracking for summary triggers.

2. **Retry Logic**: Automatically retries on failures with exponential backoff.

3. **Error Handling**: Raises specific exceptions:
   - `LLMClientError`: General API errors
   - `LLMTimeoutError`: Request timeout
   - `LLMRateLimitError`: Rate limit exceeded

4. **Logging**: All requests and responses are logged with timing information.

## DeepSeek Client

### Purpose
Used for generating conversation summaries with LLM suggestions and end scores.

### Usage

```python
from services.llm_clients import DeepSeekClient

# Initialize client
client = DeepSeekClient(
    api_key="your-api-key",
    api_url="https://api.deepseek.com/v1",
    timeout=30,
    max_retries=3,
    retry_delays=[1, 2, 4]
)

# Generate summary
prompt = """You are a conversation summarization assistant...
Historical Summary: ...
New Conversation: ...
"""

result = client.generate_summary(
    prompt=prompt,
    temperature=0.3,  # Lower temperature for focused output
    max_tokens=2000
)

# Result contains:
# - summary: Generated summary text
# - suggestion: LLM suggestion (continue/change_angle/suggest_end/force_end)
# - end_score: End score (0-100)
print(f"Summary: {result['summary']}")
print(f"Suggestion: {result['suggestion']}")
print(f"End score: {result['end_score']}")
```

### Key Features

1. **JSON Response Parsing**: Automatically parses JSON responses from the LLM.

2. **Validation**: Validates suggestion values and end_score ranges:
   - Invalid suggestions default to "continue"
   - Out-of-range end_scores are clamped to [0, 100]

3. **Retry Logic**: Same robust retry mechanism as OpenClaw client.

4. **Logging**: Comprehensive logging of all API interactions.

## Integration with SummaryService

The `SummaryService` uses the `DeepSeekClient` internally:

```python
from services.summary_service import SummaryService
from services.llm_clients import DeepSeekClient

# Create custom client (optional)
deepseek_client = DeepSeekClient(
    api_key="your-api-key",
    api_url="https://api.deepseek.com/v1"
)

# Initialize service with custom client
summary_service = SummaryService(
    db=db_session,
    deepseek_client=deepseek_client
)

# Or use default client from settings
summary_service = SummaryService(db=db_session)
```

## Configuration

LLM client settings are configured in `config/settings.py`:

```python
# OpenClaw Configuration
openclaw_api_key: str = ""
openclaw_api_url: str = "https://api.openclaw.example.com/v1"

# DeepSeek Configuration
deepseek_api_key: str = ""
deepseek_api_url: str = "https://api.deepseek.com/v1"
```

Set these via environment variables:

```bash
export OPENCLAW_API_KEY="your-openclaw-key"
export OPENCLAW_API_URL="https://api.openclaw.example.com/v1"
export DEEPSEEK_API_KEY="your-deepseek-key"
export DEEPSEEK_API_URL="https://api.deepseek.com/v1"
```

## Error Handling

### Exception Hierarchy

```
LLMClientError (base exception)
├── LLMTimeoutError (request timeout)
└── LLMRateLimitError (rate limit exceeded)
```

### Example Error Handling

```python
from services.llm_clients import (
    OpenClawClient,
    LLMClientError,
    LLMTimeoutError,
    LLMRateLimitError
)

client = OpenClawClient(api_key="...", api_url="...")

try:
    result = client.generate_dialogue(messages)
except LLMTimeoutError as e:
    print(f"Request timed out: {e}")
    # Handle timeout (e.g., retry later)
except LLMRateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Handle rate limit (e.g., wait and retry)
except LLMClientError as e:
    print(f"LLM API error: {e}")
    # Handle general error
```

## Retry Configuration

### Default Retry Behavior

- **Max retries**: 3 attempts
- **Retry delays**: [1, 2, 4] seconds (exponential backoff)
- **Timeout**: 30 seconds per request

### Custom Retry Configuration

```python
client = OpenClawClient(
    api_key="...",
    api_url="...",
    max_retries=5,           # More retries
    retry_delays=[2, 4, 8, 16, 32],  # Custom delays
    timeout=60               # Longer timeout
)
```

## Logging

All LLM API calls are logged with structured information:

```json
{
  "provider": "OpenClaw",
  "operation": "generate_dialogue",
  "request_params": {
    "messages": [...],
    "temperature": 0.7
  },
  "response": {
    "content": "...",
    "actual_tokens": 25
  },
  "duration_ms": 1234.5,
  "status": "success"
}
```

Failed requests include error details:

```json
{
  "provider": "DeepSeek",
  "operation": "generate_summary",
  "request_params": {...},
  "error": "Request timed out after 30s",
  "duration_ms": 30000,
  "status": "error"
}
```

## Testing

The LLM clients include comprehensive tests in `tests/test_llm_clients.py`:

```bash
# Run all LLM client tests
pytest tests/test_llm_clients.py -v

# Run specific test class
pytest tests/test_llm_clients.py::TestOpenClawClient -v
pytest tests/test_llm_clients.py::TestDeepSeekClient -v
```

### Mocking in Tests

```python
from unittest.mock import Mock, patch

@patch('services.llm_clients.openclaw_client.requests.post')
def test_my_function(mock_post):
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {"content": "Test response"},
            "finish_reason": "stop"
        }],
        "usage": {"total_tokens": 10}
    }
    mock_post.return_value = mock_response
    
    # Test your code
    client = OpenClawClient(api_key="test", api_url="https://test.com")
    result = client.generate_dialogue([{"role": "user", "content": "test"}])
    
    assert result["content"] == "Test response"
    assert result["actual_tokens"] == 10
```

## Best Practices

1. **Use Environment Variables**: Never hardcode API keys in code.

2. **Handle Errors Gracefully**: Always catch and handle LLM client exceptions.

3. **Monitor Logs**: Review LLM API logs regularly to identify issues.

4. **Configure Timeouts**: Adjust timeout values based on your use case.

5. **Test with Mocks**: Use mocked responses in tests to avoid actual API calls.

6. **Rate Limiting**: Implement application-level rate limiting if needed.

7. **Cost Monitoring**: Track token usage from OpenClaw responses to monitor costs.

## Troubleshooting

### Issue: API Key Not Configured

**Error**: `LLMClientError: OpenClaw API key not configured`

**Solution**: Set the API key in environment variables or `.env` file.

### Issue: Request Timeout

**Error**: `LLMTimeoutError: OpenClaw API request timed out after 30s`

**Solution**: 
- Increase timeout value
- Check network connectivity
- Verify API endpoint is responsive

### Issue: Rate Limit Exceeded

**Error**: `LLMRateLimitError: DeepSeek API rate limit exceeded`

**Solution**:
- Wait before retrying
- Implement exponential backoff
- Contact API provider to increase limits

### Issue: Invalid JSON Response

**Error**: `LLMClientError: Failed to parse JSON response`

**Solution**:
- Check API response format
- Verify prompt includes JSON format instructions
- Review API documentation for response format

## Future Enhancements

Potential improvements for the LLM clients:

1. **Async Support**: Add async versions of API calls for better concurrency.

2. **Caching**: Implement response caching to reduce API calls.

3. **Metrics**: Add Prometheus metrics for monitoring.

4. **Circuit Breaker**: Implement circuit breaker pattern for failing APIs.

5. **Streaming**: Support streaming responses for long-running requests.

6. **Batch Processing**: Add batch API support for multiple requests.
