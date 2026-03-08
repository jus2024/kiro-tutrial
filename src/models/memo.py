"""
Memo data model with validation.

This module defines the Memo dataclass and validation functions for the AI要約API.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


class ValidationError(Exception):
    """Raised when validation fails for memo fields."""
    pass


def validate_title(title: str) -> None:
    """
    Validate memo title length.
    
    Args:
        title: The memo title to validate
        
    Raises:
        ValidationError: If title is not between 1 and 200 characters
    """
    if not isinstance(title, str):
        raise ValidationError("Title must be a string")
    
    if len(title) < 1:
        raise ValidationError("Title must be at least 1 character")
    
    if len(title) > 200:
        raise ValidationError("Title must not exceed 200 characters")


def validate_content(content: str) -> None:
    """
    Validate memo content length.
    
    Args:
        content: The memo content to validate
        
    Raises:
        ValidationError: If content is not between 1 and 50000 characters
    """
    if not isinstance(content, str):
        raise ValidationError("Content must be a string")
    
    if len(content) < 1:
        raise ValidationError("Content must be at least 1 character")
    
    if len(content) > 50000:
        raise ValidationError("Content must not exceed 50000 characters")


@dataclass
class Memo:
    """
    Memo data model.
    
    Attributes:
        id: UUID v4 string
        title: Memo title (1-200 characters)
        content: Memo content (1-50000 characters)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    
    def __post_init__(self):
        """Validate memo fields after initialization."""
        validate_title(self.title)
        validate_content(self.content)
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert memo to dictionary for API response.
        
        Returns:
            Dictionary with memo fields in API response format
        """
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def to_dynamodb_item(self) -> Dict[str, str]:
        """
        Convert memo to DynamoDB item format.
        
        Returns:
            Dictionary with DynamoDB item structure including PK and entity_type
        """
        return {
            'PK': f'MEMO#{self.id}',
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'entity_type': 'MEMO'
        }
