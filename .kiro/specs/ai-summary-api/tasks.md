# Implementation Plan: AI要約API

## Overview

This implementation plan breaks down the AI要約API into discrete coding tasks. The system is a serverless RESTful API built on AWS using Python 3.12 Lambda functions, DynamoDB for storage, and AWS Bedrock Claude for AI-powered question answering. The implementation follows AWS serverless best practices with comprehensive testing including both unit tests (pytest + moto) and property-based tests (Hypothesis).

## Tasks

- [x] 1. Set up project structure and SAM infrastructure
  - Create directory structure following AWS serverless conventions
  - Create SAM template (template.yaml) with DynamoDB table, Lambda functions, API Gateway, and IAM roles
  - Configure DynamoDB table with single-table design (PK, UpdatedAtIndex GSI)
  - Set up Python 3.12 runtime configuration for both Lambda functions
  - Create requirements.txt with boto3, aws-lambda-powertools, and testing dependencies
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 2. Implement core data models and validation
  - [x] 2.1 Create Memo data model class with validation
    - Implement Memo dataclass with id, title, content, created_at, updated_at fields
    - Add to_dict() and to_dynamodb_item() methods
    - Implement validation functions for title (1-200 chars) and content (1-50000 chars)
    - _Requirements: 1.2, 1.3, 4.2_

  - [x] 2.2 Write property test for title validation
    - **Property 1: Title Validation**
    - **Validates: Requirements 1.2, 4.2**

  - [x] 2.3 Write property test for content validation
    - **Property 2: Content Validation**
    - **Validates: Requirements 1.3, 4.2**

  - [x] 2.4 Write unit tests for Memo model
    - Test boundary values (1 char, 200 chars, 50000 chars)
    - Test special characters and Unicode handling
    - Test validation error messages
    - _Requirements: 1.2, 1.3_

- [ ] 3. Implement DynamoDB repository layer
  - [x] 3.1 Create DynamoDB repository class
    - Implement create_memo() with PutItem operation
    - Implement get_memo() with GetItem operation
    - Implement list_memos() with Query on UpdatedAtIndex GSI
    - Implement update_memo() with UpdateItem and conditional check
    - Implement delete_memo() with DeleteItem and conditional check
    - Handle pagination with LastEvaluatedKey/ExclusiveStartKey
    - _Requirements: 1.5, 2.1, 3.1, 4.1, 5.1_

  - [x] 3.2 Write unit tests for repository layer
    - Use moto to mock DynamoDB
    - Test all CRUD operations with specific examples
    - Test pagination with various page sizes
    - Test conditional check failures (404 scenarios)
    - _Requirements: 1.5, 2.1, 3.1, 4.1, 5.1_

