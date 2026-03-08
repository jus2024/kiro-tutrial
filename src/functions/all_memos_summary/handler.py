"""
All Memos Summary Lambda Function Handler
Handles AI-powered summary generation for all memos using AWS Bedrock
"""
import json
import os
import time
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.metrics import MetricUnit

from models.memo import ValidationError
from repositories.memo_repository import MemoRepository
from services.memo_aggregator import MemoAggregator
from services.bedrock_service import BedrockService, ServiceUnavailableError

logger = Logger()
metrics = Metrics(namespace="AIMemoryAPI")

# Initialize tracer conditionally (avoid X-Ray dependency in tests)
tracer = None
if not os.environ.get('POWERTOOLS_TRACE_DISABLED'):
    try:
        from aws_lambda_powertools import Tracer
        tracer = Tracer()
    except ImportError:
        pass


def validate_request(body: Dict[str, Any]) -> None:
    """
    Validate request body format.
    
    Currently accepts empty body or optional filter parameters (future enhancement).
    
    Args:
        body: Parsed request body dictionary
        
    Raises:
        ValidationError: If request format is invalid
    """
    # For MVP, we accept empty body
    # Future enhancement: validate filter parameters if present
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")
    
    # If filters are provided (future enhancement), validate them
    if 'filters' in body:
        filters = body['filters']
        if not isinstance(filters, dict):
            raise ValidationError("Filters must be an object")
        
        # Validate date_from and date_to if present
        if 'date_from' in filters and not isinstance(filters['date_from'], str):
            raise ValidationError("date_from must be a string")
        
        if 'date_to' in filters and not isinstance(filters['date_to'], str):
            raise ValidationError("date_to must be a string")


