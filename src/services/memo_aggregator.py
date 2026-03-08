"""Service for aggregating memos with content limit enforcement."""

from typing import List
from models.memo import Memo
from models.summary_models import AggregationResult


class MemoAggregator:
    """Aggregates memos for AI processing with content limit enforcement.
    
    This class handles the aggregation of multiple memos into a single context
    string while respecting token limits. When limits are exceeded, it prioritizes
    the most recently updated memos.
    """
    
    def __init__(self, max_tokens: int = 180000):
        """Initialize aggregator with token limit.
        
        Args:
            max_tokens: Maximum tokens allowed for AI processing (default: 180000)
        """
        self.max_tokens = max_tokens
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Uses approximation: 1 token ≈ 4 characters.
        This is a simplified estimation suitable for planning purposes.
        
        Args:
            text: Text to estimate token count for
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def aggregate_memos(self, memos: List[Memo]) -> AggregationResult:
        """Aggregate memos into a single context string.
        
        Prioritizes most recently updated memos when content exceeds token limits.
        Includes complete memos only (no partial memo content).
        
        Args:
            memos: List of Memo objects (should be sorted by updated_at descending)
            
        Returns:
            AggregationResult with aggregated text, included count, total count,
            and truncated flag
        """
        total_count = len(memos)
        
        if total_count == 0:
            return AggregationResult(
                aggregated_text="",
                included_count=0,
                total_count=0,
                truncated=False
            )
        
        # Sort memos by updated_at descending to prioritize recent memos
        sorted_memos = sorted(memos, key=lambda m: m.updated_at, reverse=True)
        
        aggregated_parts = []
        included_count = 0
        current_tokens = 0
        truncated = False
        
        for memo in sorted_memos:
            # Format memo content with title and content
            memo_text = f"Title: {memo.title}\nContent: {memo.content}\n\n"
            memo_tokens = self.estimate_tokens(memo_text)
            
            # Check if adding this memo would exceed the limit
            if current_tokens + memo_tokens > self.max_tokens:
                truncated = True
                break
            
            aggregated_parts.append(memo_text)
            included_count += 1
            current_tokens += memo_tokens
        
        aggregated_text = "".join(aggregated_parts)
        
        return AggregationResult(
            aggregated_text=aggregated_text,
            included_count=included_count,
            total_count=total_count,
            truncated=truncated
        )
