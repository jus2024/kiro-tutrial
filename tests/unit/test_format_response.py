"""
Unit tests for format_response method.

Tests the main format_response method that orchestrates the response formatting.
"""

import pytest
import json
from src.utils.response_formatter import ResponseFormatter, ResponseFormat


class TestFormatResponse:
    """Tests for format_response method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResponseFormatter()
        self.valid_summary = "## メモの包括的な要約\n\n業務タスクの要約..."
        self.valid_metadata = {
            "model_id": "us.anthropic.claude-sonnet-4-6",
            "processing_time_ms": 11263,
            "memos_included": 3,
            "memos_total": 3,
            "truncated": False
        }
    
    def test_format_response_with_text_plain_accept_header(self):
        """Test format_response with text/plain Accept header."""
        response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="text/plain"
        )
        
        # Verify response structure
        assert response.status_code == 200
        assert response.content_type == "text/plain; charset=utf-8"
        assert isinstance(response.content, str)
        assert len(response.content) > 0
        
        # Verify content is text format
        assert "📝 メモ要約結果" in response.content
        assert "📊 処理情報:" in response.content
        assert "📄 要約内容:" in response.content
        assert self.valid_summary in response.content
        
        # Verify headers
        assert "Content-Type" in response.headers
        assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert response.headers["Access-Control-Allow-Methods"] == "POST, OPTIONS"
        assert response.headers["Access-Control-Allow-Headers"] == "Content-Type, Accept"
    
    def test_format_response_with_application_json_accept_header(self):
        """Test format_response with application/json Accept header."""
        response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="application/json"
        )
        
        # Verify response structure
        assert response.status_code == 200
        assert response.content_type == "application/json; charset=utf-8"
        assert isinstance(response.content, str)
        assert len(response.content) > 0
        
        # Verify content is JSON format
        parsed = json.loads(response.content)
        assert "summary" in parsed
        assert "metadata" in parsed
        assert parsed["summary"] == self.valid_summary
        
        # Verify headers
        assert "Content-Type" in response.headers
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert response.headers["Access-Control-Allow-Methods"] == "POST, OPTIONS"
        assert response.headers["Access-Control-Allow-Headers"] == "Content-Type, Accept"
    
    def test_format_response_with_none_accept_header_defaults_to_json(self):
        """Test format_response with None Accept header defaults to JSON."""
        response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header=None
        )
        
        # Verify response defaults to JSON
        assert response.status_code == 200
        assert response.content_type == "application/json; charset=utf-8"
        
        # Verify content is JSON format
        parsed = json.loads(response.content)
        assert "summary" in parsed
        assert "metadata" in parsed
    
    def test_format_response_with_wildcard_accept_header(self):
        """Test format_response with wildcard Accept header."""
        response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="*/*"
        )
        
        # Verify response defaults to JSON for wildcard
        assert response.status_code == 200
        assert response.content_type == "application/json; charset=utf-8"
        
        # Verify content is JSON format
        parsed = json.loads(response.content)
        assert "summary" in parsed
        assert "metadata" in parsed
    
    def test_format_response_cors_headers_present(self):
        """Test that CORS headers are present in all responses."""
        # Test with text format
        text_response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="text/plain"
        )
        
        assert text_response.headers["Access-Control-Allow-Origin"] == "*"
        assert text_response.headers["Access-Control-Allow-Methods"] == "POST, OPTIONS"
        assert text_response.headers["Access-Control-Allow-Headers"] == "Content-Type, Accept"
        
        # Test with JSON format
        json_response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="application/json"
        )
        
        assert json_response.headers["Access-Control-Allow-Origin"] == "*"
        assert json_response.headers["Access-Control-Allow-Methods"] == "POST, OPTIONS"
        assert json_response.headers["Access-Control-Allow-Headers"] == "Content-Type, Accept"
    
    def test_format_response_with_quality_values(self):
        """Test format_response with quality values in Accept header."""
        # Text has higher quality
        response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="text/plain;q=0.9, application/json;q=0.8"
        )
        
        assert response.content_type == "text/plain; charset=utf-8"
        assert "📝 メモ要約結果" in response.content
        
        # JSON has higher quality
        response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="text/plain;q=0.7, application/json;q=0.9"
        )
        
        assert response.content_type == "application/json; charset=utf-8"
        parsed = json.loads(response.content)
        assert "summary" in parsed
    
    def test_format_response_with_empty_summary_raises_error(self):
        """Test that empty summary raises ValueError."""
        with pytest.raises(ValueError, match="Summary cannot be empty"):
            self.formatter.format_response("", self.valid_metadata, accept_header="text/plain")
    
    def test_format_response_with_missing_metadata_raises_error(self):
        """Test that missing metadata keys raise ValueError."""
        incomplete_metadata = {
            "model_id": "test-model",
            "processing_time_ms": 1000
            # Missing: memos_included, memos_total, truncated
        }
        
        with pytest.raises(ValueError, match="Metadata missing required keys"):
            self.formatter.format_response(
                self.valid_summary,
                incomplete_metadata,
                accept_header="text/plain"
            )
    
    def test_format_response_content_type_header_matches_format(self):
        """Test that Content-Type header matches the selected format."""
        # Text format
        text_response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="text/plain"
        )
        
        assert text_response.content_type == "text/plain; charset=utf-8"
        assert text_response.headers["Content-Type"] == "text/plain; charset=utf-8"
        
        # JSON format
        json_response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="application/json"
        )
        
        assert json_response.content_type == "application/json; charset=utf-8"
        assert json_response.headers["Content-Type"] == "application/json; charset=utf-8"
    
    def test_format_response_status_code_is_200(self):
        """Test that status code is always 200 for successful responses."""
        # Text format
        text_response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="text/plain"
        )
        
        assert text_response.status_code == 200
        
        # JSON format
        json_response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="application/json"
        )
        
        assert json_response.status_code == 200
    
    def test_format_response_does_not_mutate_inputs(self):
        """Test that format_response does not mutate input parameters."""
        original_summary = self.valid_summary
        original_metadata = self.valid_metadata.copy()
        original_accept_header = "text/plain"
        
        response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header=original_accept_header
        )
        
        # Verify inputs are unchanged
        assert self.valid_summary == original_summary
        assert self.valid_metadata == original_metadata
    
    def test_format_response_with_unicode_characters(self):
        """Test format_response preserves Unicode characters in both formats."""
        unicode_summary = "📝 日本語のテキスト\n\n🎉 絵文字も含む"
        
        # Test text format
        text_response = self.formatter.format_response(
            unicode_summary,
            self.valid_metadata,
            accept_header="text/plain"
        )
        
        assert "📝 日本語のテキスト" in text_response.content
        assert "🎉 絵文字も含む" in text_response.content
        
        # Test JSON format
        json_response = self.formatter.format_response(
            unicode_summary,
            self.valid_metadata,
            accept_header="application/json"
        )
        
        parsed = json.loads(json_response.content)
        assert parsed["summary"] == unicode_summary
        assert "📝" in parsed["summary"]
        assert "🎉" in parsed["summary"]
    
    def test_format_response_headers_is_dict(self):
        """Test that response headers is a dictionary."""
        response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="text/plain"
        )
        
        assert isinstance(response.headers, dict)
        assert len(response.headers) >= 4  # At least Content-Type and 3 CORS headers
    
    def test_format_response_content_is_non_empty(self):
        """Test that response content is always non-empty."""
        # Text format
        text_response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="text/plain"
        )
        
        assert text_response.content
        assert len(text_response.content) > 0
        
        # JSON format
        json_response = self.formatter.format_response(
            self.valid_summary,
            self.valid_metadata,
            accept_header="application/json"
        )
        
        assert json_response.content
        assert len(json_response.content) > 0
