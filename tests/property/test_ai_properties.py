"""
Property-based tests for AI operations using Hypothesis.

These tests verify universal properties for AI question answering functionality.
Each test runs at least 100 iterations with different generated values.
"""

import os
# Disable X-Ray tracing for tests
os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from src.functions.ai.handler import validate_question
from src.models import ValidationError


# Feature: ai-summary-api, Property 3: Question Validation
@settings(max_examples=100)
@given(question=st.text(min_size=0, max_size=1500))
def test_question_validation_property(question):
    """
    Property 3: Question Validation
    
    For any AI question request, if the question length is not between 1 and 1000 
    characters (inclusive), then the request SHALL be rejected with a 400 error, 
    and if the question length is within this range, the request SHALL be accepted.
    
    Validates: Requirements 6.2
    """
    if 1 <= len(question) <= 1000:
        # Question is valid - should not raise ValidationError
        validate_question(question)
    else:
        # Question is invalid - should raise ValidationError (equivalent to 400 error)
        with pytest.raises(ValidationError):
            validate_question(question)


# Feature: ai-summary-api, Property 4: Invalid Input Error Response
@settings(max_examples=100)
@given(
    question=st.one_of(
        st.text(min_size=0, max_size=0),  # Empty string
        st.text(min_size=1001, max_size=2000)  # Too long
    )
)
def test_invalid_input_error_response_property(question):
    """
    Property 4: Invalid Input Error Response
    
    For any invalid request (failing validation rules), the API SHALL return a 400 
    status code with a descriptive error message in the response body.
    
    Validates: Requirements 1.4
    """
    from src.functions.ai.handler import validate_question
    from src.models import ValidationError
    
    # Test validation directly (simpler than full Lambda invocation)
    with pytest.raises(ValidationError) as exc_info:
        validate_question(question)
    
    # Verify error message is descriptive
    error_message = str(exc_info.value)
    assert len(error_message) > 0
    assert isinstance(error_message, str)


# Feature: ai-summary-api, Property 15: AI Question Returns Answer with Metadata
def test_ai_answer_response_structure_property(mock_bedrock_and_dynamodb):
    """
    Property 15: AI Question Returns Answer with Metadata
    
    For any valid AI question request with an existing memo ID and valid question, 
    the API SHALL return a response containing an answer field (non-empty string) 
    and a metadata object with model_id, processing_time_ms, and memo_id fields.
    
    Validates: Requirements 6.1, 6.3, 6.4
    
    Note: This test uses a single example rather than property-based testing
    due to complexity of mocking Bedrock across multiple iterations.
    """
    import json
    import os
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['BEDROCK_MODEL_ID'] = 'anthropic.claude-v2'
    os.environ['BEDROCK_REGION'] = 'us-west-2'
    os.environ['MAX_RETRIES'] = '3'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'ai-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    os.environ['POWERTOOLS_METRICS_NAMESPACE'] = 'AIMemoryAPI'
    
    from src.functions.ai.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Create a memo
    from src.repositories.memo_repository import MemoRepository
    from src.models.memo import Memo
    from datetime import datetime
    
    repository = MemoRepository()
    memo = Memo(
        id='test-memo-id',
        title='Project Plan',
        content='We will launch the product in Q2 2024.',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    repository.create_memo(memo)
    
    # Ask AI question
    ask_event = {
        'httpMethod': 'POST',
        'path': '/memos/test-memo-id/ask',
        'pathParameters': {'id': 'test-memo-id'},
        'body': json.dumps({
            'question': 'When will the product launch?'
        })
    }
    
    ask_response = lambda_handler(ask_event, context)
    
    # Verify successful response
    assert ask_response['statusCode'] == 200
    
    response_body = json.loads(ask_response['body'])
    
    # Verify answer field exists and is non-empty string
    assert 'answer' in response_body
    assert isinstance(response_body['answer'], str)
    assert len(response_body['answer']) > 0
    
    # Verify metadata object exists with required fields
    assert 'metadata' in response_body
    metadata = response_body['metadata']
    
    assert 'model_id' in metadata
    assert isinstance(metadata['model_id'], str)
    assert len(metadata['model_id']) > 0
    
    assert 'processing_time_ms' in metadata
    assert isinstance(metadata['processing_time_ms'], int)
    assert metadata['processing_time_ms'] >= 0
    
    assert 'memo_id' in metadata
    assert isinstance(metadata['memo_id'], str)
    assert metadata['memo_id'] == 'test-memo-id'

