# Implementation Plan: All Memos Summary Feature

## Overview

This plan implements the all-memos-summary feature for the AI要約API. The feature generates AI-powered summaries of all memos using AWS Bedrock Claude Sonnet 4.6. Implementation follows the existing serverless architecture with Python 3.13 Lambda functions, DynamoDB for storage, and AWS Lambda Powertools for observability.

## Tasks

- [x] 1. Set up project structure and data models
  - Create directory structure: `src/functions/all_memos_summary/`, `src/services/`, `tests/unit/`, `tests/property/`
  - Define AggregationResult and SummaryMetadata dataclasses in `src/models/summary_models.py`
  - Set up test fixtures and mock utilities
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. Implement MemoAggregator service
  - [x] 2.1 Create MemoAggregator class with token estimation
    - Implement `__init__` with max_tokens parameter (default 180000)
    - Implement `estimate_tokens` method (approximation: 1 token ≈ 4 characters)
    - Create AggregationResult dataclass
    - _Requirements: 2.1, 2.2_
  
  - [x] 2.2 Implement memo aggregation with prioritization
    - Implement `aggregate_memos` method that sorts by updated_at descending
    - Enforce content limits by including complete memos only
    - Track included_count, total_count, and truncated flag
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [x] 2.3 Write property test for recency-based prioritization
    - **Property 4: Recency-Based Prioritization Under Limits**
    - **Validates: Requirements 2.1, 2.2**
    - Use hypothesis to generate memo lists with varying sizes and timestamps
    - Verify memos are included in descending updated_at order when limits exceeded
  
  - [x] 2.4 Write unit tests for MemoAggregator
    - Test aggregation within limits
    - Test aggregation exceeding limits
    - Test empty memo list
    - Test single memo
    - Test token estimation accuracy
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 3. Implement BedrockService with retry logic
  - [x] 3.1 Create BedrockService class initialization
    - Implement `__init__` with model_id, region, max_retries parameters
    - Initialize boto3 bedrock-runtime client
    - _Requirements: 1.3, 4.1_
  
  - [x] 3.2 Implement prompt building for all-memos summary
    - Implement `build_summary_prompt` method
    - Create Japanese prompt template for comprehensive summary generation
    - Include memo count in prompt context
    - _Requirements: 1.3, 1.5_
  
  - [x] 3.3 Implement Bedrock invocation with exponential backoff
    - Implement `invoke_with_retry` method with exponential backoff (1s, 2s, 4s)
    - Handle ThrottlingException and ServiceUnavailableException as retryable
    - Raise ServiceUnavailableError after 3 failed attempts
    - _Requirements: 4.1, 4.2_
  
  - [x] 3.4 Implement generate_all_memos_summary method
    - Build request body with correct model ID and anthropic version
    - Call invoke_with_retry with formatted request
    - Parse Bedrock response and extract summary text
    - _Requirements: 1.3_
  
  - [x] 3.5 Write property test for retry logic
    - **Property 5: Retry Logic with Exponential Backoff**
    - **Validates: Requirements 4.1**
    - Use hypothesis to generate different retry scenarios
    - Verify exponential backoff timing (1s, 2s, 4s)
    - Verify max 3 retry attempts
  
  - [x] 3.6 Write property test for Bedrock invocation parameters
    - **Property 2: Bedrock Invocation with Correct Parameters**
    - **Validates: Requirements 1.3**
    - Use hypothesis to generate various aggregated content
    - Verify request body structure, model ID, and message format
  
  - [x] 3.7 Write unit tests for BedrockService
    - Test successful invocation
    - Test retry with retryable errors
    - Test non-retryable error handling
    - Test prompt building with Japanese characters
    - Test response parsing
    - _Requirements: 1.3, 4.1, 4.2_