- [ ] 4. Implement Memo Lambda function handler
  - [x] 4.1 Create Lambda handler with routing logic
    - Implement lambda_handler() with HTTP method/path routing
    - Route POST /memos to create_memo()
    - Route GET /memos/{id} to get_memo()
    - Route GET /memos to list_memos()
    - Route PUT /memos/{id} to update_memo()
    - Route DELETE /memos/{id} to delete_memo()
    - Set up aws-lambda-powertools Logger and Metrics
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

  - [x] 4.2 Implement create_memo operation
    - Parse request body and validate input
    - Generate UUID for memo ID
    - Set created_at and updated_at timestamps
    - Call repository to persist memo
    - Return 201 with created memo
    - _Requirements: 1.1, 1.5, 1.6_

  - [x] 4.3 Implement get_memo operation
    - Extract memo ID from path parameters
    - Call repository to retrieve memo
    - Return 200 with memo data or 404 if not found
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 4.4 Implement list_memos operation
    - Parse pagination query parameters (page_size, next_token)
    - Validate and cap page_size (default 20, max 100)
    - Call repository with pagination parameters
    - Return 200 with memos array and next_token
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 4.5 Implement update_memo operation
    - Extract memo ID and update data from request
    - Validate updated fields
    - Update updated_at timestamp
    - Call repository with conditional update
    - Return 200 with updated memo or 404 if not found
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 4.6 Implement delete_memo operation
    - Extract memo ID from path parameters
    - Call repository with conditional delete
    - Return 204 on success or 404 if not found
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 4.7 Implement error handling and logging
    - Add try-catch blocks for ValidationError, MemoNotFoundError, and generic exceptions
    - Implement error_response() helper function
    - Add structured logging for all operations with request_id, processing_time
    - Emit CloudWatch metrics for request count and processing time
    - _Requirements: 1.4, 8.1, 8.3_

  - [x] 4.8 Write property test for create-read round trip
    - **Property 5: Create-Read Round Trip**
    - **Validates: Requirements 1.1, 1.5, 1.6, 2.1**

  - [x] 4.9 Write property test for update-read round trip
    - **Property 6: Update-Read Round Trip with Timestamp Change**
    - **Validates: Requirements 4.1, 4.3, 4.4**

  - [x] 4.10 Write property test for delete-read verification
    - **Property 7: Delete-Read Verification**
    - **Validates: Requirements 5.1, 5.4**

  - [x] 4.11 Write property test for response structure completeness
    - **Property 8: Memo Response Structure Completeness**
    - **Validates: Requirements 1.6, 2.2, 4.4**

  - [x] 4.12 Write property test for list completeness
    - **Property 9: List Completeness**
    - **Validates: Requirements 3.1**

  - [x] 4.13 Write property test for list sorting order
    - **Property 10: List Sorting Order**
    - **Validates: Requirements 3.2**

  - [x] 4.14 Write property test for pagination page size enforcement
    - **Property 11: Pagination Page Size Enforcement**
    - **Validates: Requirements 3.3**

  - [x] 4.15 Write property test for pagination token navigation
    - **Property 12: Pagination Token Navigation**
    - **Validates: Requirements 3.4**

  - [x] 4.16 Write property test for non-existent ID returns 404
    - **Property 13: Non-Existent ID Returns 404**
    - **Validates: Requirements 2.3, 4.5, 5.3, 6.5**

  - [x] 4.17 Write property test for successful deletion status code
    - **Property 14: Successful Deletion Status Code**
    - **Validates: Requirements 5.2**

  - [x] 4.18 Write unit tests for Memo Lambda function
    - Test each operation with specific examples
    - Test edge cases (boundary values, special characters)
    - Test error conditions (malformed JSON, missing fields)
    - Test CloudWatch logging and metrics emission
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 8.1, 8.3_

- [x] 5. Checkpoint - Ensure memo CRUD operations work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement AI Lambda function with Bedrock integration
  - [x] 6.1 Create Bedrock client and prompt builder
    - Initialize boto3 Bedrock client with region configuration
    - Implement build_prompt() function to format memo content and question
    - Configure model parameters (max_tokens: 2000, temperature: 0.7, top_p: 0.9)
    - _Requirements: 6.3_

  - [x] 6.2 Implement Bedrock invocation with retry logic
    - Implement invoke_bedrock_with_retry() with exponential backoff
    - Retry on ThrottlingException and ServiceUnavailableException
    - Use retry delays: 1s, 2s, 4s (3 attempts total)
    - Parse Bedrock response and extract answer text
    - _Requirements: 6.6, 6.7_

  - [x] 6.3 Create AI Lambda handler
    - Implement lambda_handler() for POST /memos/{id}/ask
    - Extract memo_id and question from request
    - Validate question length (1-1000 chars)
    - Retrieve memo from DynamoDB using repository
    - Call Bedrock with memo content and question
    - Return answer with metadata (model_id, processing_time_ms, memo_id)
    - Set up aws-lambda-powertools Logger and Metrics
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 6.4 Implement AI function error handling
    - Handle MemoNotFoundError (return 404)
    - Handle ValidationError for question length (return 400)
    - Handle Bedrock service errors (return 503 after retries)
    - Add structured logging for AI requests with memo_id, question, processing_time
    - Emit CloudWatch metrics for AI request count and processing time
    - _Requirements: 6.5, 6.7, 8.2, 8.3, 8.4_

  - [x] 6.5 Write property test for question validation
    - **Property 3: Question Validation**
    - **Validates: Requirements 6.2**

  - [x] 6.6 Write property test for invalid input error response
    - **Property 4: Invalid Input Error Response**
    - **Validates: Requirements 1.4**

  - [x] 6.7 Write property test for AI answer response structure
    - **Property 15: AI Question Returns Answer with Metadata**
    - **Validates: Requirements 6.1, 6.3, 6.4**

  - [x] 6.8 Write unit tests for AI Lambda function
    - Mock Bedrock client with moto or custom mocks
    - Test successful AI question with specific example
    - Test question validation edge cases
    - Test memo not found scenario (404)
    - Test Bedrock retry logic with simulated failures
    - Test Bedrock service unavailable after retries (503)
    - Test logging and metrics emission
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 8.2, 8.3_

