"""
Comprehensive unit tests for Memo Lambda handler (Task 4.18).

These tests cover all memo operations with specific examples, edge cases,
and error conditions using moto to mock DynamoDB.
"""
import json
import os
import pytest
import time
from datetime import datetime
from unittest.mock import Mock
from moto import mock_aws
import boto3

# Set environment variables before importing handler
os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'

from src.functions.memo.handler import lambda_handler


@pytest.fixture
def lambda_context():
    """Create a mock Lambda context."""
    context = Mock()
    context.request_id = 'test-request-id-123'
    context.function_name = 'test-memo-function'
    context.memory_limit_in_mb = 512
    context.invoked_function_arn = 'arn:aws:lambda:us-west-2:123456789012:function:test-memo-function'
    return context


@pytest.fixture
def dynamodb_table():
    """Create mock DynamoDB table for testing."""
    with mock_aws():
        # Reset the global repository before each test
        import src.functions.memo.handler as handler_module
        handler_module.repository = None
        
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
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
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table


class TestCreateMemoEdgeCases:
    """Test create_memo operation with edge cases."""
    
    def test_create_memo_with_minimum_title_length(self, lambda_context, dynamodb_table):
        """Test creating a memo with 1 character title (boundary value)."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'A',
                'content': 'Valid content'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['title'] == 'A'
        assert len(body['title']) == 1
    
    def test_create_memo_with_maximum_title_length(self, lambda_context, dynamodb_table):
        """Test creating a memo with 200 character title (boundary value)."""
        title = 'x' * 200
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': title,
                'content': 'Valid content'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['title'] == title
        assert len(body['title']) == 200
    
    def test_create_memo_with_minimum_content_length(self, lambda_context, dynamodb_table):
        """Test creating a memo with 1 character content (boundary value)."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Valid title',
                'content': 'C'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['content'] == 'C'
        assert len(body['content']) == 1
    
    def test_create_memo_with_large_content(self, lambda_context, dynamodb_table):
        """Test creating a memo with large content (approaching 50000 chars)."""
        content = 'x' * 49999
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Large content memo',
                'content': content
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert len(body['content']) == 49999
    
    def test_create_memo_with_unicode_characters(self, lambda_context, dynamodb_table):
        """Test creating a memo with Unicode characters."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Unicode テスト 🎉',
                'content': 'Content with émojis 😀 and spëcial çhars'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['title'] == 'Unicode テスト 🎉'
        assert '😀' in body['content']
    
    def test_create_memo_with_special_characters(self, lambda_context, dynamodb_table):
        """Test creating a memo with special characters."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Special <>&"\' chars',
                'content': 'Content with\nnewlines\tand\ttabs'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert '<>&' in body['title']
        assert '\n' in body['content']