- [x] 4. Checkpoint - Ensure core services pass tests
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Lambda handler with error handling
  - [x] 5.1 Create handler.py with lambda_handler function
    - Set up AWS Lambda Powertools logger and tracer
    - Parse API Gateway event
    - Implement request validation (accept empty body)
    - _Requirements: 7.1, 7.2, 7.5_
  
  - [x] 5.2 Implement memo retrieval and aggregation flow
    - Initialize MemoRepository with MEMO_TABLE_NAME from environment
    - Retrieve all memos using list_memos() with pagination
    - Sort memos by updated_at descending
    - Call MemoAggregator.aggregate_memos()
    - _Requirements: 1.1, 1.2_
  
  - [x] 5.3 Implement empty memo collection handling
    - Check if memo count is zero
    - Return 200 response with message "メモが存在しないため、要約を生成できません。"
    - Set memos_included=0, memos_total=0, truncated=false
    - Skip Bedrock invocation
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [x] 5.4 Implement AI summary generation flow
    - Initialize BedrockService with environment variables
    - Call generate_all_memos_summary() with aggregated content
    - Measure processing time in milliseconds
    - _Requirements: 1.3, 5.3_
  
  - [x] 5.5 Implement response formatting with UTF-8 encoding
    - Create success response with summary, metadata (model_id, processing_time_ms, memos_included, memos_total, truncated)
    - Set Content-Type header to application/json; charset=utf-8
    - Add CORS headers (Access-Control-Allow-Origin, Access-Control-Allow-Methods)
    - Return 200 status code
    - _Requirements: 1.4, 1.5, 7.3, 7.4_
  
  - [x] 5.6 Implement comprehensive error handling
    - Catch ValidationError → return 400 with error response
    - Catch DynamoDB errors → log and return 500 with error response
    - Catch ServiceUnavailableError → return 503 with error response
    - Catch unexpected exceptions → log stack trace and return 500
    - All error responses include error code, message, and request_id
    - _Requirements: 4.2, 4.3, 4.4_
  
  - [x] 5.7 Implement structured logging with Lambda Powertools
    - Log all requests with request_id, memo count, processing time, status
    - Log errors with error type, message, and stack trace
    - Use JSON format for all logs
    - Set service name to "ai-summary-api"
    - _Requirements: 6.1, 6.3, 4.4_
  
  - [x] 5.8 Implement CloudWatch metrics emission
    - Emit metric for request count (dimension: endpoint=/memos/summary)
    - Emit metric for processing time (unit: milliseconds)
    - Emit metric for memos processed count
    - Emit metric for error count (dimension: error_type)
    - _Requirements: 6.2_
  
  - [x] 5.9 Write property test for response structure completeness
    - **Property 3: Response Structure Completeness**
    - **Validates: Requirements 1.4, 1.5, 2.3, 2.4, 5.3, 7.3, 7.4**
    - Use hypothesis to generate various memo collections
    - Verify all required fields present with correct types
    - Verify UTF-8 encoding and CORS headers
  
  - [x] 5.10 Write property test for error response structure
    - **Property 6: Error Response Structure**
    - **Validates: Requirements 4.2, 4.3, 7.5**
    - Use hypothesis to generate various error conditions
    - Verify error responses contain code, message, request_id
    - Verify appropriate HTTP status codes
  
  - [x] 5.11 Write property test for structured logging
    - **Property 7: Structured Logging Completeness**
    - **Validates: Requirements 4.4, 6.1, 6.3**
    - Use hypothesis to generate various request scenarios
    - Verify logs contain required fields for success and error cases
  
  - [x] 5.12 Write property test for CloudWatch metrics
    - **Property 8: CloudWatch Metrics Emission**
    - **Validates: Requirements 6.2**
    - Use hypothesis to generate various request outcomes
    - Verify metrics emitted with correct names and dimensions
  
  - [x] 5.13 Write property test for request validation
    - **Property 9: Request Validation**
    - **Validates: Requirements 7.2, 7.5**
    - Use hypothesis to generate valid and invalid request bodies
    - Verify empty JSON accepted, malformed JSON rejected with 400
  
  - [x] 5.14 Write unit tests for Lambda handler
    - Test empty memo collection (example)
    - Test valid request with memos
    - Test invalid JSON request body
    - Test DynamoDB error handling
    - Test Bedrock retry exhaustion (example)
    - Test UTF-8 encoding with Japanese characters
    - Test timeout scenarios
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.2, 3.3, 4.2, 4.3, 5.1, 5.2_

- [x] 6. Checkpoint - Ensure handler tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Create SAM template and infrastructure configuration
  - [x] 7.1 Define Lambda function in SAM template
    - Create or update template.yaml with AllMemosSummaryFunction
    - Set runtime to python3.13, timeout to 65 seconds, memory to 1024MB
    - Define environment variables: MEMO_TABLE_NAME, BEDROCK_MODEL_ID, BEDROCK_REGION, MAX_RETRIES, MAX_CONTENT_TOKENS, LOG_LEVEL, POWERTOOLS_SERVICE_NAME
    - _Requirements: 5.1, 5.2_
  
  - [x] 7.2 Configure IAM permissions
    - Add DynamoDB read permissions (dynamodb:Query, dynamodb:Scan) for MemoTable
    - Add Bedrock invoke permissions (bedrock:InvokeModel) for Claude Sonnet 4.6
    - Add CloudWatch Logs permissions (logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents)
    - Add CloudWatch Metrics permissions (cloudwatch:PutMetricData)
    - _Requirements: 1.1, 1.3, 6.2_
  
  - [x] 7.3 Configure API Gateway endpoint
    - Define POST /memos/summary endpoint
    - Set integration to Lambda proxy
    - Enable CORS with appropriate origins, methods, and headers
    - Configure request validation (accept empty body)
    - Set timeout to 65 seconds
    - _Requirements: 7.1, 7.2, 7.4, 7.5_
  
  - [x] 7.4 Write integration test for API endpoint
    - Test end-to-end API request/response flow
    - Test CORS headers in response
    - Test with local DynamoDB (moto) and mocked Bedrock
    - _Requirements: 7.1, 7.3, 7.4_

- [x] 8. Create requirements.txt and dependencies
  - Add boto3 (AWS SDK)
  - Add aws-lambda-powertools[all] (logging, tracing, metrics)
  - Add hypothesis (property-based testing)
  - Add pytest, pytest-cov, moto (testing dependencies)
  - _Requirements: 1.3, 6.1, 6.2, 6.3_

- [ ] 9. Write property test for complete memo retrieval
  - [x] 9.1 Implement property test for memo retrieval and aggregation
    - **Property 1: Complete Memo Retrieval and Aggregation**
    - **Validates: Requirements 1.1, 1.2**
    - Use hypothesis to generate memo collections
    - Verify all memos retrieved from DynamoDB
    - Verify content included in aggregated text (within limits)

- [ ] 10. Final checkpoint and documentation
  - [x] 10.1 Create README for the feature
    - Document API endpoint usage with examples
    - Document environment variables
    - Document deployment instructions
    - Include example requests and responses
    - _Requirements: 7.1, 7.2_
  
  - [x] 10.2 Final testing checkpoint
    - Run all unit tests and verify 100% pass rate
    - Run all property-based tests with 100+ iterations each
    - Verify test coverage meets requirements
    - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use hypothesis library with minimum 100 iterations
- All code uses Python 3.13 with type hints
- AWS Lambda Powertools provides structured logging and metrics
- Bedrock model: us.anthropic.claude-sonnet-4-6 in us-west-2 region
- Maximum content limit: 180,000 tokens (approximately 720,000 characters)