- [ ] 7. Configure API Gateway with request validation
  - [x] 7.1 Add API Gateway definition to SAM template
    - Define REST API with CORS configuration
    - Create resources and methods for all endpoints
    - Configure Lambda proxy integration for both functions
    - Set up CloudWatch logging (INFO level)
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_

  - [x] 7.2 Add request validation models to API Gateway
    - Create JSON Schema for CreateMemoRequest (title, content validation)
    - Create JSON Schema for UpdateMemoRequest (optional title, content)
    - Create JSON Schema for AIQuestionRequest (question validation)
    - Attach validators to POST /memos, PUT /memos/{id}, POST /memos/{id}/ask
    - _Requirements: 1.2, 1.3, 4.2, 6.2_

  - [x] 7.3 Configure API Gateway error responses
    - Set up 400 error response for validation failures
    - Set up 404 error response for not found
    - Set up 500/503 error responses for server errors
    - Ensure consistent error response format across all endpoints
    - _Requirements: 1.4, 2.3, 4.5, 5.3, 6.5, 6.7_

- [ ] 8. Finalize SAM template and deployment configuration
  - [x] 8.1 Complete Lambda function configurations in SAM template
    - Set Memo Function: 512MB memory, 10s timeout, environment variables
    - Set AI Function: 1024MB memory, 35s timeout, environment variables
    - Configure IAM roles with least privilege permissions
    - Add DynamoDB permissions to Memo Function (PutItem, GetItem, Query, UpdateItem, DeleteItem)
    - Add DynamoDB GetItem and Bedrock InvokeModel permissions to AI Function
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 8.2 Add CloudWatch monitoring configuration
    - Enable CloudWatch Logs for both Lambda functions
    - Set log retention period (e.g., 7 days)
    - Configure CloudWatch alarms for error rates and latency
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 8.3 Create deployment scripts
    - Create build script for sam build
    - Create deploy script for sam deploy with parameters
    - Add samconfig.toml with default deployment settings (region: us-west-2)
    - Document deployment commands in README
    - _Requirements: 7.1, 7.2_

- [ ] 9. Create integration tests for end-to-end flows
  - [x] 9.1 Write integration test for complete memo lifecycle
    - Test create → read → update → read → delete → read (404)
    - Verify timestamps change correctly on update
    - Use real AWS SDK calls against test environment
    - _Requirements: 1.1, 2.1, 4.1, 5.1_

  - [x] 9.2 Write integration test for pagination with large dataset
    - Create 50+ memos with different timestamps
    - Test pagination with various page sizes
    - Verify no duplicates or gaps in results
    - Verify sorting by updated_at descending
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 9.3 Write integration test for AI question answering
    - Create memo with specific content
    - Ask question about memo content
    - Verify answer structure and metadata
    - Test with non-existent memo ID (404)
    - _Requirements: 6.1, 6.3, 6.4, 6.5_

- [x] 10. Final checkpoint - Ensure all tests pass and system is ready for deployment
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties using Hypothesis (100+ iterations)
- Unit tests validate specific examples and edge cases using pytest + moto
- Integration tests verify end-to-end flows with real AWS services
- The implementation uses Python 3.12 runtime as specified in the design
- SAM template manages all infrastructure as code
- Both Lambda functions use aws-lambda-powertools for structured logging and metrics
- DynamoDB uses single-table design with GSI for efficient querying
- AI function includes retry logic with exponential backoff for Bedrock calls
