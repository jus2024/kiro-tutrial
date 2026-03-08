"""Unit tests for all-memos summary Lambda handler."""

import json
import os
from unittest.mock import MagicMock, patch
import pytest

# Set environment variables before importing handler
os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
os.environ['BEDROCK_MODEL_ID'] = 'us.anthropic.claude-sonnet-4-6'
os.environ['BEDROCK_REGION'] = 'us-west-2'
os.environ['MAX_RETRIES'] = '3'
os.environ['MAX_CONTENT_TOKENS'] = '180000'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['POWERTOOLS_SERVICE_NAME'] = 'ai-summary-api'
os.environ['POWERTOOLS_TRACE_DISABLED'] = '1'  # Disable X-Ray for tests
os.environ['POWERTOOLS_METRICS_NAMESPACE'] = 'AIMemoryAPI'

from src.functions.all_memos_summary.handler import (
    lambda_handler,
    validate_request,
    error_response
)
from src.models.memo import ValidationError
from tests.unit.test_all_memos_summary_fixtures import (
    create_test_memos,
    create_japanese_test_memo,
    MockBedrockClient,
    MockDynamoDBClient
)


class TestValidateRequest:
    """Test request validation function."""
    
    def test_validate_empty_body(self):
        """Test that empty body is accepted."""
        body = {}
        # Should not raise exception
        validate_request(body)
    
    def test_validate_non_dict_body(self):
        """Test that non-dict body raises ValidationError."""
        with pytest.raises(ValidationError, match="Request body must be a JSON object"):
            validate_request("not a dict")
    
    def test_validate_with_valid_filters(self):
        """Test that valid filters are accepted."""
        body = {
            'filters': {
                'date_from': '2024-01-01T00:00:00Z',
                'date_to': '2024-12-31T23:59:59Z'
            }
        }
        # Should not raise exception
        validate_request(body)
    
    def test_validate_with_invalid_filters_type(self):
        """Test that invalid filters type raises ValidationError."""
        body = {'filters': 'not a dict'}
        with pytest.raises(ValidationError, match="Filters must be an object"):
            validate_request(body)
    
    def test_validate_with_invalid_date_from_type(self):
        """Test that invalid date_from type raises ValidationError."""
        body = {'filters': {'date_from': 123}}
        with pytest.raises(ValidationError, match="date_from must be a string"):
            validate_request(body)


class TestErrorResponse:
    """Test error response function."""
    
    def test_error_response_without_request_id(self):
        """Test error response without request_id."""
        response = error_response(400, "ValidationError", "Invalid request")
        
        assert response['statusCode'] == 400
        assert response['headers']['Content-Type'] == 'application/json; charset=utf-8'
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
        assert body['error']['message'] == 'Invalid request'
        assert 'request_id' not in body['error']
    
    def test_error_response_with_request_id(self):
        """Test error response with request_id."""
        response = error_response(500, "InternalError", "Server error", "test-request-id")
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error']['request_id'] == 'test-request-id'
    
    def test_error_response_cors_headers(self):
        """Test that error response includes CORS headers."""
        response = error_response(400, "ValidationError", "Invalid request")
        
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert 'Access-Control-Allow-Methods' in response['headers']
        assert 'Access-Control-Allow-Headers' in response['headers']


