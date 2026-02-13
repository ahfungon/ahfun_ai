"""Custom exceptions for the Dual Agent Chat Platform."""


class AuthenticationError(Exception):
    """Exception raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)
