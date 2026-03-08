"""Test fixtures and utilities for all-memos summary tests."""

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from src.models.memo import Memo


def create_test_memo(
    title: str = "Test Memo",
    content: str = "Test content",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    memo_id: str | None = None
) -> Memo:
    """
    Create a test Memo object with default or custom values.
    
    Args:
        title: Memo title
        content: Memo content
        created_at: Creation timestamp (defaults to now)
        updated_at: Update timestamp (defaults to now)
        memo_id: Memo ID (defaults to random UUID)
        
    Returns:
        Memo object for testing
    """
    now = datetime.now(timezone.utc)
    return Memo(
        id=memo_id or str(uuid4()),
        title=title,
        content=content,
        created_at=created_at or now,
        updated_at=updated_at or now
    )


def create_test_memos(count: int, content_size: int = 100) -> List[Memo]:
    """
    Create a list of test memos with sequential timestamps.
    
    Args:
        count: Number of memos to create
        content_size: Size of content for each memo
        
    Returns:
        List of Memo objects sorted by updated_at descending
    """
    base_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    memos = []
    
    for i in range(count):
        # Create memos with incrementing timestamps
        timestamp = base_time.replace(hour=i % 24, minute=i % 60)
        content = f"Memo content {i}: " + "x" * content_size
        
        memo = create_test_memo(
            title=f"Memo {i}",
            content=content,
            created_at=timestamp,
            updated_at=timestamp,
            memo_id=str(uuid4())
        )
        memos.append(memo)
    
    # Sort by updated_at descending (most recent first)
    memos.sort(key=lambda m: m.updated_at, reverse=True)
    return memos


def create_japanese_test_memo() -> Memo:
    """
    Create a test memo with Japanese content for UTF-8 testing.
    
    Returns:
        Memo with Japanese title and content
    """
    return create_test_memo(
        title="日本語のメモ",
        content="これは日本語のテストコンテンツです。UTF-8エンコーディングをテストします。"
    )


class MockBedrockClient:
    """Mock AWS Bedrock client for testing."""
    
    def __init__(self, response_text: str = "Test summary", should_fail: bool = False):
        """
        Initialize mock Bedrock client.
        
        Args:
            response_text: Text to return in mock response
            should_fail: Whether to raise exceptions
        """
        self.response_text = response_text
        self.should_fail = should_fail
        self.invocation_count = 0
        self.last_request_body = None
    
    def invoke_model(self, **kwargs):
        """
        Mock invoke_model method.
        
        Returns:
            Mock response with body containing JSON
            
        Raises:
            Exception if should_fail is True
        """
        import json
        from io import BytesIO
        
        self.invocation_count += 1
        self.last_request_body = json.loads(kwargs.get('body', '{}'))
        
        if self.should_fail:
            from botocore.exceptions import ClientError
            raise ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                'InvokeModel'
            )
        
        response_body = {
            'content': [
                {
                    'type': 'text',
                    'text': self.response_text
                }
            ]
        }
        
        # Create a mock response object
        class MockResponse:
            def __init__(self, body_dict):
                self.body_dict = body_dict
            
            def read(self):
                import json
                return json.dumps(self.body_dict).encode('utf-8')
        
        return {
            'body': MockResponse(response_body)
        }


class MockDynamoDBClient:
    """Mock DynamoDB client for testing."""
    
    def __init__(self, memos: List[Memo] | None = None, should_fail: bool = False):
        """
        Initialize mock DynamoDB client.
        
        Args:
            memos: List of memos to return from queries
            should_fail: Whether to raise exceptions
        """
        self.memos = memos or []
        self.should_fail = should_fail
        self.query_count = 0
    
    def query(self, **kwargs):
        """
        Mock query method.
        
        Returns:
            Mock DynamoDB query response
            
        Raises:
            Exception if should_fail is True
        """
        self.query_count += 1
        
        if self.should_fail:
            from botocore.exceptions import ClientError
            raise ClientError(
                {'Error': {'Code': 'InternalServerError', 'Message': 'Service error'}},
                'Query'
            )
        
        # Convert memos to DynamoDB items
        items = []
        for memo in self.memos:
            items.append({
                'PK': {'S': f"MEMO#{memo.id}"},
                'id': {'S': memo.id},
                'title': {'S': memo.title},
                'content': {'S': memo.content},
                'created_at': {'S': memo.created_at.isoformat()},
                'updated_at': {'S': memo.updated_at.isoformat()},
                'entity_type': {'S': 'MEMO'}
            })
        
        return {
            'Items': items,
            'Count': len(items)
        }