class TestLambdaHandler:
    """Test Lambda handler function."""
    
    def create_mock_context(self, request_id: str = "test-request-id"):
        """Create a mock Lambda context."""
        context = MagicMock()
        context.aws_request_id = request_id
        context.function_name = "AllMemosSummaryFunction"
        context.memory_limit_in_mb = 1024
        context.invoked_function_arn = "arn:aws:lambda:us-west-2:123456789012:function:AllMemosSummaryFunction"
        return context
    
    @patch('src.repositories.memo_repository.boto3')
    @patch('src.services.bedrock_service.boto3')
    def test_handler_with_empty_body(self, mock_bedrock_boto3, mock_dynamodb_boto3):
        """Test handler accepts empty request body."""
        # Setup mocks
        test_memos = create_test_memos(count=5, content_size=100)
        
        # Mock DynamoDB
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [memo.to_dynamodb_item() for memo in test_memos],
            'Count': len(test_memos)
        }
        mock_dynamodb_resource = MagicMock()
        mock_dynamodb_resource.Table.return_value = mock_table
        mock_dynamodb_boto3.resource.return_value = mock_dynamodb_resource
        
        # Mock Bedrock
        mock_bedrock_client = MockBedrockClient(response_text="テスト要約")
        mock_bedrock_boto3.client.return_value = mock_bedrock_client
        
        event = {
            'body': '{}',
            'httpMethod': 'POST',
            'path': '/memos/summary'
        }
        context = self.create_mock_context()
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'application/json; charset=utf-8'
        
        body = json.loads(response['body'])
        assert 'summary' in body
        assert 'metadata' in body
    
    def test_handler_with_invalid_json(self):
        """Test handler rejects invalid JSON."""
        event = {
            'body': 'not valid json',
            'httpMethod': 'POST',
            'path': '/memos/summary'
        }
        context = self.create_mock_context()
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
        assert 'Invalid JSON' in body['error']['message']
    
    @patch('src.repositories.memo_repository.boto3')
    @patch('src.services.bedrock_service.boto3')
    def test_handler_with_missing_body(self, mock_bedrock_boto3, mock_dynamodb_boto3):
        """Test handler handles missing body (treats as empty)."""
        # Setup mocks
        test_memos = create_test_memos(count=3, content_size=50)
        
        # Mock DynamoDB
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [memo.to_dynamodb_item() for memo in test_memos],
            'Count': len(test_memos)
        }
        mock_dynamodb_resource = MagicMock()
        mock_dynamodb_resource.Table.return_value = mock_table
        mock_dynamodb_boto3.resource.return_value = mock_dynamodb_resource
        
        # Mock Bedrock
        mock_bedrock_client = MockBedrockClient(response_text="Summary text")
        mock_bedrock_boto3.client.return_value = mock_bedrock_client
        
        event = {
            'httpMethod': 'POST',
            'path': '/memos/summary'
        }
        context = self.create_mock_context()
        
        response = lambda_handler(event, context)
        
        # Should treat missing body as empty object and succeed
        assert response['statusCode'] == 200
    
    @patch('src.repositories.memo_repository.boto3')
    @patch('src.services.bedrock_service.boto3')
    def test_handler_response_structure(self, mock_bedrock_boto3, mock_dynamodb_boto3):
        """Test that handler returns correct response structure."""
        # Setup mocks
        test_memos = create_test_memos(count=10, content_size=200)
        
        # Mock DynamoDB
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [memo.to_dynamodb_item() for memo in test_memos],
            'Count': len(test_memos)
        }
        mock_dynamodb_resource = MagicMock()
        mock_dynamodb_resource.Table.return_value = mock_table
        mock_dynamodb_boto3.resource.return_value = mock_dynamodb_resource
        
        # Mock Bedrock
        mock_bedrock_client = MockBedrockClient(response_text="Comprehensive summary")
        mock_bedrock_boto3.client.return_value = mock_bedrock_client
        
        event = {
            'body': '{}',
            'httpMethod': 'POST',
            'path': '/memos/summary'
        }
        context = self.create_mock_context()
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        assert 'headers' in response
        assert 'body' in response
        
        # Verify CORS headers
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert 'Access-Control-Allow-Methods' in response['headers']
        
        # Verify response body structure
        body = json.loads(response['body'])
        assert 'summary' in body
        assert 'metadata' in body
        
        metadata = body['metadata']
        assert 'model_id' in metadata
        assert 'processing_time_ms' in metadata
        assert 'memos_included' in metadata
        assert 'memos_total' in metadata
        assert 'truncated' in metadata
    
    @patch('src.repositories.memo_repository.boto3')
    @patch('src.services.bedrock_service.boto3')
    def test_handler_utf8_encoding(self, mock_bedrock_boto3, mock_dynamodb_boto3):
        """Test that handler properly handles UTF-8 encoding."""
        # Setup mocks with Japanese content
        japanese_memo = create_japanese_test_memo()
        
        # Mock DynamoDB
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [japanese_memo.to_dynamodb_item()],
            'Count': 1
        }
        mock_dynamodb_resource = MagicMock()
        mock_dynamodb_resource.Table.return_value = mock_table
        mock_dynamodb_boto3.resource.return_value = mock_dynamodb_resource
        
        # Mock Bedrock with Japanese response
        mock_bedrock_client = MockBedrockClient(response_text="日本語の要約テキスト")
        mock_bedrock_boto3.client.return_value = mock_bedrock_client
        
        event = {
            'body': '{}',
            'httpMethod': 'POST',
            'path': '/memos/summary'
        }
        context = self.create_mock_context()
        
        response = lambda_handler(event, context)
        
        # Verify UTF-8 charset in Content-Type header
        assert 'charset=utf-8' in response['headers']['Content-Type']
        
        # Verify body can be decoded as UTF-8
        body_str = response['body']
        assert isinstance(body_str, str)
        
        # Verify JSON parsing works
        body = json.loads(body_str)
        assert body is not None
    
    def test_handler_with_invalid_filters(self):
        """Test handler rejects invalid filter format."""
        event = {
            'body': json.dumps({'filters': 'invalid'}),
            'httpMethod': 'POST',
            'path': '/memos/summary'
        }
        context = self.create_mock_context()
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['code'] == 'ValidationError'
        assert 'Filters must be an object' in body['error']['message']
    
    def test_handler_includes_request_id_in_error(self):
        """Test that error responses include request_id."""
        event = {
            'body': 'invalid json',
            'httpMethod': 'POST',
            'path': '/memos/summary'
        }
        context = self.create_mock_context(request_id="test-123")
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error']['request_id'] == 'test-123'
    
    def test_handler_catches_unexpected_exceptions(self):
        """Test that handler catches and handles unexpected exceptions."""
        event = {
            'body': '{}',
            'httpMethod': 'POST',
            'path': '/memos/summary'
        }
        context = self.create_mock_context()
        
        # Mock validate_request to raise unexpected exception
        with patch('src.functions.all_memos_summary.handler.validate_request') as mock_validate:
            mock_validate.side_effect = RuntimeError("Unexpected error")
            
            response = lambda_handler(event, context)
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert body['error']['code'] == 'InternalError'
            assert body['error']['message'] == 'An unexpected error occurred'
