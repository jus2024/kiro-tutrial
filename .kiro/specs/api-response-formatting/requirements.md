# Requirements Document: API Response Formatting

## Introduction

現在のメモ要約API（`/memos/summary`エンドポイント）は、生のJSON形式でレスポンスを返すため、ターミナルで直接確認する際に読みにくいという課題があります。この機能は、クライアントがAcceptヘッダーを使用してレスポンス形式を指定できるようにし、人間が読みやすいテキスト形式と機械処理向けのJSON形式の両方をサポートします。

## Glossary

- **API**: メモ要約サービスのRESTful API
- **ResponseFormatter**: レスポンスフォーマット処理を担当するユーティリティクラス
- **Accept_Header**: クライアントが希望するレスポンス形式を指定するHTTPヘッダー
- **Text_Format**: 人間が読みやすい形式のテキストレスポンス（text/plain）
- **JSON_Format**: 機械処理向けの構造化データレスポンス（application/json）
- **Summary_Content**: AI生成されたメモの要約テキスト
- **Metadata**: 処理時間、メモ数、モデルIDなどの処理情報
- **Client**: APIを呼び出すアプリケーションまたはユーザー

## Requirements

### Requirement 1: Content Negotiation Support

**User Story:** As a client application, I want to specify my preferred response format using the Accept header, so that I can receive data in the most suitable format for my use case.

#### Acceptance Criteria

1. WHEN a Client sends a request with Accept header "text/plain", THEN THE API SHALL return a response with Content-Type "text/plain; charset=utf-8"
2. WHEN a Client sends a request with Accept header "application/json", THEN THE API SHALL return a response with Content-Type "application/json; charset=utf-8"
3. WHEN a Client sends a request without an Accept header, THEN THE API SHALL return a response with Content-Type "application/json; charset=utf-8"
4. WHEN a Client sends a request with Accept header containing quality values, THEN THE API SHALL select the format with the highest quality value
5. WHEN a Client sends a request with Accept header "*/*", THEN THE API SHALL return a response with Content-Type "application/json; charset=utf-8"

### Requirement 2: Human-Readable Text Format

**User Story:** As a developer using the API from a terminal, I want to receive responses in a human-readable text format, so that I can quickly understand the summary without additional formatting tools.

#### Acceptance Criteria

1. WHEN THE ResponseFormatter formats a response as text, THEN THE API SHALL include visual separators using "=" and "-" characters
2. WHEN THE ResponseFormatter formats a response as text, THEN THE API SHALL include emoji icons (📝, 📊, 📄) for visual clarity
3. WHEN THE ResponseFormatter formats a response as text, THEN THE API SHALL display metadata in a labeled list format with bullet points
4. WHEN THE ResponseFormatter formats a response as text, THEN THE API SHALL display the Summary_Content in a clearly separated section
5. WHEN THE ResponseFormatter formats a response as text, THEN THE API SHALL format processing time in seconds with two decimal places

### Requirement 3: Backward Compatibility

**User Story:** As an existing API client, I want the default response format to remain JSON, so that my application continues to work without modifications.

#### Acceptance Criteria

1. WHEN a Client sends a request without specifying an Accept header, THEN THE API SHALL return JSON_Format
2. WHEN THE API returns JSON_Format, THEN THE response body SHALL contain a "summary" field with the Summary_Content
3. WHEN THE API returns JSON_Format, THEN THE response body SHALL contain a "metadata" field with all processing information
4. THE API SHALL maintain the existing JSON structure for all metadata fields (model_id, processing_time_ms, memos_included, memos_total, truncated)

### Requirement 4: Metadata Presentation

**User Story:** As a user, I want to see processing information alongside the summary, so that I can understand how the summary was generated and verify its completeness.

#### Acceptance Criteria

