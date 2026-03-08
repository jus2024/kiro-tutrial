"""Data models for all-memos summary feature."""

from dataclasses import dataclass


@dataclass
class AggregationResult:
    """Result of memo aggregation for AI processing."""
    
    aggregated_text: str
    """Combined memo content."""
    
    included_count: int
    """Number of memos included in aggregation."""
    
    total_count: int
    """Total number of memos available."""
    
    truncated: bool
    """Whether content was truncated due to token limits."""


@dataclass
class SummaryMetadata:
    """Metadata for summary response."""
    
    model_id: str
    """Bedrock model identifier."""
    
    processing_time_ms: int
    """Processing time in milliseconds."""
    
    memos_included: int
    """Number of memos included in summary."""
    
    memos_total: int
    """Total number of memos in system."""
    
    truncated: bool
    """Whether content was truncated due to limits."""