def error_response(
    status_code: int,
    error_code: str,
    message: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardized error response with UTF-8 encoding.
    
    Args:
        status_code: HTTP status code
        error_code: Error code identifier
        message: Human-readable error message
        request_id: Request ID for tracing
        
    Returns:
        API Gateway response dictionary
    """
    error_body = {
        'error': {
            'code': error_code,
            'message': message
        }
    }
    
    if request_id:
        error_body['error']['request_id'] = request_id
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(error_body, ensure_ascii=False)
    }


@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main Lambda handler for all-memos summary generation.
    
    Handles POST /memos/summary endpoint.
    
    Args:
        event: API Gateway event (empty body or optional filters)
        context: Lambda context with request_id
        
    Returns:
        API Gateway response with summary or error
    """
    # Apply tracer decorator if available
    if tracer:
        lambda_handler_traced = tracer.capture_lambda_handler(lambda_handler)
    
    start_time = time.time()
    request_id = context.aws_request_id
    
    logger.info("All memos summary request received", extra={"request_id": request_id})
    metrics.add_metric(name="AllMemosSummaryRequest", unit=MetricUnit.Count, value=1)
    
    try:
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            logger.warning(
                "Invalid JSON in request body",
                extra={"request_id": request_id}
            )
            metrics.add_metric(name="ValidationError", unit=MetricUnit.Count, value=1)
            return error_response(400, "ValidationError", "Invalid JSON in request body", request_id)
        
        # Validate request format
        try:
            validate_request(body)
        except ValidationError as e:
            logger.warning(
                "Request validation failed",
                extra={
                    "error": str(e),
                    "request_id": request_id
                }
            )
            metrics.add_metric(name="ValidationError", unit=MetricUnit.Count, value=1)
            return error_response(400, "ValidationError", str(e), request_id)
        
        logger.info("Request validation successful", extra={"request_id": request_id})
        
        # Task 5.2: Retrieve and aggregate memos
        try:
            # Initialize repository
            memo_repository = MemoRepository(table_name=os.environ.get('MEMO_TABLE_NAME'))
            
            # Retrieve all memos with pagination
            all_memos = []
            next_token = None
            
            while True:
                memos, next_token = memo_repository.list_memos(page_size=100, next_token=next_token)
                all_memos.extend(memos)
                
                if next_token is None:
                    break
            
            logger.info(
                "Memos retrieved from DynamoDB",
                extra={
                    "request_id": request_id,
                    "memo_count": len(all_memos)
                }
            )
            
            # Task 5.3: Handle empty memo collection
            if len(all_memos) == 0:
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                logger.info(
                    "No memos found, returning empty collection response",
                    extra={
                        "request_id": request_id,
                        "processing_time_ms": processing_time_ms
                    }
                )
                
                # Task 5.8: Emit metrics for empty collection
                metrics.add_metric(name="MemosProcessed", unit=MetricUnit.Count, value=0)
                metrics.add_metric(name="ProcessingTime", unit=MetricUnit.Milliseconds, value=processing_time_ms)
                
                response_body = {
                    'summary': 'メモが存在しないため、要約を生成できません。',
                    'metadata': {
                        'model_id': os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-6'),
                        'processing_time_ms': processing_time_ms,
                        'memos_included': 0,
                        'memos_total': 0,
                        'truncated': False
                    }
                }
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json; charset=utf-8',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                    'body': json.dumps(response_body, ensure_ascii=False)
                }
            
            # Aggregate memos with content limits
            max_tokens = int(os.environ.get('MAX_CONTENT_TOKENS', '180000'))
            aggregator = MemoAggregator(max_tokens=max_tokens)
            aggregation_result = aggregator.aggregate_memos(all_memos)
            
            logger.info(
                "Memos aggregated",
                extra={
                    "request_id": request_id,
                    "included_count": aggregation_result.included_count,
                    "total_count": aggregation_result.total_count,
                    "truncated": aggregation_result.truncated
                }
            )
            
        except Exception as e:
            # Task 5.6: Handle DynamoDB errors
            logger.exception(
                "DynamoDB error during memo retrieval",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "request_id": request_id
                }
            )
            metrics.add_metric(name="DynamoDBError", unit=MetricUnit.Count, value=1)
            return error_response(500, "InternalError", "Failed to retrieve memos from database", request_id)
        
        # Task 5.4: Generate AI summary
        try:
            # Initialize Bedrock service
            model_id = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')
            region = os.environ.get('BEDROCK_REGION', 'us-west-2')
            max_retries = int(os.environ.get('MAX_RETRIES', '3'))
            
            bedrock_service = BedrockService(
                model_id=model_id,
                region=region,
                max_retries=max_retries
            )
            
            # Generate summary
            summary_text = bedrock_service.generate_all_memos_summary(
                aggregated_content=aggregation_result.aggregated_text,
                memo_count=aggregation_result.included_count
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "AI summary generated successfully",
                extra={
                    "request_id": request_id,
                    "processing_time_ms": processing_time_ms,
                    "memos_included": aggregation_result.included_count,
                    "memos_total": aggregation_result.total_count,
                    "truncated": aggregation_result.truncated
                }
            )
            
            # Task 5.8: Emit CloudWatch metrics
            metrics.add_metric(name="MemosProcessed", unit=MetricUnit.Count, value=aggregation_result.included_count)
            metrics.add_metric(name="ProcessingTime", unit=MetricUnit.Milliseconds, value=processing_time_ms)
            
            # Task 5.5: Format response with UTF-8 encoding
            response_body = {
                'summary': summary_text,
                'metadata': {
                    'model_id': model_id,
                    'processing_time_ms': processing_time_ms,
                    'memos_included': aggregation_result.included_count,
                    'memos_total': aggregation_result.total_count,
                    'truncated': aggregation_result.truncated
                }
            }
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps(response_body, ensure_ascii=False)
            }
            
        except ServiceUnavailableError as e:
            # Task 5.6: Handle Bedrock service unavailable errors
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.error(
                "Bedrock service unavailable after retries",
                extra={
                    "error_type": "ServiceUnavailableError",
                    "error_message": str(e),
                    "request_id": request_id,
                    "processing_time_ms": processing_time_ms,
                    "memos_retrieved": aggregation_result.total_count
                }
            )
            
            metrics.add_metric(name="ServiceUnavailableError", unit=MetricUnit.Count, value=1)
            return error_response(503, "ServiceUnavailable", str(e), request_id)
            
        except Exception as e:
            # Task 5.6: Handle unexpected Bedrock errors
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.exception(
                "Bedrock error during summary generation",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "request_id": request_id,
                    "processing_time_ms": processing_time_ms,
                    "memos_retrieved": aggregation_result.total_count
                }
            )
            
            metrics.add_metric(name="BedrockError", unit=MetricUnit.Count, value=1)
            return error_response(500, "InternalError", "Failed to generate AI summary", request_id)
        
    except Exception as e:
        logger.exception(
            "Unexpected error in all memos summary function",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "request_id": request_id
            }
        )
        metrics.add_metric(name="UnexpectedError", unit=MetricUnit.Count, value=1)
        return error_response(500, "InternalError", "An unexpected error occurred", request_id)
