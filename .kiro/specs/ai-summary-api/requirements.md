# Requirements Document

## Introduction

AI要約APIは、AWS上でサーバーレスに稼働するRESTful APIサービスです。ユーザーがメモを作成・管理し、メモの内容についてAI（AWS Bedrock Claude Sonnet 4.6）に質問できる機能を提供します。このAPIは、Python 3.13ランタイムを使用したLambda関数で実装され、スケーラブルで費用対効果の高いサーバーレスアーキテクチャを活用します。

## Glossary

- **API_Gateway**: Amazon API Gatewayを使用したRESTful APIエンドポイント
- **Memo_Function**: メモのCRUD操作を実行するLambda関数（Python 3.13）
- **AI_Function**: AIへの質問処理を実行するLambda関数（Python 3.13）
- **Request_Validator**: APIリクエストの検証を行うコンポーネント
- **Memo_Store**: DynamoDBを使用したメモの永続化ストレージ
- **AI_Service**: AWS Bedrock Claude Sonnet 4.6（inference profile経由）を使用したAIサービス
- **Memo**: メモオブジェクト（ID、タイトル、内容、作成日時、更新日時を含む）
- **AI_Question**: AI質問リクエストオブジェクト（メモID、質問内容を含む）
- **AI_Answer**: AI回答オブジェクト（回答テキスト、メタデータを含む）

## Requirements

### Requirement 1: メモの作成

**User Story:** As a user, I want to create a new memo, so that I can store information for later reference

#### Acceptance Criteria

1. WHEN a valid Memo creation request is received, THE API_Gateway SHALL accept the request and return the created Memo within 200ms
2. THE Request_Validator SHALL validate that the memo title is between 1 and 200 characters
3. THE Request_Validator SHALL validate that the memo content is between 1 and 50000 characters
4. IF the input is invalid, THEN THE API_Gateway SHALL return a 400 error with a descriptive error message
5. WHEN a Memo is created, THE Memo_Store SHALL persist it with a unique ID, creation timestamp, and update timestamp
6. THE API_Gateway SHALL return the created Memo including its generated ID

### Requirement 2: メモの取得

**User Story:** As a user, I want to retrieve a specific memo by ID, so that I can view its content

#### Acceptance Criteria

1. WHEN a valid memo ID is provided, THE Memo_Function SHALL retrieve the Memo from Memo_Store within 100ms
2. THE API_Gateway SHALL return the Memo with all its fields (ID, title, content, creation timestamp, update timestamp)
3. IF the memo ID does not exist, THEN THE API_Gateway SHALL return a 404 error with a descriptive error message

### Requirement 3: メモの一覧取得

**User Story:** As a user, I want to retrieve a list of all my memos, so that I can browse my stored information

#### Acceptance Criteria

1. WHEN a list request is received, THE Memo_Function SHALL retrieve all Memo records from Memo_Store
2. THE API_Gateway SHALL return the list of Memo objects sorted by update timestamp in descending order
3. THE API_Gateway SHALL support pagination with configurable page size (default 20, maximum 100)
4. WHEN pagination parameters are provided, THE API_Gateway SHALL return the requested page with next page token if more results exist

### Requirement 4: メモの更新

**User Story:** As a user, I want to update an existing memo, so that I can modify its content

#### Acceptance Criteria

1. WHEN a valid update request is received with memo ID, THE Memo_Function SHALL update the Memo in Memo_Store within 200ms
2. THE Request_Validator SHALL validate that updated title and content meet the same criteria as creation
3. WHEN a Memo is updated, THE Memo_Store SHALL update the update timestamp to the current time
4. THE API_Gateway SHALL return the updated Memo with all current fields
5. IF the memo ID does not exist, THEN THE API_Gateway SHALL return a 404 error with a descriptive error message

### Requirement 5: メモの削除

**User Story:** As a user, I want to delete a memo, so that I can remove information I no longer need

#### Acceptance Criteria

1. WHEN a valid delete request is received with memo ID, THE Memo_Function SHALL delete the Memo from Memo_Store within 200ms
2. THE API_Gateway SHALL return a 204 status code on successful deletion
3. IF the memo ID does not exist, THEN THE API_Gateway SHALL return a 404 error with a descriptive error message
4. WHEN a Memo is deleted, THE Memo_Store SHALL permanently remove the record

### Requirement 6: AIへの質問

**User Story:** As a user, I want to ask questions about my memo content using AI, so that I can get insights and answers

#### Acceptance Criteria

1. WHEN a valid AI_Question is received with memo ID and question, THE AI_Function SHALL retrieve the Memo content and process the question within 30 seconds
2. THE Request_Validator SHALL validate that the question is between 1 and 1000 characters
3. THE AI_Function SHALL use AWS Bedrock Claude Sonnet 4.6 (via inference profile) to generate an answer based on the memo content and question
4. THE API_Gateway SHALL return an AI_Answer containing the response text and processing metadata
5. THE API_Gateway SHALL return responses with proper UTF-8 encoding to support Japanese and other Unicode characters
6. IF the memo ID does not exist, THEN THE API_Gateway SHALL return a 404 error with a descriptive error message
7. WHEN the AI_Service returns an error, THE AI_Function SHALL retry up to 3 times with exponential backoff
8. IF all retries fail, THEN THE AI_Function SHALL return a 503 error with a descriptive error message


### Requirement 7: Python 3.13ランタイム

**User Story:** As a developer, I want to use Python 3.13 for Lambda functions, so that I can leverage the latest Python features and performance improvements

#### Acceptance Criteria

1. THE Memo_Function SHALL use Python 3.13 runtime in AWS Lambda
2. THE AI_Function SHALL use Python 3.13 runtime in AWS Lambda
3. THE Lambda functions SHALL use boto3 for AWS SDK operations
4. THE Lambda functions SHALL use aws-lambda-powertools for structured logging and tracing

### Requirement 8: モニタリングとロギング

**User Story:** As a system administrator, I want to monitor API performance and errors, so that I can maintain service quality

#### Acceptance Criteria

1. THE Memo_Function SHALL log all requests with structured JSON format including request ID, processing time, and status
2. THE AI_Function SHALL log all AI requests with structured JSON format including memo ID, question, processing time, and status
3. THE Lambda functions SHALL emit CloudWatch metrics for request count, error count, and processing time
4. WHEN an error occurs, THE Lambda functions SHALL log the full error details and stack trace
