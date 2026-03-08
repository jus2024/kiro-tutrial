"""
Memo Lambda Function Handler
Handles CRUD operations for memos
"""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.metrics import MetricUnit

# Initialize tracer only if X-Ray SDK is available
try:
    from aws_lambda_powertools import Tracer
    tracer = Tracer()
except Exception:
    # X-Ray not available (e.g., in tests), use a no-op decorator
    class NoOpTracer:
        def capture_lambda_handler(self, func):
            return func
        def capture_method(self, func):
            return func
    tracer = NoOpTracer()

from models.memo import Memo, ValidationError, validate_title, validate_content
from repositories.memo_repository import MemoRepository, MemoNotFoundError

logger = Logger()
metrics = Metrics(namespace="AIMemoryAPI")

# Repository will be initialized per request to allow for testing
repository = None


def get_repository() -> MemoRepository:
    """Get or create repository instance."""
    global repository
    if repository is None:
        repository = MemoRepository()
    return repository


def error_response(status_code: int, error_code: str, message: str, request_id: str = "") -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error_code: Error code identifier
        message: Human-readable error message
        request_id: Request ID for tracing
        
    Returns:
        API Gateway response dictionary
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': {
                'code': error_code,
                'message': message,
                'request_id': request_id
            }
        })
    }


def success_response(status_code: int, body: Any) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        status_code: HTTP status code
        body: Response body (will be JSON serialized)
        
    Returns:
        API Gateway response dictionary
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }


@tracer.capture_method
def create_memo(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Create a new memo.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with created memo (201) or error
    """
    start_time = datetime.utcnow()
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        title = body.get('title')
        content = body.get('content')
        
        # Validate required fields
        if not title:
            raise ValidationError("Title is required")
        if not content:
            raise ValidationError("Content is required")
        
        # Validate field constraints
        validate_title(title)
        validate_content(content)
        
        # Create memo object
        memo_id = str(uuid.uuid4())
        now = datetime.utcnow()
        memo = Memo(
            id=memo_id,
            title=title,
            content=content,
            created_at=now,
            updated_at=now
        )
        
        # Persist to DynamoDB
        created_memo = get_repository().create_memo(memo)
        
        # Log success
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info("Memo created", extra={
            "operation": "create_memo",
            "memo_id": memo_id,
            "processing_time_ms": processing_time,
            "request_id": context.aws_request_id
        })
        
        # Emit metrics
        metrics.add_metric(name="MemoCreated", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="ProcessingTime", unit=MetricUnit.Milliseconds, value=processing_time)
        
        return success_response(201, created_memo.to_dict())
        
    except ValidationError as e:
        logger.warning("Validation error", extra={"error": str(e), "request_id": context.aws_request_id})
        metrics.add_metric(name="ValidationError", unit=MetricUnit.Count, value=1)
        return error_response(400, "ValidationError", str(e), context.aws_request_id)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON", extra={"request_id": context.aws_request_id})
        metrics.add_metric(name="ValidationError", unit=MetricUnit.Count, value=1)
        return error_response(400, "ValidationError", "Invalid JSON in request body", context.aws_request_id)
    except Exception as e:
        logger.exception("Unexpected error in create_memo")
        metrics.add_metric(name="InternalError", unit=MetricUnit.Count, value=1)
        return error_response(500, "InternalError", "An unexpected error occurred", context.aws_request_id)


@tracer.capture_method
def get_memo(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Retrieve a memo by ID.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with memo (200) or error (404)
    """
    start_time = datetime.utcnow()
    
    try:
        # Extract memo ID from path parameters
        path_params = event.get('pathParameters', {})
        memo_id = path_params.get('id')
        
        if not memo_id:
            raise ValidationError("Memo ID is required")
        
        # Retrieve from DynamoDB
        memo = get_repository().get_memo(memo_id)
        
        # Log success
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info("Memo retrieved", extra={
            "operation": "get_memo",
            "memo_id": memo_id,
            "processing_time_ms": processing_time,
            "request_id": context.aws_request_id
        })
        
        # Emit metrics
        metrics.add_metric(name="MemoRetrieved", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="ProcessingTime", unit=MetricUnit.Milliseconds, value=processing_time)
        
        return success_response(200, memo.to_dict())
        
    except MemoNotFoundError as e:
        logger.info("Memo not found", extra={"memo_id": e.memo_id, "request_id": context.aws_request_id})
        metrics.add_metric(name="MemoNotFound", unit=MetricUnit.Count, value=1)
        return error_response(404, "NotFound", str(e), context.aws_request_id)
    except Exception as e:
        logger.exception("Unexpected error in get_memo")
        metrics.add_metric(name="InternalError", unit=MetricUnit.Count, value=1)
        return error_response(500, "InternalError", "An unexpected error occurred", context.aws_request_id)


@tracer.capture_method
def list_memos(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    List all memos with pagination.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with memo list (200) or error
    """
    start_time = datetime.utcnow()
    
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        page_size = int(query_params.get('page_size', 20))
        next_token = query_params.get('next_token')
        
        # Validate page size (default 20, max 100)
        if page_size < 1:
            page_size = 20
        page_size = min(page_size, 100)
        
        # Retrieve from DynamoDB
        memos, new_next_token = get_repository().list_memos(page_size=page_size, next_token=next_token)
        
        # Build response
        response_body = {
            'memos': [memo.to_dict() for memo in memos],
            'next_token': new_next_token
        }
        
        # Log success
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info("Memos listed", extra={
            "operation": "list_memos",
            "count": len(memos),
            "page_size": page_size,
            "has_next": new_next_token is not None,
            "processing_time_ms": processing_time,
            "request_id": context.aws_request_id
        })
        
        # Emit metrics
        metrics.add_metric(name="MemosListed", unit=MetricUnit.Count, value=len(memos))
        metrics.add_metric(name="ProcessingTime", unit=MetricUnit.Milliseconds, value=processing_time)
        
        return success_response(200, response_body)
        
    except ValueError:
        logger.warning("Invalid page_size parameter", extra={"request_id": context.aws_request_id})
        metrics.add_metric(name="ValidationError", unit=MetricUnit.Count, value=1)
        return error_response(400, "ValidationError", "page_size must be a valid integer", context.aws_request_id)
    except Exception as e:
        logger.exception("Unexpected error in list_memos")
        metrics.add_metric(name="InternalError", unit=MetricUnit.Count, value=1)
        return error_response(500, "InternalError", "An unexpected error occurred", context.aws_request_id)


@tracer.capture_method
def update_memo(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Update an existing memo.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with updated memo (200) or error (404, 400)
    """
    start_time = datetime.utcnow()
    
    try:
        # Extract memo ID from path parameters
        path_params = event.get('pathParameters', {})
        memo_id = path_params.get('id')
        
        if not memo_id:
            raise ValidationError("Memo ID is required")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        title = body.get('title')
        content = body.get('content')
        
        # At least one field must be provided
        if title is None and content is None:
            raise ValidationError("At least one field (title or content) must be provided")
        
        # Validate fields if provided
        if title is not None:
            validate_title(title)
        if content is not None:
            validate_content(content)
        
        # Update in DynamoDB
        updated_memo = get_repository().update_memo(
            memo_id=memo_id,
            title=title,
            content=content,
            updated_at=datetime.utcnow()
        )
        
        # Log success
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info("Memo updated", extra={
            "operation": "update_memo",
            "memo_id": memo_id,
            "processing_time_ms": processing_time,
            "request_id": context.aws_request_id
        })
        
        # Emit metrics
        metrics.add_metric(name="MemoUpdated", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="ProcessingTime", unit=MetricUnit.Milliseconds, value=processing_time)
        
        return success_response(200, updated_memo.to_dict())
        
    except ValidationError as e:
        logger.warning("Validation error", extra={"error": str(e), "request_id": context.aws_request_id})
        metrics.add_metric(name="ValidationError", unit=MetricUnit.Count, value=1)
        return error_response(400, "ValidationError", str(e), context.aws_request_id)
    except MemoNotFoundError as e:
        logger.info("Memo not found", extra={"memo_id": e.memo_id, "request_id": context.aws_request_id})
        metrics.add_metric(name="MemoNotFound", unit=MetricUnit.Count, value=1)
        return error_response(404, "NotFound", str(e), context.aws_request_id)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON", extra={"request_id": context.aws_request_id})
        metrics.add_metric(name="ValidationError", unit=MetricUnit.Count, value=1)
        return error_response(400, "ValidationError", "Invalid JSON in request body", context.aws_request_id)
    except Exception as e:
        logger.exception("Unexpected error in update_memo")
        metrics.add_metric(name="InternalError", unit=MetricUnit.Count, value=1)
        return error_response(500, "InternalError", "An unexpected error occurred", context.aws_request_id)


@tracer.capture_method
def delete_memo(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Delete a memo by ID.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response with 204 (success) or error (404)
    """
    start_time = datetime.utcnow()
    
    try:
        # Extract memo ID from path parameters
        path_params = event.get('pathParameters', {})
        memo_id = path_params.get('id')
        
        if not memo_id:
            raise ValidationError("Memo ID is required")
        
        # Delete from DynamoDB
        get_repository().delete_memo(memo_id)
        
        # Log success
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info("Memo deleted", extra={
            "operation": "delete_memo",
            "memo_id": memo_id,
            "processing_time_ms": processing_time,
            "request_id": context.aws_request_id
        })
        
        # Emit metrics
        metrics.add_metric(name="MemoDeleted", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="ProcessingTime", unit=MetricUnit.Milliseconds, value=processing_time)
        
        # Return 204 No Content
        return {
            'statusCode': 204,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': ''
        }
        
    except MemoNotFoundError as e:
        logger.info("Memo not found", extra={"memo_id": e.memo_id, "request_id": context.aws_request_id})
        metrics.add_metric(name="MemoNotFound", unit=MetricUnit.Count, value=1)
        return error_response(404, "NotFound", str(e), context.aws_request_id)
    except Exception as e:
        logger.exception("Unexpected error in delete_memo")
        metrics.add_metric(name="InternalError", unit=MetricUnit.Count, value=1)
        return error_response(500, "InternalError", "An unexpected error occurred", context.aws_request_id)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main Lambda handler for memo operations.
    Routes requests based on HTTP method and path.
    
    Routes:
        POST /memos -> create_memo()
        GET /memos/{id} -> get_memo()
        GET /memos -> list_memos()
        PUT /memos/{id} -> update_memo()
        DELETE /memos/{id} -> delete_memo()
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    logger.info("Received request", extra={
        "http_method": event.get('httpMethod'),
        "path": event.get('path'),
        "request_id": context.aws_request_id
    })
    
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        path_params = event.get('pathParameters')
        
        # Route based on HTTP method and path
        if http_method == 'POST' and path == '/memos':
            return create_memo(event, context)
        
        elif http_method == 'GET' and path_params and 'id' in path_params:
            return get_memo(event, context)
        
        elif http_method == 'GET' and path == '/memos':
            return list_memos(event, context)
        
        elif http_method == 'PUT' and path_params and 'id' in path_params:
            return update_memo(event, context)
        
        elif http_method == 'DELETE' and path_params and 'id' in path_params:
            return delete_memo(event, context)
        
        else:
            # Unknown route
            logger.warning("Unknown route", extra={
                "http_method": http_method,
                "path": path,
                "request_id": context.aws_request_id
            })
            return error_response(404, "NotFound", "Route not found", context.aws_request_id)
    
    except Exception as e:
        logger.exception("Unexpected error in lambda_handler")
        metrics.add_metric(name="InternalError", unit=MetricUnit.Count, value=1)
        return error_response(500, "InternalError", "An unexpected error occurred", context.aws_request_id)
