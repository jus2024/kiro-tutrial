# Requirements Document

## Introduction

全メモ要約機能は、既存のAI要約APIに追加される新機能です。この機能により、ユーザーは個別のメモではなく、システムに保存されている全てのメモを対象にAI（AWS Bedrock Claude Sonnet 4.6）による要約を生成できます。この機能は、大量のメモから重要な情報を抽出し、全体像を把握するために使用されます。

## Glossary

- **All_Memos_Summary_Function**: 全メモを取得し、AI要約を生成するLambda関数（Python 3.13）
- **Summary_Request**: 全メモ要約リクエストオブジェクト（オプションのフィルタ条件を含む）
- **Summary_Response**: AI生成の要約結果オブジェクト（要約テキスト、メタデータ、処理されたメモ数を含む）
- **Memo_Aggregator**: 複数のメモを集約し、AI処理用のコンテキストを構築するコンポーネント
- **Content_Limit**: AI処理のための最大コンテンツサイズ制限（トークン数またはバイト数）

## Requirements

### Requirement 1: 全メモ要約の生成

**User Story:** As a user, I want to generate an AI summary of all my memos, so that I can understand the overall themes and important information across all my notes

#### Acceptance Criteria

1. WHEN a valid Summary_Request is received, THE All_Memos_Summary_Function SHALL retrieve all Memo records from Memo_Store
2. THE All_Memos_Summary_Function SHALL aggregate the content of all retrieved memos
3. THE All_Memos_Summary_Function SHALL use AWS Bedrock Claude Sonnet 4.6 to generate a comprehensive summary within 60 seconds
4. THE API_Gateway SHALL return a Summary_Response containing the summary text, number of memos processed, and processing metadata
5. THE API_Gateway SHALL return responses with proper UTF-8 encoding to support Japanese and other Unicode characters

### Requirement 2: コンテンツサイズ制限の処理

**User Story:** As a system, I want to handle cases where total memo content exceeds AI model limits, so that the service remains reliable and functional

#### Acceptance Criteria

1. WHEN the total content size exceeds Content_Limit, THE Memo_Aggregator SHALL prioritize the most recently updated memos
2. THE Memo_Aggregator SHALL include as many complete memos as possible within Content_Limit
3. THE Summary_Response SHALL indicate the number of memos included in the summary
4. THE Summary_Response SHALL indicate the total number of memos available in the system

### Requirement 3: 空のメモリストの処理

**User Story:** As a user, I want to receive a clear message when I have no memos, so that I understand why no summary is generated

#### Acceptance Criteria

1. WHEN no Memo records exist in Memo_Store, THE All_Memos_Summary_Function SHALL return a 200 response with an informative message
2. THE Summary_Response SHALL indicate that zero memos were processed
3. THE API_Gateway SHALL not invoke AWS Bedrock when no memos exist

### Requirement 4: エラーハンドリングとリトライ

**User Story:** As a user, I want the system to handle temporary failures gracefully, so that I can successfully generate summaries even when services are temporarily unavailable

#### Acceptance Criteria

1. WHEN the AI_Service returns a retryable error, THE All_Memos_Summary_Function SHALL retry up to 3 times with exponential backoff
2. IF all retries fail, THEN THE All_Memos_Summary_Function SHALL return a 503 error with a descriptive error message
3. WHEN a DynamoDB error occurs, THE All_Memos_Summary_Function SHALL log the error and return a 500 error with a descriptive message
4. THE All_Memos_Summary_Function SHALL log all errors with structured JSON format including error type, message, and request ID

### Requirement 5: パフォーマンスとタイムアウト

**User Story:** As a user, I want the summary generation to complete in a reasonable time, so that I can use the feature efficiently

#### Acceptance Criteria

1. THE All_Memos_Summary_Function SHALL have a timeout of 65 seconds to accommodate AI processing time
2. WHEN processing takes longer than 60 seconds, THE All_Memos_Summary_Function SHALL return a 504 error
3. THE Summary_Response SHALL include the actual processing time in milliseconds

### Requirement 6: モニタリングとロギング

**User Story:** As a system administrator, I want to monitor summary generation performance and errors, so that I can maintain service quality

#### Acceptance Criteria

1. THE All_Memos_Summary_Function SHALL log all requests with structured JSON format including request ID, number of memos processed, processing time, and status
2. THE All_Memos_Summary_Function SHALL emit CloudWatch metrics for request count, error count, processing time, and number of memos processed
3. WHEN an error occurs, THE All_Memos_Summary_Function SHALL log the full error details and stack trace
4. THE All_Memos_Summary_Function SHALL use aws-lambda-powertools for structured logging and tracing

### Requirement 7: API エンドポイント

**User Story:** As a developer, I want a clear and consistent API endpoint for generating all-memos summaries, so that I can integrate this feature into client applications

#### Acceptance Criteria

1. THE API_Gateway SHALL expose a POST endpoint at /memos/summary
2. THE API_Gateway SHALL accept an empty request body or optional filter parameters
3. THE API_Gateway SHALL return a 200 status code with Summary_Response on success
4. THE API_Gateway SHALL support CORS for web client access
5. THE API_Gateway SHALL validate request format and return 400 for invalid requests
