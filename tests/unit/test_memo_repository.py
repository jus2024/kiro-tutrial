"""
Unit tests for MemoRepository using moto to mock DynamoDB.

Tests all CRUD operations, pagination, and error scenarios.
"""

import os
import pytest
import base64
import json
from datetime import datetime
from moto import mock_aws
import boto3

from src.repositories.memo_repository import MemoRepository, MemoNotFoundError
from src.models.memo import Memo


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        # Set up DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create table with GSI
        table = dynamodb.create_table(
            TableName='test-memo-table',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'entity_type', 'AttributeType': 'S'},
                {'AttributeName': 'updated_at', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UpdatedAtIndex',
                    'KeySchema': [
                        {'AttributeName': 'entity_type', 'KeyType': 'HASH'},
                        {'AttributeName': 'updated_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Set environment variable
        os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
        
        yield table


@pytest.fixture
def repository(dynamodb_table):
    """Create a MemoRepository instance with mocked DynamoDB."""
    return MemoRepository(table_name='test-memo-table')


@pytest.fixture
def sample_memo():
    """Create a sample memo for testing."""
    return Memo(
        id='test-memo-123',
        title='Test Memo',
        content='This is test content',
        created_at=datetime(2024, 1, 15, 10, 0, 0),
        updated_at=datetime(2024, 1, 15, 10, 0, 0)
    )


class TestMemoRepositoryInit:
    """Test repository initialization."""
    
    def test_init_with_table_name(self):
        """Test initializing repository with explicit table name."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            dynamodb.create_table(
                TableName='custom-table',
                KeySchema=[{'AttributeName': 'PK', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'PK', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST'
            )
            
            repo = MemoRepository(table_name='custom-table')
            assert repo.table_name == 'custom-table'
    
    def test_init_with_env_variable(self, dynamodb_table):
        """Test initializing repository with environment variable."""
        os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
        repo = MemoRepository()
        assert repo.table_name == 'test-memo-table'
    
    def test_init_without_table_name_raises_error(self):
        """Test that initializing without table name raises ValueError."""
        # Clear environment variable
        if 'MEMO_TABLE_NAME' in os.environ:
            del os.environ['MEMO_TABLE_NAME']
        
        with pytest.raises(ValueError, match="MEMO_TABLE_NAME environment variable not set"):
            MemoRepository()


class TestCreateMemo:
    """Test create_memo operation."""
    
    def test_create_memo_success(self, repository, sample_memo):
        """Test successfully creating a memo."""
        result = repository.create_memo(sample_memo)
        
        assert result.id == sample_memo.id
        assert result.title == sample_memo.title
        assert result.content == sample_memo.content
        assert result.created_at == sample_memo.created_at
        assert result.updated_at == sample_memo.updated_at
    
    def test_create_memo_persists_to_dynamodb(self, repository, sample_memo):
        """Test that created memo is persisted to DynamoDB."""
        repository.create_memo(sample_memo)
        
        # Verify it was saved by retrieving it
        retrieved = repository.get_memo(sample_memo.id)
        assert retrieved.id == sample_memo.id
        assert retrieved.title == sample_memo.title
        assert retrieved.content == sample_memo.content
    
    def test_create_memo_with_special_characters(self, repository):
        """Test creating memo with special characters and Unicode."""
        memo = Memo(
            id='special-123',
            title='タイトル with émojis 🎉',
            content='Content with special chars: @#$%^&*() and 日本語',
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        
        result = repository.create_memo(memo)
        
        assert result.title == 'タイトル with émojis 🎉'
        assert result.content == 'Content with special chars: @#$%^&*() and 日本語'
    
    def test_create_memo_with_boundary_values(self, repository):
        """Test creating memo with minimum and maximum field lengths."""
        memo = Memo(
            id='boundary-123',
            title='A' * 200,  # Max title length
            content='B' * 50000,  # Max content length
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        
        result = repository.create_memo(memo)
        
        assert len(result.title) == 200
        assert len(result.content) == 50000


class TestGetMemo:
    """Test get_memo operation."""
    
    def test_get_memo_success(self, repository, sample_memo):
        """Test successfully retrieving an existing memo."""
        repository.create_memo(sample_memo)
        
        result = repository.get_memo(sample_memo.id)
        
        assert result.id == sample_memo.id
        assert result.title == sample_memo.title
        assert result.content == sample_memo.content
        assert result.created_at == sample_memo.created_at
        assert result.updated_at == sample_memo.updated_at
    
    def test_get_memo_not_found(self, repository):
        """Test retrieving non-existent memo raises MemoNotFoundError."""
        with pytest.raises(MemoNotFoundError) as exc_info:
            repository.get_memo('non-existent-id')
        
        assert exc_info.value.memo_id == 'non-existent-id'
        assert 'Memo not found: non-existent-id' in str(exc_info.value)
    
    def test_get_memo_with_special_characters(self, repository):
        """Test retrieving memo with special characters."""
        memo = Memo(
            id='special-456',
            title='Special タイトル 🎉',
            content='Special content 日本語',
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        repository.create_memo(memo)
        
        result = repository.get_memo('special-456')
        
        assert result.title == 'Special タイトル 🎉'
        assert result.content == 'Special content 日本語'


class TestListMemos:
    """Test list_memos operation with pagination."""
    
    def test_list_memos_empty_table(self, repository):
        """Test listing memos from empty table returns empty list."""
        memos, next_token = repository.list_memos()
        
        assert memos == []
        assert next_token is None
    
    def test_list_memos_single_page(self, repository):
        """Test listing memos that fit in a single page."""
        # Create 5 memos
        for i in range(5):
            memo = Memo(
                id=f'memo-{i}',
                title=f'Memo {i}',
                content=f'Content {i}',
                created_at=datetime(2024, 1, 15, 10, i, 0),
                updated_at=datetime(2024, 1, 15, 10, i, 0)
            )
            repository.create_memo(memo)
        
        memos, next_token = repository.list_memos(page_size=10)
        
        assert len(memos) == 5
        assert next_token is None
    
    def test_list_memos_sorted_by_updated_at_desc(self, repository):
        """Test that memos are sorted by updated_at in descending order."""
        # Create memos with different timestamps
        memo1 = Memo(
            id='memo-1',
            title='First',
            content='Content 1',
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        memo2 = Memo(
            id='memo-2',
            title='Second',
            content='Content 2',
            created_at=datetime(2024, 1, 15, 11, 0, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0)
        )
        memo3 = Memo(
            id='memo-3',
            title='Third',
            content='Content 3',
            created_at=datetime(2024, 1, 15, 12, 0, 0),
            updated_at=datetime(2024, 1, 15, 12, 0, 0)
        )
        
        repository.create_memo(memo1)
        repository.create_memo(memo2)
        repository.create_memo(memo3)
        
        memos, _ = repository.list_memos()
        
        # Most recent first
        assert memos[0].id == 'memo-3'
        assert memos[1].id == 'memo-2'
        assert memos[2].id == 'memo-1'
    
    def test_list_memos_with_pagination(self, repository):
        """Test pagination with page_size smaller than total memos."""
        # Create 10 memos
        for i in range(10):
            memo = Memo(
                id=f'memo-{i:02d}',
                title=f'Memo {i}',
                content=f'Content {i}',
                created_at=datetime(2024, 1, 15, 10, i, 0),
                updated_at=datetime(2024, 1, 15, 10, i, 0)
            )
            repository.create_memo(memo)
        
        # First page
        memos_page1, next_token = repository.list_memos(page_size=3)
        
        assert len(memos_page1) == 3
        assert next_token is not None
        
        # Second page
        memos_page2, next_token2 = repository.list_memos(page_size=3, next_token=next_token)
        
        assert len(memos_page2) == 3
        assert next_token2 is not None
        
        # Verify no overlap
        page1_ids = {m.id for m in memos_page1}
        page2_ids = {m.id for m in memos_page2}
        assert len(page1_ids & page2_ids) == 0
    
    def test_list_memos_page_size_variations(self, repository):
        """Test different page sizes."""
        # Create 15 memos
        for i in range(15):
            memo = Memo(
                id=f'memo-{i:02d}',
                title=f'Memo {i}',
                content=f'Content {i}',
                created_at=datetime(2024, 1, 15, 10, i, 0),
                updated_at=datetime(2024, 1, 15, 10, i, 0)
            )
            repository.create_memo(memo)
        
        # Test page_size=5
        memos, next_token = repository.list_memos(page_size=5)
        assert len(memos) == 5
        assert next_token is not None
        
        # Test page_size=10
        memos, next_token = repository.list_memos(page_size=10)
        assert len(memos) == 10
        assert next_token is not None
        
        # Test page_size=20 (larger than total)
        memos, next_token = repository.list_memos(page_size=20)
        assert len(memos) == 15
        assert next_token is None
    
    def test_list_memos_max_page_size_capped_at_100(self, repository):
        """Test that page_size is capped at 100."""
        # Create 5 memos
        for i in range(5):
            memo = Memo(
                id=f'memo-{i}',
                title=f'Memo {i}',
                content=f'Content {i}',
                created_at=datetime(2024, 1, 15, 10, i, 0),
                updated_at=datetime(2024, 1, 15, 10, i, 0)
            )
            repository.create_memo(memo)
        
        # Request with page_size > 100
        memos, next_token = repository.list_memos(page_size=200)
        
        # Should return all 5 memos (capped at 100, but only 5 exist)
        assert len(memos) == 5
        assert next_token is None
    
    def test_list_memos_invalid_next_token(self, repository):
        """Test that invalid next_token is ignored and starts from beginning."""
        # Create 3 memos
        for i in range(3):
            memo = Memo(
                id=f'memo-{i}',
                title=f'Memo {i}',
                content=f'Content {i}',
                created_at=datetime(2024, 1, 15, 10, i, 0),
                updated_at=datetime(2024, 1, 15, 10, i, 0)
            )
            repository.create_memo(memo)
        
        # Use invalid token
        memos, next_token = repository.list_memos(next_token='invalid-token')
        
        # Should return results from beginning
        assert len(memos) == 3
        assert next_token is None
    
    def test_list_memos_default_page_size(self, repository):
        """Test that default page_size is 20."""
        # Create 25 memos
        for i in range(25):
            memo = Memo(
                id=f'memo-{i:02d}',
                title=f'Memo {i}',
                content=f'Content {i}',
                created_at=datetime(2024, 1, 15, 10, i, 0),
                updated_at=datetime(2024, 1, 15, 10, i, 0)
            )
            repository.create_memo(memo)
        
        # Call without page_size parameter
        memos, next_token = repository.list_memos()
        
        assert len(memos) == 20
        assert next_token is not None


class TestUpdateMemo:
    """Test update_memo operation."""
    
    def test_update_memo_title_only(self, repository, sample_memo):
        """Test updating only the title."""
        repository.create_memo(sample_memo)
        
        updated = repository.update_memo(
            memo_id=sample_memo.id,
            title='Updated Title'
        )
        
        assert updated.title == 'Updated Title'
        assert updated.content == sample_memo.content  # Unchanged
        assert updated.updated_at > sample_memo.updated_at
    
    def test_update_memo_content_only(self, repository, sample_memo):
        """Test updating only the content."""
        repository.create_memo(sample_memo)
        
        updated = repository.update_memo(
            memo_id=sample_memo.id,
            content='Updated content'
        )
        
        assert updated.title == sample_memo.title  # Unchanged
        assert updated.content == 'Updated content'
        assert updated.updated_at > sample_memo.updated_at
    
    def test_update_memo_both_fields(self, repository, sample_memo):
        """Test updating both title and content."""
        repository.create_memo(sample_memo)
        
        updated = repository.update_memo(
            memo_id=sample_memo.id,
            title='New Title',
            content='New content'
        )
        
        assert updated.title == 'New Title'
        assert updated.content == 'New content'
        assert updated.updated_at > sample_memo.updated_at
    
    def test_update_memo_with_custom_timestamp(self, repository, sample_memo):
        """Test updating memo with custom updated_at timestamp."""
        repository.create_memo(sample_memo)
        
        custom_time = datetime(2024, 2, 1, 15, 30, 0)
        updated = repository.update_memo(
            memo_id=sample_memo.id,
            title='Updated',
            updated_at=custom_time
        )
        
        assert updated.updated_at == custom_time
    
    def test_update_memo_not_found(self, repository):
        """Test updating non-existent memo raises MemoNotFoundError."""
        with pytest.raises(MemoNotFoundError) as exc_info:
            repository.update_memo(
                memo_id='non-existent-id',
                title='New Title'
            )
        
        assert exc_info.value.memo_id == 'non-existent-id'
    
    def test_update_memo_no_fields_provided(self, repository, sample_memo):
        """Test update with no fields returns existing memo."""
        repository.create_memo(sample_memo)
        
        # Update with no title or content
        updated = repository.update_memo(memo_id=sample_memo.id)
        
        # Should return the existing memo
        assert updated.id == sample_memo.id
        assert updated.title == sample_memo.title
        assert updated.content == sample_memo.content
    
    def test_update_memo_persists_changes(self, repository, sample_memo):
        """Test that updates are persisted to DynamoDB."""
        repository.create_memo(sample_memo)
        
        repository.update_memo(
            memo_id=sample_memo.id,
            title='Persisted Title'
        )
        
        # Retrieve and verify
        retrieved = repository.get_memo(sample_memo.id)
        assert retrieved.title == 'Persisted Title'
    
    def test_update_memo_with_special_characters(self, repository, sample_memo):
        """Test updating memo with special characters."""
        repository.create_memo(sample_memo)
        
        updated = repository.update_memo(
            memo_id=sample_memo.id,
            title='Updated タイトル 🎉',
            content='Updated 日本語 content'
        )
        
        assert updated.title == 'Updated タイトル 🎉'
        assert updated.content == 'Updated 日本語 content'


class TestDeleteMemo:
    """Test delete_memo operation."""
    
    def test_delete_memo_success(self, repository, sample_memo):
        """Test successfully deleting an existing memo."""
        repository.create_memo(sample_memo)
        
        # Delete should not raise
        repository.delete_memo(sample_memo.id)
        
        # Verify it's deleted
        with pytest.raises(MemoNotFoundError):
            repository.get_memo(sample_memo.id)
    
    def test_delete_memo_not_found(self, repository):
        """Test deleting non-existent memo raises MemoNotFoundError."""
        with pytest.raises(MemoNotFoundError) as exc_info:
            repository.delete_memo('non-existent-id')
        
        assert exc_info.value.memo_id == 'non-existent-id'
    
    def test_delete_memo_removes_from_list(self, repository):
        """Test that deleted memo is removed from list results."""
        # Create 3 memos
        memo1 = Memo(
            id='memo-1',
            title='Memo 1',
            content='Content 1',
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        memo2 = Memo(
            id='memo-2',
            title='Memo 2',
            content='Content 2',
            created_at=datetime(2024, 1, 15, 11, 0, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0)
        )
        memo3 = Memo(
            id='memo-3',
            title='Memo 3',
            content='Content 3',
            created_at=datetime(2024, 1, 15, 12, 0, 0),
            updated_at=datetime(2024, 1, 15, 12, 0, 0)
        )
        
        repository.create_memo(memo1)
        repository.create_memo(memo2)
        repository.create_memo(memo3)
        
        # Delete memo-2
        repository.delete_memo('memo-2')
        
        # List should only have 2 memos
        memos, _ = repository.list_memos()
        assert len(memos) == 2
        assert 'memo-2' not in [m.id for m in memos]
    
    def test_delete_memo_idempotency(self, repository, sample_memo):
        """Test that deleting same memo twice raises error on second attempt."""
        repository.create_memo(sample_memo)
        
        # First delete succeeds
        repository.delete_memo(sample_memo.id)
        
        # Second delete should raise MemoNotFoundError
        with pytest.raises(MemoNotFoundError):
            repository.delete_memo(sample_memo.id)


class TestItemToMemo:
    """Test _item_to_memo conversion method."""
    
    def test_item_to_memo_conversion(self, repository):
        """Test converting DynamoDB item to Memo object."""
        item = {
            'PK': 'MEMO#test-123',
            'id': 'test-123',
            'title': 'Test Title',
            'content': 'Test Content',
            'created_at': '2024-01-15T10:00:00',
            'updated_at': '2024-01-15T10:00:00',
            'entity_type': 'MEMO'
        }
        
        memo = repository._item_to_memo(item)
        
        assert memo.id == 'test-123'
        assert memo.title == 'Test Title'
        assert memo.content == 'Test Content'
        assert memo.created_at == datetime(2024, 1, 15, 10, 0, 0)
        assert memo.updated_at == datetime(2024, 1, 15, 10, 0, 0)
