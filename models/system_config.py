"""System configuration model for storing runtime settings."""
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text, Integer
from models.database import Base


class SystemConfig(Base):
    """
    System configuration model for storing runtime settings.
    
    This allows dynamic configuration without restarting the application.
    """
    __tablename__ = "system_configs"
    
    # Configuration key (unique identifier)
    key = Column(String(100), primary_key=True)
    
    # Configuration value (stored as string, parsed by application)
    value = Column(Text, nullable=False)
    
    # Configuration type (for UI rendering: text, number, textarea, select)
    config_type = Column(String(20), nullable=False, default="text")
    
    # Configuration category (for grouping in UI)
    category = Column(String(50), nullable=False, default="general")
    
    # Display name (for UI)
    display_name = Column(String(200), nullable=False)
    
    # Description (for UI tooltip)
    description = Column(Text, nullable=True)
    
    # Default value (for reset functionality)
    default_value = Column(Text, nullable=True)
    
    # Validation rules (JSON string, optional)
    validation = Column(Text, nullable=True)
    
    # Options for select type (JSON string, optional)
    options = Column(Text, nullable=True)
    
    # Display order (for UI sorting)
    display_order = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            "key": self.key,
            "value": self.value,
            "config_type": self.config_type,
            "category": self.category,
            "display_name": self.display_name,
            "description": self.description,
            "default_value": self.default_value,
            "validation": self.validation,
            "options": self.options,
            "display_order": self.display_order,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
