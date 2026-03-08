"""
Unit tests for AI Lambda function handler.

Tests cover AI question answering, Bedrock integration, error handling,
and retry logic.
"""

import os
# Disable X-Ray tracing for tests
os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from botocore.exceptions import ClientError


@pytest.fixture
def lambda_context():
    """Create mock Lambda context."""
    context = Mock()
    context.request_id = 'test-request-id-12345'
    context.function_name = 'test-ai-function'
    context.memory_limit_in_mb = 1024
    context.invoked_function_arn = 'arn:aws:lambda:us-west-2:123456789012:function:test-ai-function'
    return context


@pytest.fixture
def mock_dynamodb():
    """Create mock DynamoDB table."""
    from moto import mock_aws
    import boto3
    
    with mock_aws():
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


@pytest.fixture
def setup_env():
    """Set up environment variables for testing."""
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['BEDROCK_MODEL_ID'] = 'anthropic.claude-v2'
    os.environ['BEDROCK_REGION'] = 'us-west-2'
    os.environ['MAX_RETRIES'] = '3'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'ai-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    os.environ['POWERTOOLS_METRICS_NAMESPACE'] = 'test'
    yield
    # Cleanup
    for key in ['MEMO_TABLE_NAME', 'BEDROCK_MODEL_ID', 'BEDROCK_REGION', 'MAX_RETRIES']:
        if key in os.environ:
            del os.environ[key]


def test_validate_question_valid():
    """Test question validation with valid input."""
    from src.functions.ai.handler import validate_question
    
    # Valid questions
    validate_question("What is this about?")
    validate_question("x")  # 1 character
    validate_question("x" * 1000)  # 1000 characters


def test_validate_question_invalid():
    """Test question validation with invalid input."""
    from src.functions.ai.handler import validate_question
    from src.models import ValidationError
    
    # Empty string
    with pytest.raises(ValidationError, match="at least 1 character"):
        validate_question("")
    
    # Too long
    with pytest.raises(ValidationError, match="not exceed 1000 characters"):
        validate_question("x" * 1001)
    
    # Not a string
    with pytest.raises(ValidationError, match="must be a string"):
        validate_question(123)


def test_build_prompt():
    """Test prompt building for Bedrock."""
    from src.functions.ai.handler import build_prompt
    
    title = "Meeting Notes"
    content = "Discussed project timeline and deliverables."
    question = "What was discussed?"
    
    prompt = build_prompt(title, content, question)
    
    assert "Meeting Notes" in prompt
    assert "Discussed project timeline and deliverables." in prompt
    assert "What was discussed?" in prompt
    assert "helpful assistant" in prompt.lower()