class TestUpdateMemoEdgeCases:
    """Test update_memo operation with edge cases."""
    
    def test_update_memo_partial_title_only(self, lambda_context, dynamodb_table):
        """Test updating only the title field."""
        # Create memo
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Original Title',
                'content': 'Original Content'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        memo = json.loads(create_response['body'])
        
        # Update only title
        update_event = {
            'httpMethod': 'PUT',
            'path': f'/memos/{memo["id"]}',
            'pathParameters': {'id': memo['id']},
            'body': json.dumps({
                'title': 'Updated Title'
            })
        }
        
        response = lambda_handler(update_event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['title'] == 'Updated Title'
        assert body['content'] == 'Original Content'  # Unchanged
    
    def test_update_memo_partial_content_only(self, lambda_context, dynamodb_table):
        """Test updating only the content field."""
        # Create memo
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Original Title',
                'content': 'Original Content'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        memo = json.loads(create_response['body'])
        
        # Update only content
        update_event = {
            'httpMethod': 'PUT',
            'path': f'/memos/{memo["id"]}',
            'pathParameters': {'id': memo['id']},
            'body': json.dumps({
                'content': 'Updated Content'
            })
        }
        
        response = lambda_handler(update_event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['title'] == 'Original Title'  # Unchanged
        assert body['content'] == 'Updated Content'
    
    def test_update_memo_timestamp_changes(self, lambda_context, dynamodb_table):
        """Test that updating a memo changes the updated_at timestamp."""
        # Create memo
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Original',
                'content': 'Original content'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        memo = json.loads(create_response['body'])
        original_updated_at = memo['updated_at']
        
        # Wait a moment
        time.sleep(0.01)
        
        # Update memo
        update_event = {
            'httpMethod': 'PUT',
            'path': f'/memos/{memo["id"]}',
            'pathParameters': {'id': memo['id']},
            'body': json.dumps({
                'title': 'Updated'
            })
        }
        update_response = lambda_handler(update_event, lambda_context)
        updated_memo = json.loads(update_response['body'])
        
        assert updated_memo['updated_at'] > original_updated_at
        assert updated_memo['created_at'] == memo['created_at']  # Created timestamp unchanged


class TestListMemosEdgeCases:
    """Test list_memos operation with edge cases."""
    
    def test_list_memos_default_page_size(self, lambda_context, dynamodb_table):
        """Test that default page size is 20."""
        # Create 25 memos
        for i in range(25):
            create_event = {
                'httpMethod': 'POST',
                'path': '/memos',
                'body': json.dumps({
                    'title': f'Memo {i}',
                    'content': f'Content {i}'
                })
            }
            lambda_handler(create_event, lambda_context)
        
        # List without page_size parameter
        list_event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': None
        }
        
        response = lambda_handler(list_event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['memos']) == 20  # Default page size
        assert body['next_token'] is not None  # More results available
    
    def test_list_memos_max_page_size_enforcement(self, lambda_context, dynamodb_table):
        """Test that page size is capped at 100."""
        # Create 10 memos
        for i in range(10):
            create_event = {
                'httpMethod': 'POST',
                'path': '/memos',
                'body': json.dumps({
                    'title': f'Memo {i}',
                    'content': f'Content {i}'
                })
            }
            lambda_handler(create_event, lambda_context)
        
        # Request with page_size > 100
        list_event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': {'page_size': '150'}
        }
        
        response = lambda_handler(list_event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Should return all 10 memos (less than cap)
        assert len(body['memos']) == 10
    
    def test_list_memos_sorting_order(self, lambda_context, dynamodb_table):
        """Test that memos are sorted by updated_at descending."""
        # Create memos with delays
        memo_ids = []
        for i in range(5):
            create_event = {
                'httpMethod': 'POST',
                'path': '/memos',
                'body': json.dumps({
                    'title': f'Memo {i}',
                    'content': f'Content {i}'
                })
            }
            response = lambda_handler(create_event, lambda_context)
            memo = json.loads(response['body'])
            memo_ids.append(memo['id'])
            time.sleep(0.01)
        
        # List memos
        list_event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': None
        }
        
        response = lambda_handler(list_event, lambda_context)
        body = json.loads(response['body'])
        memos = body['memos']
        
        # Verify descending order
        for i in range(len(memos) - 1):
            current_time = datetime.fromisoformat(memos[i]['updated_at'])
            next_time = datetime.fromisoformat(memos[i + 1]['updated_at'])
            assert current_time >= next_time
    
    def test_list_memos_pagination_navigation(self, lambda_context, dynamodb_table):
        """Test pagination with next_token."""
        # Create 15 memos
        for i in range(15):
            create_event = {
                'httpMethod': 'POST',
                'path': '/memos',
                'body': json.dumps({
                    'title': f'Memo {i}',
                    'content': f'Content {i}'
                })
            }
            lambda_handler(create_event, lambda_context)
        
        # Get first page
        list_event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': {'page_size': '5'}
        }
        
        response = lambda_handler(list_event, lambda_context)
        body = json.loads(response['body'])
        
        assert len(body['memos']) == 5
        assert body['next_token'] is not None
        
        first_page_ids = {memo['id'] for memo in body['memos']}
        
        # Get second page
        list_event['queryStringParameters']['next_token'] = body['next_token']
        response = lambda_handler(list_event, lambda_context)
        body = json.loads(response['body'])
        
        assert len(body['memos']) == 5
        second_page_ids = {memo['id'] for memo in body['memos']}
        
        # Verify no overlap
        assert len(first_page_ids & second_page_ids) == 0


