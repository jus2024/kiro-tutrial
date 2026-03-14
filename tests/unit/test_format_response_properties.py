"""
Property-based tests for format_response method.

These tests validate universal correctness properties that should hold
across all valid inputs to the format_response method.
"""

import pytest
import json
from hypothesis import given, strategies as st
from src.utils.response_formatter import ResponseFormatter, ResponseFormat


class TestFormatResponseProperties:
    """Property-based tests for format_response method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResponseFormatter()
    
    # Strategy for generating valid summaries (non-empty strings)
    summary_strategy = st.text(min_size=1, max_size=500).filter(lambda s: s.strip())
    
    # Strategy for generating valid metadata
    metadata_strategy = st.fixed_dictionaries({
        "model_id": st.text(min_size=1, max_size=100),
        "processing_time_ms": st.integers(min_value=0, max_value=100000),
        "memos_included": st.integers(min_value=0, max_value=10000),
        "memos_total": st.integers(min_value=0, max_value=10000),
        "truncated": st.booleans()
    })
    
    # Strategy for Accept headers
    accept_header_strategy = st.one_of(
        st.none(),
        st.just("text/plain"),
        st.just("application/json"),
        st.just("*/*"),
        st.just("text/plain;q=0.9, application/json;q=0.8"),
        st.just("text/plain;q=0.7, application/json;q=0.9"),
        st.just("text/plain, application/json"),
        st.just("application/json, text/plain")
    )
    
    @given(
        summary=summary_strategy,
        metadata=metadata_strategy,
        accept_header=accept_header_strategy
    )
    def test_property_content_type_matches_accept_header(self, summary, metadata, accept_header):
        """
        Property 1: Content Type Matches Accept Header
        
        **Validates: Requirements 1.1, 1.2, 1.3, 5.1**
        
        For any valid summary, metadata, and Accept header, the response Content-Type 
        should match the format specified in the Accept header, with text/plain for 
        text requests, application/json for JSON requests or when no header is provided, 
        and proper charset=utf-8 encoding.
        """
        # Format response
        response = self.formatter.format_response(summary, metadata, accept_header)
        
        # Determine expected format
        expected_format = self.formatter.parse_accept_header(accept_header)
        
        # Verify Content-Type matches expected format
        if expected_format == ResponseFormat.TEXT:
            assert response.content_type == "text/plain; charset=utf-8", \
                f"Expected text/plain for Accept: {accept_header}"
            assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
        else:
            assert response.content_type == "application/json; charset=utf-8", \
                f"Expected application/json for Accept: {accept_header}"
            assert response.headers["Content-Type"] == "application/json; charset=utf-8"
        
        # Verify charset=utf-8 is always present
        assert "charset=utf-8" in response.content_type
        assert "charset=utf-8" in response.headers["Content-Type"]
    
    @given(
        summary=summary_strategy,
        metadata=metadata_strategy,
        accept_header=accept_header_strategy
    )
    def test_property_content_preservation(self, summary, metadata, accept_header):
        """
        Property 8: Content Preservation
        
        **Validates: Requirements 2.4, 3.2**
        
        For any valid summary, metadata, and Accept header, the summary content 
        should be included in the response regardless of the output format.
        """
        # Format response
        response = self.formatter.format_response(summary, metadata, accept_header)
        
        # Verify response has content
        assert response.content
        assert len(response.content) > 0
        
        # Verify summary is preserved in the response
        if response.content_type.startswith("text/plain"):
            # For text format, summary should appear directly
            assert summary in response.content, \
                "Summary content not found in text response"
        else:
            # For JSON format, summary should be in the "summary" field
            parsed = json.loads(response.content)
            assert "summary" in parsed
            assert parsed["summary"] == summary, \
                "Summary content not preserved in JSON response"
    
    @given(
        metadata=metadata_strategy,
        accept_header=accept_header_strategy
    )
    def test_property_utf8_character_preservation(self, metadata, accept_header):
        """
        Property 9: UTF-8 Character Preservation
        
        **Validates: Requirements 5.2, 5.3, 5.4**
        
        For any summary containing Japanese characters, emoji, or other Unicode 
        characters, these characters should be correctly preserved in both text 
        and JSON formats.
        """
        # Strategy for Unicode-rich summaries
        unicode_summaries = [
            "📝 日本語のテキスト\n\n🎉 絵文字も含む",
            "こんにちは世界！\n\nテストメッセージです。",
            "🚀 プロジェクト開始\n\n✅ タスク完了",
            "漢字、ひらがな、カタカナ\n\n全て含みます。",
            "Emoji: 😀😃😄😁\n\nJapanese: 日本語"
        ]
        
        for summary in unicode_summaries:
            # Format response
            response = self.formatter.format_response(summary, metadata, accept_header)
            
            # Verify Unicode characters are preserved
            if response.content_type.startswith("text/plain"):
                # Text format: check direct presence
                assert summary in response.content, \
                    f"Unicode summary not preserved in text format: {summary}"
                
                # Check specific Unicode characters
                if "📝" in summary:
                    assert "📝" in response.content
                if "日本語" in summary:
                    assert "日本語" in response.content
                if "🎉" in summary:
                    assert "🎉" in response.content
            else:
                # JSON format: parse and check
                parsed = json.loads(response.content)
                assert parsed["summary"] == summary, \
                    f"Unicode summary not preserved in JSON format: {summary}"
                
                # Check specific Unicode characters in parsed JSON
                if "📝" in summary:
                    assert "📝" in parsed["summary"]
                if "日本語" in summary:
                    assert "日本語" in parsed["summary"]
                if "🎉" in summary:
                    assert "🎉" in parsed["summary"]
    
    @given(
        summary=summary_strategy,
        metadata=metadata_strategy,
        accept_header=accept_header_strategy
    )
    def test_property_cors_headers_presence(self, summary, metadata, accept_header):
        """
        Property 10: CORS Headers Presence
        
        **Validates: Requirements 6.1, 6.2, 6.3**
        
        For any valid summary, metadata, and Accept header, the response should 
        include all required CORS headers: Access-Control-Allow-Origin with value "*", 
        Access-Control-Allow-Methods with value "POST, OPTIONS", and 
        Access-Control-Allow-Headers with value "Content-Type, Accept".
        """
        # Format response
        response = self.formatter.format_response(summary, metadata, accept_header)
        
        # Verify all required CORS headers are present
        assert "Access-Control-Allow-Origin" in response.headers, \
            "Missing Access-Control-Allow-Origin header"
        assert "Access-Control-Allow-Methods" in response.headers, \
            "Missing Access-Control-Allow-Methods header"
        assert "Access-Control-Allow-Headers" in response.headers, \
            "Missing Access-Control-Allow-Headers header"
        
        # Verify CORS header values
        assert response.headers["Access-Control-Allow-Origin"] == "*", \
            f"Expected '*' for Access-Control-Allow-Origin, got {response.headers['Access-Control-Allow-Origin']}"
        assert response.headers["Access-Control-Allow-Methods"] == "POST, OPTIONS", \
            f"Expected 'POST, OPTIONS' for Access-Control-Allow-Methods, got {response.headers['Access-Control-Allow-Methods']}"
        assert response.headers["Access-Control-Allow-Headers"] == "Content-Type, Accept", \
            f"Expected 'Content-Type, Accept' for Access-Control-Allow-Headers, got {response.headers['Access-Control-Allow-Headers']}"
    
    @given(
        summary=summary_strategy,
        metadata=metadata_strategy,
        accept_header=accept_header_strategy
    )
    def test_property_metadata_completeness(self, summary, metadata, accept_header):
        """
        Property 7: Metadata Completeness
        
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        
        For any valid summary and metadata, the response should include all metadata 
        fields: model_id, processing_time_ms, memos_included, memos_total, and 
        truncated flag.
        """
        # Format response
        response = self.formatter.format_response(summary, metadata, accept_header)
        
        # Required metadata fields
        required_fields = ["model_id", "processing_time_ms", "memos_included", "memos_total", "truncated"]
        
        if response.content_type.startswith("text/plain"):
            # Text format: check for metadata labels
            assert "• モデル:" in response.content, "Missing model_id in text format"
            assert "• 処理時間:" in response.content, "Missing processing_time_ms in text format"
            assert "• 要約対象:" in response.content, "Missing memos count in text format"
            assert "• 切り詰め:" in response.content, "Missing truncated flag in text format"
            
            # Verify actual values are present
            assert str(metadata["model_id"]) in response.content or "N/A" in response.content
            assert f"{metadata['memos_included']}/{metadata['memos_total']}件のメモ" in response.content
            
            truncated_text = "あり" if metadata["truncated"] else "なし"
            assert truncated_text in response.content
            
            # Processing time: either formatted time or "N/A"
            if metadata["processing_time_ms"] > 0:
                processing_time_sec = metadata["processing_time_ms"] / 1000.0
                expected_time = f"{processing_time_sec:.2f}秒"
                assert expected_time in response.content
            else:
                assert "N/A" in response.content
        else:
            # JSON format: parse and check all fields
            parsed = json.loads(response.content)
            assert "metadata" in parsed, "Missing metadata field in JSON"
            
            for field in required_fields:
                assert field in parsed["metadata"], \
                    f"Missing required field '{field}' in JSON metadata"
                assert parsed["metadata"][field] == metadata[field], \
                    f"Metadata field '{field}' value mismatch"
    
    @given(
        summary=summary_strategy,
        metadata=metadata_strategy,
        accept_header=accept_header_strategy
    )
    def test_property_response_structure_completeness(self, summary, metadata, accept_header):
        """
        Property 13: Response Structure Completeness
        
        **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
        
        For any valid summary, metadata, and Accept header, the response object 
        should include all required fields: non-empty content, valid content_type, 
        valid status_code, and headers dictionary.
        """
        # Format response
        response = self.formatter.format_response(summary, metadata, accept_header)
        
        # Verify response has all required fields
        assert hasattr(response, "content"), "Response missing 'content' field"
        assert hasattr(response, "content_type"), "Response missing 'content_type' field"
        assert hasattr(response, "status_code"), "Response missing 'status_code' field"
        assert hasattr(response, "headers"), "Response missing 'headers' field"
        
        # Verify content is non-empty
        assert response.content, "Response content is empty"
        assert len(response.content) > 0, "Response content has zero length"
        assert isinstance(response.content, str), "Response content is not a string"
        
        # Verify content_type is valid
        assert response.content_type, "Response content_type is empty"
        assert isinstance(response.content_type, str), "Response content_type is not a string"
        assert response.content_type in [
            "text/plain; charset=utf-8",
            "application/json; charset=utf-8"
        ], f"Invalid content_type: {response.content_type}"
        
        # Verify status_code is valid
        assert response.status_code == 200, f"Expected status_code 200, got {response.status_code}"
        assert isinstance(response.status_code, int), "Response status_code is not an integer"
        
        # Verify headers is a dictionary
        assert isinstance(response.headers, dict), "Response headers is not a dictionary"
        assert len(response.headers) > 0, "Response headers dictionary is empty"
        
        # Verify Content-Type header is present and matches content_type
        assert "Content-Type" in response.headers, "Missing Content-Type in headers"
        assert response.headers["Content-Type"] == response.content_type, \
            "Content-Type header doesn't match content_type field"
    
    @given(
        summary=summary_strategy,
        metadata=metadata_strategy,
        accept_header=accept_header_strategy
    )
    def test_property_input_immutability(self, summary, metadata, accept_header):
        """
        Property 14: Input Immutability
        
        **Validates: Requirements 8.5**
        
        For any valid summary, metadata, and Accept header, calling format_response 
        should not mutate any of the input parameters.
        """
        # Create copies of inputs for comparison
        original_summary = summary
        original_metadata = metadata.copy()
        original_accept_header = accept_header
        
        # Format response
        response = self.formatter.format_response(summary, metadata, accept_header)
        
        # Verify inputs are unchanged
        assert summary == original_summary, "Summary was mutated"
        assert metadata == original_metadata, "Metadata was mutated"
        assert accept_header == original_accept_header, "Accept header was mutated"
        
        # Verify metadata dictionary contents are unchanged
        for key, value in original_metadata.items():
            assert key in metadata, f"Metadata key '{key}' was removed"
            assert metadata[key] == value, f"Metadata value for '{key}' was changed"
        
        # Verify no new keys were added to metadata
        assert len(metadata) == len(original_metadata), "Metadata dictionary size changed"