1. WHEN THE API returns a response, THEN THE response SHALL include the model_id used for generation
2. WHEN THE API returns a response, THEN THE response SHALL include the processing_time_ms
3. WHEN THE API returns a response, THEN THE response SHALL include the number of memos_included in the summary
4. WHEN THE API returns a response, THEN THE response SHALL include the total number of memos_total available
5. WHEN THE API returns a response, THEN THE response SHALL include a truncated flag indicating whether content was truncated
6. WHEN THE ResponseFormatter formats Metadata as text AND processing_time_ms is greater than zero, THEN THE API SHALL display processing time in seconds
7. WHEN THE ResponseFormatter formats Metadata as text AND processing_time_ms is zero or negative, THEN THE API SHALL display "N/A" for processing time

### Requirement 5: Character Encoding

**User Story:** As a user working with Japanese text and emoji, I want all responses to use UTF-8 encoding, so that special characters display correctly.

#### Acceptance Criteria

1. THE API SHALL set the charset parameter to "utf-8" in the Content-Type header for all responses
2. WHEN THE API returns Text_Format, THEN THE response SHALL correctly encode Japanese characters
3. WHEN THE API returns Text_Format, THEN THE response SHALL correctly encode emoji characters
4. WHEN THE API returns JSON_Format, THEN THE response SHALL correctly encode Unicode characters

### Requirement 6: CORS Support

**User Story:** As a web application developer, I want the API to include proper CORS headers, so that my browser-based application can access the API.

#### Acceptance Criteria

1. THE API SHALL include the "Access-Control-Allow-Origin" header with value "*" in all responses
2. THE API SHALL include the "Access-Control-Allow-Methods" header with value "POST, OPTIONS" in all responses
3. THE API SHALL include the "Access-Control-Allow-Headers" header with value "Content-Type, Accept" in all responses

### Requirement 7: Accept Header Parsing

**User Story:** As a client application, I want the API to correctly parse complex Accept headers with multiple media types and quality values, so that I can express my format preferences accurately.

#### Acceptance Criteria

1. WHEN a Client sends an Accept header with multiple media types separated by commas, THEN THE ResponseFormatter SHALL parse each media type
2. WHEN a Client sends an Accept header with quality values (q=), THEN THE ResponseFormatter SHALL extract and respect the quality values
3. WHEN a Client sends an Accept header with multiple media types, THEN THE ResponseFormatter SHALL select the format with the highest quality value
4. WHEN a Client sends an Accept header with invalid or malformed content, THEN THE ResponseFormatter SHALL default to JSON_Format
5. WHEN a Client sends an Accept header with whitespace around media types, THEN THE ResponseFormatter SHALL trim whitespace before processing

### Requirement 8: Response Structure Integrity

**User Story:** As a system architect, I want to ensure that all response components are properly structured, so that the system maintains data integrity and reliability.

#### Acceptance Criteria

1. WHEN THE ResponseFormatter creates a response, THEN THE response SHALL include a valid status_code
2. WHEN THE ResponseFormatter creates a response, THEN THE response SHALL include a non-empty content field
3. WHEN THE ResponseFormatter creates a response, THEN THE response SHALL include a valid content_type field
4. WHEN THE ResponseFormatter creates a response, THEN THE response SHALL include a headers dictionary
5. THE ResponseFormatter SHALL NOT mutate input parameters (summary, metadata, accept_header)

### Requirement 9: Error Handling

**User Story:** As a developer, I want the API to handle edge cases gracefully, so that the system remains stable even with unexpected inputs.

#### Acceptance Criteria

1. WHEN THE ResponseFormatter receives an empty summary string, THEN THE API SHALL handle it according to validation rules
2. WHEN THE ResponseFormatter receives metadata missing required keys, THEN THE API SHALL handle it according to validation rules
3. WHEN THE ResponseFormatter receives a None Accept_Header, THEN THE API SHALL default to JSON_Format
4. WHEN THE ResponseFormatter receives an empty Accept_Header string, THEN THE API SHALL default to JSON_Format
5. WHEN THE ResponseFormatter encounters an unsupported media type in Accept_Header, THEN THE API SHALL default to JSON_Format