class TestErrorConditions:
    """Test error handling and edge cases."""
    
    def test_create_memo_empty_title(self, lambda_context, dynamodb_table):
        """Test that empty title is rejected."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': '',
                'content': 'Valid content'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
    
    def test_create_memo_empty_content(self, lambda_context, dynamodb_table):
        """Test that empty content is rejected."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Valid title',
                'content': ''
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
    
    def test_create_memo_title_exceeds_max_length(self, lambda_context, dynamodb_table):
        """Test that title over 200 characters is rejected."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'x' * 201,
                'content': 'Valid content'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
        assert 'title' in body['error']['message'].lower()
    
    def test_create_memo_content_exceeds_max_length(self, lambda_context, dynamodb_table):
        """Test that content over 50000 characters is rejected."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Valid title',
                'content': 'x' * 50001
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
        assert 'content' in body['error']['message'].lower()
    
    def test_get_memo_nonexistent_id(self, lambda_context, dynamodb_table):
        """Test that getting a non-existent memo returns 404."""
        event = {
            'httpMethod': 'GET',
            'path': '/memos/nonexistent-id-12345',
            'pathParameters': {'id': 'nonexistent-id-12345'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NotFound'
        assert 'request_id' in body['error']
    
    def test_update_memo_nonexistent_id(self, lambda_context, dynamodb_table):
        """Test that updating a non-existent memo returns 404."""
        event = {
            'httpMethod': 'PUT',
            'path': '/memos/nonexistent-id-12345',
            'pathParameters': {'id': 'nonexistent-id-12345'},
            'body': json.dumps({
                'title': 'Updated Title'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NotFound'
    
    def test_delete_memo_nonexistent_id(self, lambda_context, dynamodb_table):
        """Test that deleting a non-existent memo returns 404."""
        event = {
            'httpMethod': 'DELETE',
            'path': '/memos/nonexistent-id-12345',
            'pathParameters': {'id': 'nonexistent-id-12345'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NotFound'
    
    def test_create_memo_malformed_json(self, lambda_context, dynamodb_table):
        """Test that malformed JSON returns 400."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': '{invalid json'
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
        assert 'json' in body['error']['message'].lower()
    
    def test_update_memo_no_fields_provided(self, lambda_context, dynamodb_table):
        """Test that update with no fields returns 400."""
        # Create memo
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Original',
                'content': 'Original content'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        memo = json.loads(create_response['body'])
        
        # Try to update with no fields
        update_event = {
            'httpMethod': 'PUT',
            'path': f'/memos/{memo["id"]}',
            'pathParameters': {'id': memo['id']},
            'body': json.dumps({})
        }
        
        response = lambda_handler(update_event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'


class TestCompleteWorkflows:
    """Test complete workflows and round-trip operations."""
    
    def test_create_read_round_trip(self, lambda_context, dynamodb_table):
        """Test creating and then reading a memo."""
        # Create
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Test Memo',
                'content': 'Test Content'
            })
        }
        
        create_response = lambda_handler(create_event, lambda_context)
        assert create_response['statusCode'] == 201
        created_memo = json.loads(create_response['body'])
        
        # Read
        get_event = {
            'httpMethod': 'GET',
            'path': f'/memos/{created_memo["id"]}',
            'pathParameters': {'id': created_memo['id']}
        }
        
        get_response = lambda_handler(get_event, lambda_context)
        assert get_response['statusCode'] == 200
        retrieved_memo = json.loads(get_response['body'])
        
        # Verify
        assert retrieved_memo['id'] == created_memo['id']
        assert retrieved_memo['title'] == 'Test Memo'
        assert retrieved_memo['content'] == 'Test Content'
        assert retrieved_memo['created_at'] == created_memo['created_at']
        assert retrieved_memo['updated_at'] == created_memo['updated_at']
    
    def test_create_update_read_workflow(self, lambda_context, dynamodb_table):
        """Test creating, updating, and reading a memo."""
        # Create
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Original',
                'content': 'Original Content'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        created_memo = json.loads(create_response['body'])
        
        time.sleep(0.01)
        
        # Update
        update_event = {
            'httpMethod': 'PUT',
            'path': f'/memos/{created_memo["id"]}',
            'pathParameters': {'id': created_memo['id']},
            'body': json.dumps({
                'title': 'Updated',
                'content': 'Updated Content'
            })
        }
        update_response = lambda_handler(update_event, lambda_context)
        assert update_response['statusCode'] == 200
        
        # Read
        get_event = {
            'httpMethod': 'GET',
            'path': f'/memos/{created_memo["id"]}',
            'pathParameters': {'id': created_memo['id']}
        }
        get_response = lambda_handler(get_event, lambda_context)
        retrieved_memo = json.loads(get_response['body'])
        
        # Verify
        assert retrieved_memo['title'] == 'Updated'
        assert retrieved_memo['content'] == 'Updated Content'
        assert retrieved_memo['updated_at'] > created_memo['updated_at']
        assert retrieved_memo['created_at'] == created_memo['created_at']
    
    def test_create_delete_read_workflow(self, lambda_context, dynamodb_table):
        """Test creating, deleting, and attempting to read a memo."""
        # Create
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'To Delete',
                'content': 'Will be deleted'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        created_memo = json.loads(create_response['body'])
        
        # Delete
        delete_event = {
            'httpMethod': 'DELETE',
            'path': f'/memos/{created_memo["id"]}',
            'pathParameters': {'id': created_memo['id']}
        }
        delete_response = lambda_handler(delete_event, lambda_context)
        assert delete_response['statusCode'] == 204
        assert delete_response['body'] == ''
        
        # Try to read
        get_event = {
            'httpMethod': 'GET',
            'path': f'/memos/{created_memo["id"]}',
            'pathParameters': {'id': created_memo['id']}
        }
        get_response = lambda_handler(get_event, lambda_context)
        assert get_response['statusCode'] == 404
    
    def test_multiple_memos_list_completeness(self, lambda_context, dynamodb_table):
        """Test that all created memos appear in list."""
        # Create multiple memos
        created_ids = set()
        for i in range(5):
            create_event = {
                'httpMethod': 'POST',
                'path': '/memos',
                'body': json.dumps({
                    'title': f'Memo {i}',
                    'content': f'Content {i}'
                })
            }
            response = lambda_handler(create_event, lambda_context)
            memo = json.loads(response['body'])
            created_ids.add(memo['id'])
        
        # List all
        list_event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': {'page_size': '100'}
        }
        list_response = lambda_handler(list_event, lambda_context)
        body = json.loads(list_response['body'])
        
        listed_ids = {memo['id'] for memo in body['memos']}
        
        # Verify all created memos are in the list
        assert created_ids.issubset(listed_ids)


class TestResponseStructure:
    """Test response structure and format."""
    
    def test_create_response_has_all_fields(self, lambda_context, dynamodb_table):
        """Test that create response contains all required fields."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Test',
                'content': 'Content'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        body = json.loads(response['body'])
        
        assert 'id' in body
        assert 'title' in body
        assert 'content' in body
        assert 'created_at' in body
        assert 'updated_at' in body
        
        # Verify types
        assert isinstance(body['id'], str)
        assert isinstance(body['title'], str)
        assert isinstance(body['content'], str)
        assert isinstance(body['created_at'], str)
        assert isinstance(body['updated_at'], str)
        
        # Verify timestamps are valid ISO 8601
        datetime.fromisoformat(body['created_at'])
        datetime.fromisoformat(body['updated_at'])
    
    def test_error_response_structure(self, lambda_context, dynamodb_table):
        """Test that error responses have correct structure."""
        event = {
            'httpMethod': 'GET',
            'path': '/memos/nonexistent',
            'pathParameters': {'id': 'nonexistent'}
        }
        
        response = lambda_handler(event, lambda_context)
        body = json.loads(response['body'])
        
        assert 'error' in body
        assert 'code' in body['error']
        assert 'message' in body['error']
        assert 'request_id' in body['error']
        
        assert isinstance(body['error']['code'], str)
        assert isinstance(body['error']['message'], str)
        assert isinstance(body['error']['request_id'], str)
    
    def test_cors_headers_present(self, lambda_context, dynamodb_table):
        """Test that CORS headers are present in responses."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Test',
                'content': 'Content'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert 'headers' in response
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
