"""
Unit tests for Memo data model.

Tests boundary values, special characters, and validation error messages.
"""

import pytest
from datetime import datetime
from src.models import Memo, ValidationError, validate_title, validate_content


class TestTitleValidation:
    """Test title validation function."""
    
    def test_valid_title_min_length(self):
        """Test title with minimum valid length (1 character)."""
        validate_title("A")  # Should not raise
    
    def test_valid_title_max_length(self):
        """Test title with maximum valid length (200 characters)."""
        validate_title("x" * 200)  # Should not raise
    
    def test_valid_title_normal_length(self):
        """Test title with normal length."""
        validate_title("This is a normal title")  # Should not raise
    
    def test_invalid_title_empty(self):
        """Test that empty title raises ValidationError."""
        with pytest.raises(ValidationError, match="at least 1 character"):
            validate_title("")
    
    def test_invalid_title_too_long(self):
        """Test that title over 200 characters raises ValidationError."""
        with pytest.raises(ValidationError, match="not exceed 200 characters"):
            validate_title("x" * 201)
    
    def test_invalid_title_not_string(self):
        """Test that non-string title raises ValidationError."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate_title(123)


class TestContentValidation:
    """Test content validation function."""
    
    def test_valid_content_min_length(self):
        """Test content with minimum valid length (1 character)."""
        validate_content("A")  # Should not raise
    
    def test_valid_content_max_length(self):
        """Test content with maximum valid length (50000 characters)."""
        validate_content("x" * 50000)  # Should not raise
    
    def test_valid_content_normal_length(self):
        """Test content with normal length."""
        validate_content("This is normal content with multiple sentences.")  # Should not raise
    
    def test_invalid_content_empty(self):
        """Test that empty content raises ValidationError."""
        with pytest.raises(ValidationError, match="at least 1 character"):
            validate_content("")
    
    def test_invalid_content_too_long(self):
        """Test that content over 50000 characters raises ValidationError."""
        with pytest.raises(ValidationError, match="not exceed 50000 characters"):
            validate_content("x" * 50001)
    
    def test_invalid_content_not_string(self):
        """Test that non-string content raises ValidationError."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate_content(None)


class TestMemoModel:
    """Test Memo dataclass."""
    
    def test_create_valid_memo(self):
        """Test creating a memo with valid data."""
        now = datetime.utcnow()
        memo = Memo(
            id="test-id-123",
            title="Test Title",
            content="Test content",
            created_at=now,
            updated_at=now
        )
        
        assert memo.id == "test-id-123"
        assert memo.title == "Test Title"
        assert memo.content == "Test content"
        assert memo.created_at == now
        assert memo.updated_at == now
    
    def test_create_memo_with_special_characters(self):
        """Test creating a memo with special characters and Unicode."""
        now = datetime.utcnow()
        memo = Memo(
            id="test-id-456",
            title="タイトル with émojis 🎉",
            content="Content with special chars: @#$%^&*() and 日本語",
            created_at=now,
            updated_at=now
        )
        
        assert "タイトル" in memo.title
        assert "🎉" in memo.title
        assert "日本語" in memo.content
    
    def test_create_memo_with_boundary_values(self):
        """Test creating memo with boundary values."""
        now = datetime.utcnow()
        
        # Minimum lengths
        memo_min = Memo(
            id="min-id",
            title="A",
            content="B",
            created_at=now,
            updated_at=now
        )
        assert len(memo_min.title) == 1
        assert len(memo_min.content) == 1
        
        # Maximum lengths
        memo_max = Memo(
            id="max-id",
            title="x" * 200,
            content="y" * 50000,
            created_at=now,
            updated_at=now
        )
        assert len(memo_max.title) == 200
        assert len(memo_max.content) == 50000
    
    def test_create_memo_invalid_title_raises_error(self):
        """Test that creating memo with invalid title raises ValidationError."""
        now = datetime.utcnow()
        
        with pytest.raises(ValidationError):
            Memo(
                id="test-id",
                title="",  # Empty title
                content="Valid content",
                created_at=now,
                updated_at=now
            )
    
    def test_create_memo_invalid_content_raises_error(self):
        """Test that creating memo with invalid content raises ValidationError."""
        now = datetime.utcnow()
        
        with pytest.raises(ValidationError):
            Memo(
                id="test-id",
                title="Valid title",
                content="",  # Empty content
                created_at=now,
                updated_at=now
            )
    
    def test_to_dict(self):
        """Test converting memo to dictionary for API response."""
        now = datetime(2024, 1, 15, 10, 30, 0)
        memo = Memo(
            id="dict-test-id",
            title="Dict Test",
            content="Testing to_dict method",
            created_at=now,
            updated_at=now
        )
        
        result = memo.to_dict()
        
        assert result['id'] == "dict-test-id"
        assert result['title'] == "Dict Test"
        assert result['content'] == "Testing to_dict method"
        assert result['created_at'] == "2024-01-15T10:30:00"
        assert result['updated_at'] == "2024-01-15T10:30:00"
        assert len(result) == 5  # Exactly 5 fields
    
    def test_to_dynamodb_item(self):
        """Test converting memo to DynamoDB item format."""
        now = datetime(2024, 1, 15, 10, 30, 0)
        memo = Memo(
            id="ddb-test-id",
            title="DDB Test",
            content="Testing to_dynamodb_item method",
            created_at=now,
            updated_at=now
        )
        
        result = memo.to_dynamodb_item()
        
        assert result['PK'] == "MEMO#ddb-test-id"
        assert result['id'] == "ddb-test-id"
        assert result['title'] == "DDB Test"
        assert result['content'] == "Testing to_dynamodb_item method"
        assert result['created_at'] == "2024-01-15T10:30:00"
        assert result['updated_at'] == "2024-01-15T10:30:00"
        assert result['entity_type'] == "MEMO"
        assert len(result) == 7  # Exactly 7 fields
