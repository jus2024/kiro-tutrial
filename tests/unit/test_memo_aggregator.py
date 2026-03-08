"""Unit tests for MemoAggregator service."""

import pytest
from datetime import datetime, timezone
from src.services.memo_aggregator import MemoAggregator
from src.models.memo import Memo
from src.models.summary_models import AggregationResult


class TestMemoAggregator:
    """Test suite for MemoAggregator class."""
    
    def test_init_default_max_tokens(self):
        """Test initialization with default max_tokens."""
        aggregator = MemoAggregator()
        assert aggregator.max_tokens == 180000
    
    def test_init_custom_max_tokens(self):
        """Test initialization with custom max_tokens."""
        aggregator = MemoAggregator(max_tokens=100000)
        assert aggregator.max_tokens == 100000
    
    def test_estimate_tokens_empty_string(self):
        """Test token estimation for empty string."""
        aggregator = MemoAggregator()
        assert aggregator.estimate_tokens("") == 0
    
    def test_estimate_tokens_simple_text(self):
        """Test token estimation for simple text."""
        aggregator = MemoAggregator()
        # 1 token ≈ 4 characters
        text = "a" * 100  # 100 characters
        assert aggregator.estimate_tokens(text) == 25  # 100 // 4 = 25 tokens
    
    def test_estimate_tokens_japanese_text(self):
        """Test token estimation for Japanese text."""
        aggregator = MemoAggregator()
        text = "こんにちは世界"  # 7 characters
        assert aggregator.estimate_tokens(text) == 1  # 7 // 4 = 1 token
    
    def test_aggregate_memos_empty_list(self):
        """Test aggregation with empty memo list."""
        aggregator = MemoAggregator()
        result = aggregator.aggregate_memos([])
        
        assert isinstance(result, AggregationResult)
        assert result.aggregated_text == ""
        assert result.included_count == 0
        assert result.total_count == 0
        assert result.truncated is False
    
    def test_aggregate_memos_single_memo(self):
        """Test aggregation with single memo."""
        aggregator = MemoAggregator()
        memo = Memo(
            id="test-id-1",
            title="Test Title",
            content="Test content",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        result = aggregator.aggregate_memos([memo])
        
        assert isinstance(result, AggregationResult)
        assert "Title: Test Title" in result.aggregated_text
        assert "Content: Test content" in result.aggregated_text
        assert result.included_count == 1
        assert result.total_count == 1
        assert result.truncated is False
    
    def test_aggregate_memos_multiple_within_limit(self):
        """Test aggregation with multiple memos within token limit."""
        aggregator = MemoAggregator(max_tokens=1000)
        
        memos = [
            Memo(
                id=f"test-id-{i}",
                title=f"Title {i}",
                content=f"Content {i}",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        
        result = aggregator.aggregate_memos(memos)
        
        assert isinstance(result, AggregationResult)
        assert result.included_count == 3
        assert result.total_count == 3
        assert result.truncated is False
        assert "Title: Title 0" in result.aggregated_text
        assert "Title: Title 1" in result.aggregated_text
        assert "Title: Title 2" in result.aggregated_text
    
    def test_aggregate_memos_exceeding_limit(self):
        """Test aggregation when content exceeds token limit."""
        # Set a very small limit to force truncation
        aggregator = MemoAggregator(max_tokens=50)
        
        # Create memos with content that will exceed the limit
        memos = [
            Memo(
                id=f"test-id-{i}",
                title=f"Title {i}",
                content="x" * 100,  # Large content
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            for i in range(5)
        ]
        
        result = aggregator.aggregate_memos(memos)
        
        assert isinstance(result, AggregationResult)
        assert result.included_count < result.total_count
        assert result.total_count == 5
        assert result.truncated is True
    
    def test_aggregate_memos_prioritizes_recent(self):
        """Test that aggregation prioritizes most recently updated memos."""
        aggregator = MemoAggregator(max_tokens=100)
        
        # Create memos with different update times
        base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        memos = [
            Memo(
                id="old-memo",
                title="Old Memo",
                content="x" * 200,  # Large content to force truncation
                created_at=base_time,
                updated_at=base_time
            ),
            Memo(
                id="recent-memo",
                title="Recent Memo",
                content="x" * 200,
                created_at=base_time,
                updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        result = aggregator.aggregate_memos(memos)
        
        # Should include the recent memo and exclude the old one
        assert result.included_count == 1
        assert result.total_count == 2
        assert result.truncated is True
        assert "Recent Memo" in result.aggregated_text
        assert "Old Memo" not in result.aggregated_text
    
    def test_aggregate_memos_format(self):
        """Test that aggregated text has correct format."""
        aggregator = MemoAggregator()
        memo = Memo(
            id="test-id",
            title="Test Title",
            content="Test content",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        result = aggregator.aggregate_memos([memo])
        
        # Check format: "Title: {title}\nContent: {content}\n\n"
        expected_format = "Title: Test Title\nContent: Test content\n\n"
        assert result.aggregated_text == expected_format
    
    def test_aggregate_memos_japanese_content(self):
        """Test aggregation with Japanese content."""
        aggregator = MemoAggregator()
        memo = Memo(
            id="test-id",
            title="日本語タイトル",
            content="これは日本語のコンテンツです。",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        result = aggregator.aggregate_memos([memo])
        
        assert isinstance(result, AggregationResult)
        assert "Title: 日本語タイトル" in result.aggregated_text
        assert "Content: これは日本語のコンテンツです。" in result.aggregated_text
        assert result.included_count == 1
        assert result.total_count == 1
        assert result.truncated is False
