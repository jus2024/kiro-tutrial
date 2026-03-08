"""
Simple unit tests for Lambda handler routing logic.
Tests the routing without DynamoDB dependencies.
"""
import json
import os
from unittest.mock import Mock, patch

# Set environment variables before importing
os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
os.environ['POWERTOOLS_METRICS_NAMESPACE'] = 'AIMemoryAPI'

from src.functions.memo.handler import lambda_handler


def test_routing_post_memos():
    """Test that POST /memos routes correctly."""
    event = {
        'httpMethod': 'POST',
        'path': '/memos',
        'body': json.dumps({'title': 'Test', 'content': 'Content'})
    }
    context = Mock()
    context.request_id = 'test-123'
    
    with patch('src.functions.memo.handler.get_repository') as mock_repo:
        # Mock the repository to return a memo
        mock_memo = Mock()
        mock_memo.to_dict.return_value = {
            'id': '123',
            'title': 'Test',
            'content': 'Content',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00'
        }
        mock_repo().create_memo.return_value = mock_memo
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 201
        assert mock_repo().create_memo.called


def test_routing_get_memo_by_id():
    """Test that GET /memos/{id} routes correctly."""
    event = {
        'httpMethod': 'GET',
        'path': '/memos/123',
        'pathParameters': {'id': '123'}
    }
    context = Mock()
    context.request_id = 'test-123'
    
    with patch('src.functions.memo.handler.get_repository') as mock_repo:
        mock_memo = Mock()
        mock_memo.to_dict.return_value = {
            'id': '123',
            'title': 'Test',
            'content': 'Content',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00'
        }
        mock_repo().get_memo.return_value = mock_memo
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        assert mock_repo().get_memo.called


def test_routing_list_memos():
    """Test that GET /memos routes correctly."""
    event = {
        'httpMethod': 'GET',
        'path': '/memos',
        'queryStringParameters': None
    }
    context = Mock()
    context.request_id = 'test-123'
    
    with patch('src.functions.memo.handler.get_repository') as mock_repo:
        mock_repo().list_memos.return_value = ([], None)
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        assert mock_repo().list_memos.called


def test_routing_update_memo():
    """Test that PUT /memos/{id} routes correctly."""
    event = {
        'httpMethod': 'PUT',
        'path': '/memos/123',
        'pathParameters': {'id': '123'},
        'body': json.dumps({'title': 'Updated'})
    }
    context = Mock()
    context.request_id = 'test-123'
    
    with patch('src.functions.memo.handler.get_repository') as mock_repo:
        mock_memo = Mock()
        mock_memo.to_dict.return_value = {
            'id': '123',
            'title': 'Updated',
            'content': 'Content',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:01'
        }
        mock_repo().update_memo.return_value = mock_memo
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        assert mock_repo().update_memo.called


def test_routing_delete_memo():
    """Test that DELETE /memos/{id} routes correctly."""
    event = {
        'httpMethod': 'DELETE',
        'path': '/memos/123',
        'pathParameters': {'id': '123'}
    }
    context = Mock()
    context.request_id = 'test-123'
    
    with patch('src.functions.memo.handler.get_repository') as mock_repo:
        mock_repo().delete_memo.return_value = None
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 204
        assert mock_repo().delete_memo.called


def test_routing_unknown_route():
    """Test that unknown routes return 404."""
    event = {
        'httpMethod': 'PATCH',
        'path': '/unknown',
        'pathParameters': None
    }
    context = Mock()
    context.request_id = 'test-123'
    
    response = lambda_handler(event, context)
    
    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['error']['code'] == 'NotFound'
