"""
AI Lambda Function Handler
Handles AI-powered question answering using AWS Bedrock
"""
import json
import os
import time
from typing import Dict, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.metrics import MetricUnit

from models.memo import ValidationError
from repositories.memo_repository import MemoRepository, MemoNotFoundError

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


class ServiceUnavailableError(Exception):
    """Raised when AI service is unavailable after retries."""
    pass


def validate_question(question: str) -> None:
    """
    Validate AI question length.
    
    Args:
        question: The question to validate
        
    Raises:
        ValidationError: If question is not between 1 and 1000 characters
    """
    if not isinstance(question, str):
        raise ValidationError("Question must be a string")
    
    if len(question) < 1:
        raise ValidationError("Question must be at least 1 character")
    
    if len(question) > 1000:
        raise ValidationError("Question must not exceed 1000 characters")


def build_prompt(title: str, content: str, question: str) -> str:
    """
    Build the prompt for AWS Bedrock Claude.
    
    Args:
        title: Memo title
        content: Memo content
        question: User's question
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a helpful assistant analyzing memo content. 
Based on the following memo, please answer the user's question.

Memo Title: {title}
Memo Content: {content}

User Question: {question}

Please provide a clear and concise answer based only on the information in the memo."""
    
    return prompt


def invoke_bedrock_with_retry(
    bedrock_client,
    model_id: str,
    memo_title: str,
    memo_content: str,
    question: str,
    max_retries: int = 3
) -> str:
    """
    Invoke AWS Bedrock with exponential backoff retry logic.
    
    Args:
        bedrock_client: Boto3 Bedrock Runtime client
        model_id: Bedrock model identifier
        memo_title: Memo title for context
        memo_content: Memo content to analyze
        question: User's question
        max_retries: Maximum number of retry attempts (default 3)
        
    Returns:
        AI-generated answer text
        
    Raises:
        ServiceUnavailableError: If all retries are exhausted
        ClientError: For non-retryable errors
    """
    # Apply tracer decorator if available
    if tracer:
        invoke_bedrock_with_retry = tracer.capture_method(invoke_bedrock_with_retry)
    
    prompt = build_prompt(memo_title, memo_content, question)
    
    # Build request body for Claude 3+ (Messages API)
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(
                "Invoking Bedrock",
                extra={
                    "attempt": attempt + 1,
                    "model_id": model_id,
                    "question_length": len(question)
                }
            )
            
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response (Messages API format)
            response_body = json.loads(response['body'].read())
            
            # Extract answer from Messages API response
            content_blocks = response_body.get('content', [])
            if content_blocks and len(content_blocks) > 0:
                answer = content_blocks[0].get('text', '').strip()
            else:
                answer = ''
            
            logger.info(
                "Bedrock invocation successful",
                extra={
                    "attempt": attempt + 1,
                    "answer_length": len(answer)
                }
            )
            
            metrics.add_metric(name="BedrockSuccess", unit=MetricUnit.Count, value=1)
            
            return answer
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            # Check if error is retryable
            if error_code in ['ThrottlingException', 'ServiceUnavailableException']:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Bedrock error, retrying in {wait_time}s",
                        extra={
                            "attempt": attempt + 1,
                            "error_code": error_code,
                            "wait_time": wait_time
                        }
                    )
                    metrics.add_metric(name="BedrockRetry", unit=MetricUnit.Count, value=1)
                    time.sleep(wait_time)
                else:
                    logger.error(
                        "Bedrock retries exhausted",
                        extra={
                            "attempts": max_retries,
                            "error_code": error_code
                        }
                    )
                    metrics.add_metric(name="BedrockFailure", unit=MetricUnit.Count, value=1)
                    raise ServiceUnavailableError("AI service temporarily unavailable. Please try again later.")
            else:
                # Non-retryable error
                logger.error(
                    "Bedrock non-retryable error",
                    extra={
                        "error_code": error_code,
                        "error_message": str(e)
                    }
                )
                metrics.add_metric(name="BedrockError", unit=MetricUnit.Count, value=1)
                raise
    
    # Should not reach here, but just in case
    raise ServiceUnavailableError("AI service temporarily unavailable. Please try again later.")


def error_response(status_code: int, error_code: str, message: str, request_id: str = None) -> Dict[str, Any]:
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
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(error_body, ensure_ascii=False)
    }


@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main Lambda handler for AI question answering.
    
    Handles POST /memos/{id}/ask endpoint.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    # Apply tracer decorator if available
    if tracer:
        lambda_handler_traced = tracer.capture_lambda_handler(lambda_handler)
    
    start_time = time.time()
    request_id = context.aws_request_id
    
    logger.info("AI question request received", extra={"request_id": request_id})
    
    try:
        # Extract memo ID from path parameters
        path_parameters = event.get('pathParameters', {})
        if not path_parameters or 'id' not in path_parameters:
            return error_response(400, "ValidationError", "Memo ID is required", request_id)
        
        memo_id = path_parameters['id']
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return error_response(400, "ValidationError", "Invalid JSON in request body", request_id)
        
        # Extract and validate question
        question = body.get('question', '')
        
        try:
            validate_question(question)
        except ValidationError as e:
            logger.warning(
                "Question validation failed",
                extra={
                    "memo_id": memo_id,
                    "error": str(e),
                    "request_id": request_id
                }
            )
            metrics.add_metric(name="ValidationError", unit=MetricUnit.Count, value=1)
            return error_response(400, "ValidationError", str(e), request_id)
        
        # Retrieve memo from DynamoDB
        repository = MemoRepository()
        
        try:
            memo = repository.get_memo(memo_id)
        except MemoNotFoundError as e:
            logger.info(
                "Memo not found",
                extra={
                    "memo_id": memo_id,
                    "request_id": request_id
                }
            )
            metrics.add_metric(name="MemoNotFound", unit=MetricUnit.Count, value=1)
            return error_response(404, "NotFound", str(e), request_id)
        
        # Initialize Bedrock client
        bedrock_region = os.environ.get('BEDROCK_REGION', 'us-west-2')
        bedrock_client = boto3.client('bedrock-runtime', region_name=bedrock_region)
        model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-sonnet-4-6')
        max_retries = int(os.environ.get('MAX_RETRIES', '3'))
        
        # Invoke Bedrock with retry logic
        try:
            answer = invoke_bedrock_with_retry(
                bedrock_client=bedrock_client,
                model_id=model_id,
                memo_title=memo.title,
                memo_content=memo.content,
                question=question,
                max_retries=max_retries
            )
        except ServiceUnavailableError as e:
            logger.error(
                "AI service unavailable",
                extra={
                    "memo_id": memo_id,
                    "request_id": request_id
                }
            )
            return error_response(503, "ServiceUnavailable", str(e), request_id)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Build response
        response_body = {
            'answer': answer,
            'metadata': {
                'model_id': model_id,
                'processing_time_ms': processing_time_ms,
                'memo_id': memo_id
            }
        }
        
        logger.info(
            "AI question processed successfully",
            extra={
                "memo_id": memo_id,
                "processing_time_ms": processing_time_ms,
                "request_id": request_id
            }
        )
        
        metrics.add_metric(name="AIQuestionSuccess", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="ProcessingTime", unit=MetricUnit.Milliseconds, value=processing_time_ms)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.exception(
            "Unexpected error in AI function",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "request_id": request_id
            }
        )
        metrics.add_metric(name="UnexpectedError", unit=MetricUnit.Count, value=1)
        return error_response(500, "InternalError", "An unexpected error occurred", request_id)
