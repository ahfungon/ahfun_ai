"""Authentication middleware for the Dual Agent Chat Platform."""
import bcrypt
from fastapi import Request
from sqlalchemy.orm import Session

from api.exceptions import AuthenticationError
from models.database import get_db
from models.models import Agent


class AuthMiddleware:
    """
    Middleware for authenticating agents via HTTP headers.
    
    Extracts X-Agent-Id and X-Auth-Token from request headers,
    verifies the token hash against the database, and returns
    the authenticated Agent object.
    """
    
    @staticmethod
    def authenticate(request: Request, db: Session) -> Agent:
        """
        Authenticate an agent from request headers.
        
        Supports two authentication modes:
        1. X-Agent-Id + X-Auth-Token (original mode)
        2. X-Agent-Token only (new mode for self-registered agents)
        
        Args:
            request: FastAPI Request object containing headers
            db: Database session for querying agents
            
        Returns:
            Agent: The authenticated agent object
            
        Raises:
            AuthenticationError: If authentication fails for any reason
        """
        # Check for new single-token authentication mode
        agent_token = request.headers.get("X-Agent-Token")
        
        if agent_token:
            # New mode: authenticate using token only
            # Query all agents and check token hash
            agents = db.query(Agent).all()
            
            for agent in agents:
                try:
                    token_bytes = agent_token.encode('utf-8')
                    hash_bytes = agent.auth_token_hash.encode('utf-8')
                    
                    if bcrypt.checkpw(token_bytes, hash_bytes):
                        return agent
                except (ValueError, AttributeError):
                    continue
            
            raise AuthenticationError("Invalid authentication token")
        
        # Original mode: X-Agent-Id + X-Auth-Token
        agent_id = request.headers.get("X-Agent-Id")
        auth_token = request.headers.get("X-Auth-Token")
        
        # Check if headers are present
        if not agent_id:
            raise AuthenticationError("Missing X-Agent-Id or X-Agent-Token header")
        
        if not auth_token:
            raise AuthenticationError("Missing X-Auth-Token header")
        
        # Query agent from database
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            raise AuthenticationError(f"Agent with id '{agent_id}' not found")
        
        # Verify token hash using bcrypt
        try:
            # bcrypt.checkpw expects bytes
            token_bytes = auth_token.encode('utf-8')
            hash_bytes = agent.auth_token_hash.encode('utf-8')
            
            if not bcrypt.checkpw(token_bytes, hash_bytes):
                raise AuthenticationError("Invalid authentication token")
        except (ValueError, AttributeError) as e:
            raise AuthenticationError(f"Token verification failed: {str(e)}")
        
        return agent
