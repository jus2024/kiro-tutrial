"""Unit tests for summary data models."""

import pytest
from src.models.summary_models import AggregationResult, SummaryMetadata


class TestAggregationResult:
    """Tests for AggregationResult dataclass."""
    
    def test_create_aggregation_result(self):
        """Test creating an AggregationResult with all fields."""
        result = AggregationResult(
            aggregated_text="Test content",
            included_count=5,
            total_count=10,
            truncated=True
        )
        
        assert result.aggregated_text == "Test content"
        assert result.included_count == 5
        assert result.total_count == 10
        assert result.truncated is True
    
    def test_aggregation_result_no_truncation(self):
        """Test AggregationResult when no truncation occurred."""
        result = AggregationResult(
            aggregated_text="All content included",
            included_count=10,
            total_count=10,
            truncated=False
        )
        
        assert result.included_count == result.total_count
        assert result.truncated is False


class TestSummaryMetadata:
    """Tests for SummaryMetadata dataclass."""
    
    def test_create_summary_metadata(self):
        """Test creating SummaryMetadata with all fields."""
        metadata = SummaryMetadata(
            model_id="us.anthropic.claude-sonnet-4-6",
            processing_time_ms=1500,
            memos_included=5,
            memos_total=10,
            truncated=True
        )
        
        assert metadata.model_id == "us.anthropic.claude-sonnet-4-6"
        assert metadata.processing_time_ms == 1500
        assert metadata.memos_included == 5
        assert metadata.memos_total == 10
        assert metadata.truncated is True
    
    def test_summary_metadata_no_truncation(self):
        """Test SummaryMetadata when all memos included."""
        metadata = SummaryMetadata(
            model_id="test-model",
            processing_time_ms=2000,
            memos_included=20,
            memos_total=20,
            truncated=False
        )
        
        assert metadata.memos_included == metadata.memos_total
        assert metadata.truncated is False
    
    def test_summary_metadata_zero_memos(self):
        """Test SummaryMetadata for empty memo collection."""
        metadata = SummaryMetadata(
            model_id="test-model",
            processing_time_ms=100,
            memos_included=0,
            memos_total=0,
            truncated=False
        )
        
        assert metadata.memos_included == 0
        assert metadata.memos_total == 0
        assert metadata.truncated is False
