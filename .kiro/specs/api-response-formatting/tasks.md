# Implementation Plan: API Response Formatting

## Overview

This implementation adds content negotiation support to the `/memos/summary` API endpoint, allowing clients to request either human-readable text format or JSON format via the Accept header. The implementation creates a ResponseFormatter utility class that handles format detection, content formatting, and response construction while maintaining backward compatibility with existing JSON clients.

## Tasks

- [x] 1. Set up project structure and core interfaces
  - Create `src/utils/response_formatter.py` module
  - Define ResponseFormat enum (JSON, TEXT)
  - Define FormattedResponse dataclass with content, content_type, status_code, and headers fields
  - Add pytest and hypothesis to requirements if not already present
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 2. Implement Accept header parsing
  - [x] 2.1 Implement parse_accept_header() method
    - Parse comma-separated media types from Accept header
    - Extract quality values (q=) from media type parameters
    - Sort media types by quality value (descending)
    - Return ResponseFormat.TEXT for "text/plain", ResponseFormat.JSON for "application/json" or "*/*"
    - Default to ResponseFormat.JSON for None, empty, or unsupported media types
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.1, 7.2, 7.3, 7.4, 7.5, 9.3, 9.4, 9.5_
  
  - [x] 2.2 Write property test for Accept header parsing
    - **Property 11: Accept Header Parsing**
    - **Validates: Requirements 7.1, 7.5**
  
  - [x] 2.3 Write property test for quality value selection
    - **Property 2: Quality Value Selection**
    - **Validates: Requirements 1.4, 7.2, 7.3**
  
  - [x] 2.4 Write property test for wildcard and default handling
    - **Property 3: Wildcard and Default Handling**
    - **Validates: Requirements 1.5, 9.3, 9.4, 9.5**
  
  - [x] 2.5 Write property test for malformed header handling
    - **Property 12: Malformed Header Handling**
    - **Validates: Requirements 7.4**

- [x] 3. Implement JSON formatting
  - [x] 3.1 Implement format_as_json() method
    - Create JSON structure with "summary" and "metadata" fields
    - Preserve all metadata fields: model_id, processing_time_ms, memos_included, memos_total, truncated
    - Return JSON string with proper encoding
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [x] 3.2 Write property test for JSON structure preservation
    - **Property 6: JSON Structure Preservation**
    - **Validates: Requirements 3.2, 3.3, 3.4**
  
  - [x] 3.3 Write unit tests for JSON formatting
    - Test with valid summary and metadata
    - Test JSON structure and field presence
    - Test Unicode character encoding
    - _Requirements: 3.2, 3.3, 3.4, 5.4_

- [x] 4. Implement text formatting
  - [x] 4.1 Implement format_as_text() method
    - Add header section with "=" separators and 📝 emoji
    - Add metadata section with 📊 emoji and bullet points
    - Format processing time in seconds with two decimal places (or "N/A" if <= 0)
    - Display memos_included/memos_total count
    - Display model_id and truncated flag
    - Add summary content section with 📄 emoji and "-" separator
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  
  - [x] 4.2 Write property test for text format visual elements
    - **Property 4: Text Format Visual Elements**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
  
  - [x] 4.3 Write property test for processing time formatting
    - **Property 5: Processing Time Formatting**
    - **Validates: Requirements 2.5, 4.6**
  
  - [x] 4.4 Write unit tests for text formatting
    - Test with valid summary and metadata
    - Test visual separators and emoji presence
    - Test metadata display format
    - Test Japanese character encoding
    - Test processing time formatting (positive, zero, negative values)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.2, 5.3_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement main format_response() method
  - [x] 6.1 Implement format_response() method
    - Call parse_accept_header() to determine format
    - Call format_as_text() or format_as_json() based on format
    - Set appropriate Content-Type header with charset=utf-8
    - Add CORS headers: Access-Control-Allow-Origin, Access-Control-Allow-Methods, Access-Control-Allow-Headers
    - Create and return FormattedResponse object with status_code 200
    - _Requirements: 1.1, 1.2, 1.3, 5.1, 6.1, 6.2, 6.3, 8.1, 8.2, 8.3, 8.4_
  
  - [x] 6.2 Write property test for content type matching
    - **Property 1: Content Type Matches Accept Header**
    - **Validates: Requirements 1.1, 1.2, 1.3, 5.1**
  
  - [x] 6.3 Write property test for content preservation
    - **Property 8: Content Preservation**
    - **Validates: Requirements 2.4, 3.2**
  
  - [x] 6.4 Write property test for UTF-8 character preservation
    - **Property 9: UTF-8 Character Preservation**
    - **Validates: Requirements 5.2, 5.3, 5.4**
  
  - [x] 6.5 Write property test for CORS headers presence
    - **Property 10: CORS Headers Presence**
    - **Validates: Requirements 6.1, 6.2, 6.3**
  
  - [x] 6.6 Write property test for metadata completeness
    - **Property 7: Metadata Completeness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
  
  - [x] 6.7 Write property test for response structure completeness
    - **Property 13: Response Structure Completeness**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
  
  - [x] 6.8 Write property test for input immutability
    - **Property 14: Input Immutability**
    - **Validates: Requirements 8.5**
  
  - [x] 6.9 Write unit tests for format_response()
    - Test with text/plain Accept header
    - Test with application/json Accept header
    - Test with None Accept header (default to JSON)
    - Test with wildcard Accept header
    - Test CORS headers presence
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 6.1, 6.2, 6.3_

- [x] 7. Integrate ResponseFormatter with Lambda handler
  - [x] 7.1 Update AllMemosSummaryFunction Lambda handler
    - Import ResponseFormatter from utils.response_formatter
    - Extract Accept header from event["headers"]
    - Replace existing response construction with formatter.format_response()
    - Return formatted response with statusCode, headers, and body
    - _Requirements: 1.1, 1.2, 1.3, 3.1_
  
  - [x] 7.2 Write integration tests for Lambda handler
    - Test POST request with Accept: text/plain header
    - Test POST request with Accept: application/json header
    - Test POST request without Accept header
    - Verify response format matches Accept header
    - Verify backward compatibility with existing clients
    - _Requirements: 1.1, 1.2, 1.3, 3.1_

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end functionality with the Lambda handler
- The implementation maintains backward compatibility by defaulting to JSON format