def test_successful_ai_question(mock_dynamodb, setup_env, lambda_context):
    """Test successful AI question answering."""
    from src.functions.ai.handler import lambda_handler
    from src.repositories.memo_repository import MemoRepository
    from src.models.memo import Memo
    
    # Create a memo
    repository = MemoRepository()
    memo = Memo(
        id='test-memo-123',
        title='Project Plan',
        content='We will launch the product in Q2 2024.',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    repository.create_memo(memo)
    
    # Mock Bedrock response
    mock_bedrock_response = {
        'body': MagicMock()
    }
    mock_bedrock_response['body'].read.return_value = b'{"completion": "The product will launch in Q2 2024."}'
    
    with patch('boto3.client') as mock_boto_client:
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = mock_bedrock_response
        mock_boto_client.return_value = mock_bedrock
        
        event = {
            'httpMethod': 'POST',
            'path': '/memos/test-memo-123/ask',
            'pathParameters': {'id': 'test-memo-123'},
            'body': json.dumps({
                'question': 'When will the product launch?'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        assert 'answer' in body
        assert body['answer'] == 'The product will launch in Q2 2024.'
        
        assert 'metadata' in body
        assert body['metadata']['model_id'] == 'anthropic.claude-v2'
        assert body['metadata']['memo_id'] == 'test-memo-123'
        assert 'processing_time_ms' in body['metadata']
        assert body['metadata']['processing_time_ms'] >= 0


def test_question_validation_error(mock_dynamodb, setup_env, lambda_context):
    """Test AI question with invalid question length."""
    from src.functions.ai.handler import lambda_handler
    from src.repositories.memo_repository import MemoRepository
    from src.models.memo import Memo
    
    # Create a memo
    repository = MemoRepository()
    memo = Memo(
        id='test-memo-123',
        title='Test',
        content='Test content',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    repository.create_memo(memo)
    
    # Test with empty question
    event = {
        'httpMethod': 'POST',
        'path': '/memos/test-memo-123/ask',
        'pathParameters': {'id': 'test-memo-123'},
        'body': json.dumps({
            'question': ''
        })
    }
    
    response = lambda_handler(event, lambda_context)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'ValidationError'
    assert 'at least 1 character' in body['error']['message']
    
    # Test with too long question
    event['body'] = json.dumps({
        'question': 'x' * 1001
    })
    
    response = lambda_handler(event, lambda_context)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'ValidationError'
    assert 'not exceed 1000 characters' in body['error']['message']


def test_memo_not_found(mock_dynamodb, setup_env, lambda_context):
    """Test AI question with non-existent memo ID."""
    from src.functions.ai.handler import lambda_handler
    
    event = {
        'httpMethod': 'POST',
        'path': '/memos/nonexistent-id/ask',
        'pathParameters': {'id': 'nonexistent-id'},
        'body': json.dumps({
            'question': 'What is this about?'
        })
    }
    
    response = lambda_handler(event, lambda_context)
    
    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['error']['code'] == 'NotFound'
    assert 'not found' in body['error']['message'].lower()


def test_missing_memo_id(setup_env, lambda_context):
    """Test AI question without memo ID in path parameters."""
    from src.functions.ai.handler import lambda_handler
    
    event = {
        'httpMethod': 'POST',
        'path': '/memos//ask',
        'pathParameters': {},
        'body': json.dumps({
            'question': 'What is this about?'
        })
    }
    
    response = lambda_handler(event, lambda_context)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'ValidationError'
    assert 'Memo ID is required' in body['error']['message']


def test_invalid_json_body(setup_env, lambda_context):
    """Test AI question with malformed JSON."""
    from src.functions.ai.handler import lambda_handler
    
    event = {
        'httpMethod': 'POST',
        'path': '/memos/test-id/ask',
        'pathParameters': {'id': 'test-id'},
        'body': 'invalid json {'
    }
    
    response = lambda_handler(event, lambda_context)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error']['code'] == 'ValidationError'
    assert 'Invalid JSON' in body['error']['message']


def test_bedrock_retry_logic_success_after_retry(mock_dynamodb, setup_env, lambda_context):
    """Test Bedrock retry logic succeeds after initial failure."""
    from src.functions.ai.handler import lambda_handler
    from src.repositories.memo_repository import MemoRepository
    from src.models.memo import Memo
    
    # Create a memo
    repository = MemoRepository()
    memo = Memo(
        id='test-memo-123',
        title='Test',
        content='Test content',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    repository.create_memo(memo)
    
    # Mock Bedrock to fail once, then succeed
    mock_bedrock_response = {
        'body': MagicMock()
    }
    mock_bedrock_response['body'].read.return_value = b'{"completion": "Success after retry"}'
    
    with patch('boto3.client') as mock_boto_client:
        mock_bedrock = MagicMock()
        
        # First call fails with throttling, second succeeds
        mock_bedrock.invoke_model.side_effect = [
            ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                'InvokeModel'
            ),
            mock_bedrock_response
        ]
        
        mock_boto_client.return_value = mock_bedrock
        
        with patch('time.sleep'):  # Skip actual sleep in tests
            event = {
                'httpMethod': 'POST',
                'path': '/memos/test-memo-123/ask',
                'pathParameters': {'id': 'test-memo-123'},
                'body': json.dumps({
                    'question': 'Test question?'
                })
            }
            
            response = lambda_handler(event, lambda_context)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['answer'] == 'Success after retry'
            
            # Verify retry was attempted
            assert mock_bedrock.invoke_model.call_count == 2


def test_bedrock_retry_exhausted(mock_dynamodb, setup_env, lambda_context):
    """Test Bedrock retry logic when all retries are exhausted."""
    from src.functions.ai.handler import lambda_handler
    from src.repositories.memo_repository import MemoRepository
    from src.models.memo import Memo
    
    # Create a memo
    repository = MemoRepository()
    memo = Memo(
        id='test-memo-123',
        title='Test',
        content='Test content',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    repository.create_memo(memo)
    
    with patch('boto3.client') as mock_boto_client:
        mock_bedrock = MagicMock()
        
        # All calls fail with throttling
        mock_bedrock.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'InvokeModel'
        )
        
        mock_boto_client.return_value = mock_bedrock
        
        with patch('time.sleep'):  # Skip actual sleep in tests
            event = {
                'httpMethod': 'POST',
                'path': '/memos/test-memo-123/ask',
                'pathParameters': {'id': 'test-memo-123'},
                'body': json.dumps({
                    'question': 'Test question?'
                })
            }
            
            response = lambda_handler(event, lambda_context)
            
            assert response['statusCode'] == 503
            body = json.loads(response['body'])
            assert body['error']['code'] == 'ServiceUnavailable'
            assert 'temporarily unavailable' in body['error']['message'].lower()
            
            # Verify all retries were attempted (3 attempts)
            assert mock_bedrock.invoke_model.call_count == 3


def test_bedrock_non_retryable_error(mock_dynamodb, setup_env, lambda_context):
    """Test Bedrock with non-retryable error."""
    from src.functions.ai.handler import lambda_handler
    from src.repositories.memo_repository import MemoRepository
    from src.models.memo import Memo
    
    # Create a memo
    repository = MemoRepository()
    memo = Memo(
        id='test-memo-123',
        title='Test',
        content='Test content',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    repository.create_memo(memo)
    
    with patch('boto3.client') as mock_boto_client:
        mock_bedrock = MagicMock()
        
        # Non-retryable error (ValidationException)
        mock_bedrock.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid model ID'}},
            'InvokeModel'
        )
        
        mock_boto_client.return_value = mock_bedrock
        
        event = {
            'httpMethod': 'POST',
            'path': '/memos/test-memo-123/ask',
            'pathParameters': {'id': 'test-memo-123'},
            'body': json.dumps({
                'question': 'Test question?'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        # Should return 500 for unexpected errors
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error']['code'] == 'InternalError'
        
        # Should only attempt once (no retry for non-retryable errors)
        assert mock_bedrock.invoke_model.call_count == 1


def test_exponential_backoff_timing(mock_dynamodb, setup_env, lambda_context):
    """Test that exponential backoff uses correct timing (1s, 2s, 4s)."""
    from src.functions.ai.handler import invoke_bedrock_with_retry
    from botocore.exceptions import ClientError
    
    mock_bedrock = MagicMock()
    mock_bedrock.invoke_model.side_effect = ClientError(
        {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
        'InvokeModel'
    )
    
    with patch('time.sleep') as mock_sleep:
        with pytest.raises(Exception):  # Will raise ServiceUnavailableError
            invoke_bedrock_with_retry(
                bedrock_client=mock_bedrock,
                model_id='anthropic.claude-v2',
                memo_title='Test',
                memo_content='Test content',
                question='Test question?',
                max_retries=3
            )
        
        # Verify exponential backoff: 1s, 2s (only 2 sleeps for 3 attempts)
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1, 2]  # 2^0=1, 2^1=2


def test_error_response_format(setup_env):
    """Test error response formatting."""
    from src.functions.ai.handler import error_response
    
    response = error_response(
        status_code=400,
        error_code='ValidationError',
        message='Invalid input',
        request_id='test-123'
    )
    
    assert response['statusCode'] == 400
    assert response['headers']['Content-Type'] == 'application/json'
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    body = json.loads(response['body'])
    assert body['error']['code'] == 'ValidationError'
    assert body['error']['message'] == 'Invalid input'
    assert body['error']['request_id'] == 'test-123'


def test_cors_headers_in_response(mock_dynamodb, setup_env, lambda_context):
    """Test that CORS headers are included in responses."""
    from src.functions.ai.handler import lambda_handler
    from src.repositories.memo_repository import MemoRepository
    from src.models.memo import Memo
    
    # Create a memo
    repository = MemoRepository()
    memo = Memo(
        id='test-memo-123',
        title='Test',
        content='Test content',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    repository.create_memo(memo)
    
    # Mock Bedrock
    mock_bedrock_response = {
        'body': MagicMock()
    }
    mock_bedrock_response['body'].read.return_value = b'{"completion": "Test answer"}'
    
    with patch('boto3.client') as mock_boto_client:
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = mock_bedrock_response
        mock_boto_client.return_value = mock_bedrock
        
        event = {
            'httpMethod': 'POST',
            'path': '/memos/test-memo-123/ask',
            'pathParameters': {'id': 'test-memo-123'},
            'body': json.dumps({
                'question': 'Test?'
            })
        }
        
        response = lambda_handler(event, lambda_context)
        
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'
