"""
Unit tests for Memo Lambda handler routing and operations.
"""
import json
import os
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3

# Set environment variable before importing handler
os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'  # Disable X-Ray for tests

from src.functions.memo.handler import (
    lambda_handler,
    create_memo,
    get_memo,
    list_memos,
    update_memo,
    delete_memo,
    error_response,
    success_response
)


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


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_error_response(self):
        """Test error response formatting."""
        response = error_response(400, "ValidationError", "Invalid input", "req-123")
        
        assert response['statusCode'] == 400
        assert response['headers']['Content-Type'] == 'application/json'
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
        assert body['error']['message'] == 'Invalid input'
        assert body['error']['request_id'] == 'req-123'
    
    def test_success_response(self):
        """Test success response formatting."""
        data = {'id': '123', 'title': 'Test'}
        response = success_response(200, data)
        
        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'application/json'
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body == data


class TestRouting:
    """Test Lambda handler routing logic."""
    
    def test_route_to_create_memo(self, lambda_context, dynamodb_table):
        """Test routing POST /memos to create_memo."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Test Memo',
                'content': 'Test content'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['title'] == 'Test Memo'
        assert body['content'] == 'Test content'
        assert 'id' in body
    
    def test_route_to_get_memo(self, lambda_context, dynamodb_table):
        """Test routing GET /memos/{id} to get_memo."""
        # First create a memo
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Test Memo',
                'content': 'Test content'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        memo = json.loads(create_response['body'])
        
        # Now get it
        get_event = {
            'httpMethod': 'GET',
            'path': f'/memos/{memo["id"]}',
            'pathParameters': {'id': memo['id']}
        }
        
        response = lambda_handler(get_event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['id'] == memo['id']
        assert body['title'] == 'Test Memo'
    
    def test_route_to_list_memos(self, lambda_context, dynamodb_table):
        """Test routing GET /memos to list_memos."""
        event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'memos' in body
        assert isinstance(body['memos'], list)
    
    def test_route_to_update_memo(self, lambda_context, dynamodb_table):
        """Test routing PUT /memos/{id} to update_memo."""
        # First create a memo
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Original Title',
                'content': 'Original content'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        memo = json.loads(create_response['body'])
        
        # Now update it
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
        assert body['content'] == 'Original content'  # Content unchanged
    
    def test_route_to_delete_memo(self, lambda_context, dynamodb_table):
        """Test routing DELETE /memos/{id} to delete_memo."""
        # First create a memo
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'To Delete',
                'content': 'Will be deleted'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        memo = json.loads(create_response['body'])
        
        # Now delete it
        delete_event = {
            'httpMethod': 'DELETE',
            'path': f'/memos/{memo["id"]}',
            'pathParameters': {'id': memo['id']}
        }
        
        response = lambda_handler(delete_event, lambda_context)
        
        assert response['statusCode'] == 204
        assert response['body'] == ''
    
    def test_unknown_route(self, lambda_context, dynamodb_table):
        """Test that unknown routes return 404."""
        event = {
            'httpMethod': 'PATCH',
            'path': '/unknown',
            'pathParameters': None
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NotFound'


class TestCreateMemo:
    """Test create_memo operation."""
    
    def test_create_memo_success(self, lambda_context, dynamodb_table):
        """Test creating a memo with valid data."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Test Memo',
                'content': 'This is test content'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['title'] == 'Test Memo'
        assert body['content'] == 'This is test content'
        assert 'id' in body
        assert 'created_at' in body
        assert 'updated_at' in body
    
    def test_create_memo_missing_title(self, lambda_context, dynamodb_table):
        """Test that missing title returns 400."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'content': 'Content without title'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
    
    def test_create_memo_title_too_long(self, lambda_context, dynamodb_table):
        """Test that titles over 200 characters are rejected."""
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
    
    def test_create_memo_invalid_json(self, lambda_context, dynamodb_table):
        """Test that invalid JSON returns 400."""
        event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': 'not valid json'
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'


class TestGetMemo:
    """Test get_memo operation."""
    
    def test_get_memo_success(self, lambda_context, dynamodb_table):
        """Test retrieving an existing memo."""
        # Create a memo first
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'Test Memo',
                'content': 'Test content'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        created_memo = json.loads(create_response['body'])
        
        # Now retrieve it
        get_event = {
            'httpMethod': 'GET',
            'path': f'/memos/{created_memo["id"]}',
            'pathParameters': {'id': created_memo['id']}
        }
        
        response = lambda_handler(get_event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['id'] == created_memo['id']
        assert body['title'] == 'Test Memo'
        assert body['content'] == 'Test content'
    
    def test_get_nonexistent_memo(self, lambda_context, dynamodb_table):
        """Test that getting a non-existent memo returns 404."""
        event = {
            'httpMethod': 'GET',
            'path': '/memos/nonexistent-id',
            'pathParameters': {'id': 'nonexistent-id'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NotFound'


class TestListMemos:
    """Test list_memos operation."""
    
    def test_list_memos_empty(self, lambda_context, dynamodb_table):
        """Test listing memos when none exist."""
        event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['memos'] == []
        assert body['next_token'] is None
    
    def test_list_memos_with_data(self, lambda_context, dynamodb_table):
        """Test listing memos with existing data."""
        # Create a few memos
        for i in range(3):
            create_event = {
                'httpMethod': 'POST',
                'path': '/memos',
                'body': json.dumps({
                    'title': f'Memo {i}',
                    'content': f'Content {i}'
                })
            }
            lambda_handler(create_event, lambda_context)
        
        # List them
        list_event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': None
        }
        
        response = lambda_handler(list_event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['memos']) == 3
    
    def test_list_memos_with_page_size(self, lambda_context, dynamodb_table):
        """Test listing memos with custom page size."""
        event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': {'page_size': '10'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'memos' in body


class TestUpdateMemo:
    """Test update_memo operation."""
    
    def test_update_memo_success(self, lambda_context, dynamodb_table):
        """Test updating a memo successfully."""
        # Create a memo
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
        
        # Update it
        update_event = {
            'httpMethod': 'PUT',
            'path': f'/memos/{memo["id"]}',
            'pathParameters': {'id': memo['id']},
            'body': json.dumps({
                'title': 'Updated',
                'content': 'Updated content'
            })
        }
        
        response = lambda_handler(update_event, lambda_context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['title'] == 'Updated'
        assert body['content'] == 'Updated content'
    
    def test_update_nonexistent_memo(self, lambda_context, dynamodb_table):
        """Test updating a non-existent memo returns 404."""
        event = {
            'httpMethod': 'PUT',
            'path': '/memos/nonexistent-id',
            'pathParameters': {'id': 'nonexistent-id'},
            'body': json.dumps({
                'title': 'Updated'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NotFound'


class TestDeleteMemo:
    """Test delete_memo operation."""
    
    def test_delete_memo_success(self, lambda_context, dynamodb_table):
        """Test deleting a memo successfully."""
        # Create a memo
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': 'To Delete',
                'content': 'Will be deleted'
            })
        }
        create_response = lambda_handler(create_event, lambda_context)
        memo = json.loads(create_response['body'])
        
        # Delete it
        delete_event = {
            'httpMethod': 'DELETE',
            'path': f'/memos/{memo["id"]}',
            'pathParameters': {'id': memo['id']}
        }
        
        response = lambda_handler(delete_event, lambda_context)
        
        assert response['statusCode'] == 204
        assert response['body'] == ''
        
        # Verify it's gone
        get_event = {
            'httpMethod': 'GET',
            'path': f'/memos/{memo["id"]}',
            'pathParameters': {'id': memo['id']}
        }
        get_response = lambda_handler(get_event, lambda_context)
        assert get_response['statusCode'] == 404
    
    def test_delete_nonexistent_memo(self, lambda_context, dynamodb_table):
        """Test deleting a non-existent memo returns 404."""
        event = {
            'httpMethod': 'DELETE',
            'path': '/memos/nonexistent-id',
            'pathParameters': {'id': 'nonexistent-id'}
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error']['code'] == 'NotFound'
