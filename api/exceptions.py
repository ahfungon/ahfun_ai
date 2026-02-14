"""Custom exceptions for the Dual Agent Chat Platform."""


class AuthenticationError(Exception):
    """Exception raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception raised when request validation fails."""
    
    def __init__(self, message: str = "Validation failed"):
        self.message = message
        super().__init__(self.message)


class NotFoundError(Exception):
    """Exception raised when a requested resource is not found."""
    
    def __init__(self, message: str = "Resource not found"):
        self.message = message
        super().__init__(self.message)


class LLMServiceError(Exception):
    """Exception raised when LLM service is unavailable or fails."""
    
    def __init__(self, message: str = "LLM service error"):
        self.message = message
        super().__init__(self.message)
