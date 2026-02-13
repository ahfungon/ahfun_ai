"""Authentication utility functions."""
import bcrypt


def hash_token(token: str) -> str:
    """
    Hash a token using bcrypt.
    
    Args:
        token: Plain text token to hash
        
    Returns:
        str: Hashed token (bcrypt hash as string)
    """
    token_bytes = token.encode('utf-8')
    hashed = bcrypt.hashpw(token_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_token(token: str, hashed_token: str) -> bool:
    """
    Verify a token against its hash.
    
    Args:
        token: Plain text token to verify
        hashed_token: Hashed token to compare against
        
    Returns:
        bool: True if token matches, False otherwise
    """
    try:
        token_bytes = token.encode('utf-8')
        hash_bytes = hashed_token.encode('utf-8')
        return bcrypt.checkpw(token_bytes, hash_bytes)
    except (ValueError, AttributeError):
        return False
