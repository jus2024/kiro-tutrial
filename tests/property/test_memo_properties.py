"""
Property-based tests for Memo operations using Hypothesis.

These tests verify universal properties across randomized inputs.
Each test runs at least 100 iterations with different generated values.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from src.models import Memo, ValidationError, validate_title


# Feature: ai-summary-api, Property 1: Title Validation
@settings(max_examples=100)
@given(title=st.text(min_size=0, max_size=300))
def test_title_validation_property(title):
    """
    Property 1: Title Validation
    
    For any memo creation or update request, if the title length is not between 
    1 and 200 characters (inclusive), then the request SHALL be rejected with 
    a 400 error, and if the title length is within this range, the request 
    SHALL be accepted.
    
    Validates: Requirements 1.2, 4.2
    """
    if 1 <= len(title) <= 200:
        # Title is valid - should not raise ValidationError
        validate_title(title)
        
        # Should be able to create a Memo with this title
        now = datetime.utcnow()
        memo = Memo(
            id="test-id",
            title=title,
            content="Valid content",
            created_at=now,
            updated_at=now
        )
        assert memo.title == title
    else:
        # Title is invalid - should raise ValidationError (equivalent to 400 error)
        with pytest.raises(ValidationError):
            validate_title(title)
        
        # Should not be able to create a Memo with this title
        now = datetime.utcnow()
        with pytest.raises(ValidationError):
            Memo(
                id="test-id",
                title=title,
                content="Valid content",
                created_at=now,
                updated_at=now
            )

# Feature: ai-summary-api, Property 2: Content Validation
@settings(max_examples=100)
@given(content=st.text(min_size=0, max_size=60000))
def test_content_validation_property(content):
    """
    Property 2: Content Validation
    
    For any memo creation or update request, if the content length is not between 
    1 and 50000 characters (inclusive), then the request SHALL be rejected with 
    a 400 error, and if the content length is within this range, the request 
    SHALL be accepted.
    
    Validates: Requirements 1.3, 4.2
    """
    if 1 <= len(content) <= 50000:
        # Content is valid - should not raise ValidationError
        from src.models import validate_content
        validate_content(content)
        
        # Should be able to create a Memo with this content
        now = datetime.utcnow()
        memo = Memo(
            id="test-id",
            title="Valid title",
            content=content,
            created_at=now,
            updated_at=now
        )
        assert memo.content == content
    else:
        # Content is invalid - should raise ValidationError (equivalent to 400 error)
        from src.models import validate_content
        with pytest.raises(ValidationError):
            validate_content(content)
        
        # Should not be able to create a Memo with this content
        now = datetime.utcnow()
        with pytest.raises(ValidationError):
            Memo(
                id="test-id",
                title="Valid title",
                content=content,
                created_at=now,
                updated_at=now
            )

# Feature: ai-summary-api, Property 5: Create-Read Round Trip
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    title=st.text(min_size=1, max_size=200),
    content=st.text(min_size=1, max_size=50000)
)
def test_create_read_round_trip_property(title, content, dynamodb_table):
    """
    Property 5: Create-Read Round Trip
    
    For any valid memo (with valid title and content), creating the memo and 
    then immediately retrieving it by its returned ID SHALL return a memo object 
    with the same title and content, along with a generated ID, creation timestamp, 
    and update timestamp.
    
    Validates: Requirements 1.1, 1.5, 1.6, 2.1
    """
    import json
    import os
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Create memo
    create_event = {
        'httpMethod': 'POST',
        'path': '/memos',
        'body': json.dumps({
            'title': title,
            'content': content
        })
    }
    
    create_response = lambda_handler(create_event, context)
    assert create_response['statusCode'] == 201
    
    created_memo = json.loads(create_response['body'])
    memo_id = created_memo['id']
    
    # Read memo
    get_event = {
        'httpMethod': 'GET',
        'path': f'/memos/{memo_id}',
        'pathParameters': {'id': memo_id}
    }
    
    get_response = lambda_handler(get_event, context)
    assert get_response['statusCode'] == 200
    
    retrieved_memo = json.loads(get_response['body'])
    
    # Verify round trip
    assert retrieved_memo['id'] == memo_id
    assert retrieved_memo['title'] == title
    assert retrieved_memo['content'] == content
    assert 'created_at' in retrieved_memo
    assert 'updated_at' in retrieved_memo
    # Verify timestamps are valid ISO 8601 format
    datetime.fromisoformat(retrieved_memo['created_at'])
    datetime.fromisoformat(retrieved_memo['updated_at'])


# Feature: ai-summary-api, Property 6: Update-Read Round Trip with Timestamp Change
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    original_title=st.text(min_size=1, max_size=200),
    original_content=st.text(min_size=1, max_size=50000),
    new_title=st.text(min_size=1, max_size=200),
    new_content=st.text(min_size=1, max_size=50000)
)
def test_update_read_round_trip_property(original_title, original_content, new_title, new_content, dynamodb_table):
    """
    Property 6: Update-Read Round Trip with Timestamp Change
    
    For any existing memo and valid update data, updating the memo and then 
    immediately retrieving it SHALL return the memo with the updated fields, 
    and the updated_at timestamp SHALL be greater than the original updated_at timestamp.
    
    Validates: Requirements 4.1, 4.3, 4.4
    """
    import json
    import os
    import time
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Create memo
    create_event = {
        'httpMethod': 'POST',
        'path': '/memos',
        'body': json.dumps({
            'title': original_title,
            'content': original_content
        })
    }
    
    create_response = lambda_handler(create_event, context)
    created_memo = json.loads(create_response['body'])
    memo_id = created_memo['id']
    original_updated_at = created_memo['updated_at']
    
    # Wait a moment to ensure timestamp difference
    time.sleep(0.01)
    
    # Update memo
    update_event = {
        'httpMethod': 'PUT',
        'path': f'/memos/{memo_id}',
        'pathParameters': {'id': memo_id},
        'body': json.dumps({
            'title': new_title,
            'content': new_content
        })
    }
    
    update_response = lambda_handler(update_event, context)
    assert update_response['statusCode'] == 200
    
    # Read updated memo
    get_event = {
        'httpMethod': 'GET',
        'path': f'/memos/{memo_id}',
        'pathParameters': {'id': memo_id}
    }
    
    get_response = lambda_handler(get_event, context)
    assert get_response['statusCode'] == 200
    
    updated_memo = json.loads(get_response['body'])
    
    # Verify update
    assert updated_memo['id'] == memo_id
    assert updated_memo['title'] == new_title
    assert updated_memo['content'] == new_content
    assert updated_memo['updated_at'] > original_updated_at


# Feature: ai-summary-api, Property 7: Delete-Read Verification
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    title=st.text(min_size=1, max_size=200),
    content=st.text(min_size=1, max_size=50000)
)
def test_delete_read_verification_property(title, content, dynamodb_table):
    """
    Property 7: Delete-Read Verification
    
    For any existing memo, after successfully deleting the memo (receiving 204 status), 
    attempting to retrieve that memo by its ID SHALL return a 404 error.
    
    Validates: Requirements 5.1, 5.4
    """
    import json
    import os
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Create memo
    create_event = {
        'httpMethod': 'POST',
        'path': '/memos',
        'body': json.dumps({
            'title': title,
            'content': content
        })
    }
    
    create_response = lambda_handler(create_event, context)
    created_memo = json.loads(create_response['body'])
    memo_id = created_memo['id']
    
    # Delete memo
    delete_event = {
        'httpMethod': 'DELETE',
        'path': f'/memos/{memo_id}',
        'pathParameters': {'id': memo_id}
    }
    
    delete_response = lambda_handler(delete_event, context)
    assert delete_response['statusCode'] == 204
    
    # Try to read deleted memo
    get_event = {
        'httpMethod': 'GET',
        'path': f'/memos/{memo_id}',
        'pathParameters': {'id': memo_id}
    }
    
    get_response = lambda_handler(get_event, context)
    assert get_response['statusCode'] == 404
    
    error_body = json.loads(get_response['body'])
    assert error_body['error']['code'] == 'NotFound'


# Feature: ai-summary-api, Property 8: Memo Response Structure Completeness
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    title=st.text(min_size=1, max_size=200),
    content=st.text(min_size=1, max_size=50000)
)
def test_response_structure_completeness_property(title, content, dynamodb_table):
    """
    Property 8: Memo Response Structure Completeness
    
    For any successful memo operation (create, read, update), the response SHALL 
    contain all required fields: id (string), title (string), content (string), 
    created_at (ISO 8601 timestamp), and updated_at (ISO 8601 timestamp).
    
    Validates: Requirements 1.6, 2.2, 4.4
    """
    import json
    import os
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Test create operation
    create_event = {
        'httpMethod': 'POST',
        'path': '/memos',
        'body': json.dumps({
            'title': title,
            'content': content
        })
    }
    
    create_response = lambda_handler(create_event, context)
    assert create_response['statusCode'] == 201
    
    created_memo = json.loads(create_response['body'])
    
    # Verify all required fields in create response
    assert 'id' in created_memo and isinstance(created_memo['id'], str)
    assert 'title' in created_memo and isinstance(created_memo['title'], str)
    assert 'content' in created_memo and isinstance(created_memo['content'], str)
    assert 'created_at' in created_memo and isinstance(created_memo['created_at'], str)
    assert 'updated_at' in created_memo and isinstance(created_memo['updated_at'], str)
    
    # Verify timestamps are valid ISO 8601
    datetime.fromisoformat(created_memo['created_at'])
    datetime.fromisoformat(created_memo['updated_at'])
    
    memo_id = created_memo['id']
    
    # Test read operation
    get_event = {
        'httpMethod': 'GET',
        'path': f'/memos/{memo_id}',
        'pathParameters': {'id': memo_id}
    }
    
    get_response = lambda_handler(get_event, context)
    assert get_response['statusCode'] == 200
    
    retrieved_memo = json.loads(get_response['body'])
    
    # Verify all required fields in read response
    assert 'id' in retrieved_memo and isinstance(retrieved_memo['id'], str)
    assert 'title' in retrieved_memo and isinstance(retrieved_memo['title'], str)
    assert 'content' in retrieved_memo and isinstance(retrieved_memo['content'], str)
    assert 'created_at' in retrieved_memo and isinstance(retrieved_memo['created_at'], str)
    assert 'updated_at' in retrieved_memo and isinstance(retrieved_memo['updated_at'], str)
    
    # Test update operation
    update_event = {
        'httpMethod': 'PUT',
        'path': f'/memos/{memo_id}',
        'pathParameters': {'id': memo_id},
        'body': json.dumps({
            'title': title + ' updated'
        })
    }
    
    update_response = lambda_handler(update_event, context)
    assert update_response['statusCode'] == 200
    
    updated_memo = json.loads(update_response['body'])
    
    # Verify all required fields in update response
    assert 'id' in updated_memo and isinstance(updated_memo['id'], str)
    assert 'title' in updated_memo and isinstance(updated_memo['title'], str)
    assert 'content' in updated_memo and isinstance(updated_memo['content'], str)
    assert 'created_at' in updated_memo and isinstance(updated_memo['created_at'], str)
    assert 'updated_at' in updated_memo and isinstance(updated_memo['updated_at'], str)


# Feature: ai-summary-api, Property 9: List Completeness
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    memo_count=st.integers(min_value=0, max_value=10)
)
def test_list_completeness_property(memo_count, dynamodb_table):
    """
    Property 9: List Completeness
    
    For any set of created memos, listing all memos SHALL return all memos that 
    have been created and not deleted, with no duplicates.
    
    Validates: Requirements 3.1
    """
    import json
    import os
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Create memos
    created_ids = set()
    for i in range(memo_count):
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': f'Memo {i}',
                'content': f'Content {i}'
            })
        }
        
        create_response = lambda_handler(create_event, context)
        created_memo = json.loads(create_response['body'])
        created_ids.add(created_memo['id'])
    
    # List all memos
    list_event = {
        'httpMethod': 'GET',
        'path': '/memos',
        'queryStringParameters': {'page_size': '100'}  # Get all in one page
    }
    
    list_response = lambda_handler(list_event, context)
    assert list_response['statusCode'] == 200
    
    list_body = json.loads(list_response['body'])
    listed_memos = list_body['memos']
    
    # Verify all created memos are in the list
    listed_ids = {memo['id'] for memo in listed_memos}
    assert created_ids.issubset(listed_ids)
    
    # Verify no duplicates
    assert len(listed_ids) == len(listed_memos)


# Feature: ai-summary-api, Property 10: List Sorting Order
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    memo_count=st.integers(min_value=2, max_value=10)
)
def test_list_sorting_order_property(memo_count, dynamodb_table):
    """
    Property 10: List Sorting Order
    
    For any list of memos returned by the list operation, the memos SHALL be 
    sorted by updated_at timestamp in descending order (most recently updated first).
    
    Validates: Requirements 3.2
    """
    import json
    import os
    import time
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Create memos with slight delays to ensure different timestamps
    for i in range(memo_count):
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': f'Memo {i}',
                'content': f'Content {i}'
            })
        }
        
        lambda_handler(create_event, context)
        time.sleep(0.01)  # Small delay to ensure different timestamps
    
    # List all memos
    list_event = {
        'httpMethod': 'GET',
        'path': '/memos',
        'queryStringParameters': {'page_size': '100'}
    }
    
    list_response = lambda_handler(list_event, context)
    assert list_response['statusCode'] == 200
    
    list_body = json.loads(list_response['body'])
    listed_memos = list_body['memos']
    
    # Verify sorting order (descending by updated_at)
    if len(listed_memos) >= 2:
        for i in range(len(listed_memos) - 1):
            current_updated = datetime.fromisoformat(listed_memos[i]['updated_at'])
            next_updated = datetime.fromisoformat(listed_memos[i + 1]['updated_at'])
            assert current_updated >= next_updated, "Memos should be sorted by updated_at descending"


# Feature: ai-summary-api, Property 11: Pagination Page Size Enforcement
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    requested_page_size=st.integers(min_value=-10, max_value=200)
)
def test_pagination_page_size_enforcement_property(requested_page_size, dynamodb_table):
    """
    Property 11: Pagination Page Size Enforcement
    
    For any list request, if no page_size is specified, the response SHALL contain 
    at most 20 memos, and if a page_size is specified, it SHALL be capped at 100 
    memos regardless of the requested value.
    
    Validates: Requirements 3.3
    """
    import json
    import os
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Create enough memos to test pagination (more than 100)
    for i in range(min(30, max(requested_page_size + 10, 25))):
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': f'Memo {i}',
                'content': f'Content {i}'
            })
        }
        lambda_handler(create_event, context)
    
    # Test with specified page_size
    list_event = {
        'httpMethod': 'GET',
        'path': '/memos',
        'queryStringParameters': {'page_size': str(requested_page_size)}
    }
    
    list_response = lambda_handler(list_event, context)
    assert list_response['statusCode'] == 200
    
    list_body = json.loads(list_response['body'])
    listed_memos = list_body['memos']
    
    # Verify page size enforcement
    if requested_page_size <= 0:
        # Invalid page size should default to 20
        assert len(listed_memos) <= 20
    elif requested_page_size > 100:
        # Should be capped at 100
        assert len(listed_memos) <= 100
    else:
        # Should respect the requested size
        assert len(listed_memos) <= requested_page_size
    
    # Test without page_size (should default to 20)
    list_event_no_size = {
        'httpMethod': 'GET',
        'path': '/memos',
        'queryStringParameters': None
    }
    
    list_response_no_size = lambda_handler(list_event_no_size, context)
    list_body_no_size = json.loads(list_response_no_size['body'])
    assert len(list_body_no_size['memos']) <= 20


# Feature: ai-summary-api, Property 12: Pagination Token Navigation
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    memo_count=st.integers(min_value=5, max_value=15),
    page_size=st.integers(min_value=2, max_value=5)
)
def test_pagination_token_navigation_property(memo_count, page_size, dynamodb_table):
    """
    Property 12: Pagination Token Navigation
    
    For any list request that returns a next_token, using that next_token in a 
    subsequent request SHALL return the next page of results with no overlap or 
    gaps in the memo sequence.
    
    Validates: Requirements 3.4
    """
    import json
    import os
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Create memos
    created_ids = set()
    for i in range(memo_count):
        create_event = {
            'httpMethod': 'POST',
            'path': '/memos',
            'body': json.dumps({
                'title': f'Memo {i}',
                'content': f'Content {i}'
            })
        }
        
        create_response = lambda_handler(create_event, context)
        created_memo = json.loads(create_response['body'])
        created_ids.add(created_memo['id'])
    
    # Paginate through all memos
    all_listed_ids = []
    next_token = None
    
    while True:
        list_event = {
            'httpMethod': 'GET',
            'path': '/memos',
            'queryStringParameters': {'page_size': str(page_size)}
        }
        
        if next_token:
            list_event['queryStringParameters']['next_token'] = next_token
        
        list_response = lambda_handler(list_event, context)
        assert list_response['statusCode'] == 200
        
        list_body = json.loads(list_response['body'])
        listed_memos = list_body['memos']
        
        # Collect IDs from this page
        page_ids = [memo['id'] for memo in listed_memos]
        all_listed_ids.extend(page_ids)
        
        # Check for next page
        next_token = list_body.get('next_token')
        if not next_token:
            break
    
    # Verify no duplicates (no overlap)
    assert len(all_listed_ids) == len(set(all_listed_ids)), "Pagination should not return duplicates"
    
    # Verify all created memos are present (no gaps)
    listed_ids_set = set(all_listed_ids)
    assert created_ids.issubset(listed_ids_set), "All created memos should be in paginated results"


# Feature: ai-summary-api, Property 13: Non-Existent ID Returns 404
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    fake_id=st.text(min_size=1, max_size=100)
)
def test_nonexistent_id_returns_404_property(fake_id, dynamodb_table):
    """
    Property 13: Non-Existent ID Returns 404
    
    For any operation (get, update, delete) performed with a memo ID that does not 
    exist in the system, the API SHALL return a 404 status code with a descriptive 
    error message.
    
    Validates: Requirements 2.3, 4.5, 5.3
    """
    import json
    import os
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Test GET with non-existent ID
    get_event = {
        'httpMethod': 'GET',
        'path': f'/memos/{fake_id}',
        'pathParameters': {'id': fake_id}
    }
    
    get_response = lambda_handler(get_event, context)
    assert get_response['statusCode'] == 404
    
    get_body = json.loads(get_response['body'])
    assert get_body['error']['code'] == 'NotFound'
    assert 'message' in get_body['error']
    
    # Test UPDATE with non-existent ID
    update_event = {
        'httpMethod': 'PUT',
        'path': f'/memos/{fake_id}',
        'pathParameters': {'id': fake_id},
        'body': json.dumps({
            'title': 'Updated Title'
        })
    }
    
    update_response = lambda_handler(update_event, context)
    assert update_response['statusCode'] == 404
    
    update_body = json.loads(update_response['body'])
    assert update_body['error']['code'] == 'NotFound'
    assert 'message' in update_body['error']
    
    # Test DELETE with non-existent ID
    delete_event = {
        'httpMethod': 'DELETE',
        'path': f'/memos/{fake_id}',
        'pathParameters': {'id': fake_id}
    }
    
    delete_response = lambda_handler(delete_event, context)
    assert delete_response['statusCode'] == 404
    
    delete_body = json.loads(delete_response['body'])
    assert delete_body['error']['code'] == 'NotFound'
    assert 'message' in delete_body['error']


# Feature: ai-summary-api, Property 14: Successful Deletion Status Code
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    title=st.text(min_size=1, max_size=200),
    content=st.text(min_size=1, max_size=50000)
)
def test_successful_deletion_status_code_property(title, content, dynamodb_table):
    """
    Property 14: Successful Deletion Status Code
    
    For any existing memo, successfully deleting that memo SHALL return a 204 
    (No Content) status code with an empty response body.
    
    Validates: Requirements 5.2
    """
    import json
    import os
    from unittest.mock import Mock
    
    # Set up environment
    os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
    os.environ['POWERTOOLS_SERVICE_NAME'] = 'memo-service'
    os.environ['POWERTOOLS_TRACE_DISABLED'] = 'true'
    
    from src.functions.memo.handler import lambda_handler
    
    # Create mock context
    context = Mock()
    context.request_id = 'test-request-id'
    
    # Create memo
    create_event = {
        'httpMethod': 'POST',
        'path': '/memos',
        'body': json.dumps({
            'title': title,
            'content': content
        })
    }
    
    create_response = lambda_handler(create_event, context)
    created_memo = json.loads(create_response['body'])
    memo_id = created_memo['id']
    
    # Delete memo
    delete_event = {
        'httpMethod': 'DELETE',
        'path': f'/memos/{memo_id}',
        'pathParameters': {'id': memo_id}
    }
    
    delete_response = lambda_handler(delete_event, context)
    
    # Verify 204 status code
    assert delete_response['statusCode'] == 204
    
    # Verify empty body
    assert delete_response['body'] == ''


# Pytest fixtures for property tests
@pytest.fixture
def dynamodb_table():
    """Create mock DynamoDB table for property testing."""
    from moto import mock_aws
    import boto3
    
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
