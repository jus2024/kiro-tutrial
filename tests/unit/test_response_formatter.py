"""
Unit tests for ResponseFormatter.
"""

import pytest
from src.utils.response_formatter import ResponseFormatter, ResponseFormat


class TestParseAcceptHeader:
    """Tests for parse_accept_header method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResponseFormatter()
    
    def test_none_header_defaults_to_json(self):
        """Test that None Accept header defaults to JSON."""
        result = self.formatter.parse_accept_header(None)
        assert result == ResponseFormat.JSON
    
    def test_empty_header_defaults_to_json(self):
        """Test that empty Accept header defaults to JSON."""
        result = self.formatter.parse_accept_header("")
        assert result == ResponseFormat.JSON
    
    def test_whitespace_header_defaults_to_json(self):
        """Test that whitespace-only Accept header defaults to JSON."""
        result = self.formatter.parse_accept_header("   ")
        assert result == ResponseFormat.JSON
    
    def test_text_plain_returns_text(self):
        """Test that text/plain Accept header returns TEXT format."""
        result = self.formatter.parse_accept_header("text/plain")
        assert result == ResponseFormat.TEXT
    
    def test_application_json_returns_json(self):
        """Test that application/json Accept header returns JSON format."""
        result = self.formatter.parse_accept_header("application/json")
        assert result == ResponseFormat.JSON
    
    def test_wildcard_returns_json(self):
        """Test that */* Accept header returns JSON format."""
        result = self.formatter.parse_accept_header("*/*")
        assert result == ResponseFormat.JSON
    
    def test_unsupported_media_type_defaults_to_json(self):
        """Test that unsupported media types default to JSON."""
        result = self.formatter.parse_accept_header("text/html")
        assert result == ResponseFormat.JSON
    
    def test_quality_value_selection_text_higher(self):
        """Test that higher quality value is selected (text/plain preferred)."""
        result = self.formatter.parse_accept_header("text/plain;q=0.9, application/json;q=0.8")
        assert result == ResponseFormat.TEXT
    
    def test_quality_value_selection_json_higher(self):
        """Test that higher quality value is selected (JSON preferred)."""
        result = self.formatter.parse_accept_header("text/plain;q=0.7, application/json;q=0.9")
        assert result == ResponseFormat.JSON
    
    def test_quality_value_default_1_0(self):
        """Test that media types without quality value default to 1.0."""
        result = self.formatter.parse_accept_header("text/plain, application/json;q=0.8")
        assert result == ResponseFormat.TEXT
    
    def test_multiple_media_types_with_whitespace(self):
        """Test parsing with whitespace around media types."""
        result = self.formatter.parse_accept_header(" text/plain ; q=0.9 , application/json ; q=0.8 ")
        assert result == ResponseFormat.TEXT
    
    def test_invalid_quality_value_uses_default(self):
        """Test that invalid quality values use default 1.0."""
        result = self.formatter.parse_accept_header("text/plain;q=invalid, application/json;q=0.8")
        assert result == ResponseFormat.TEXT
    
    def test_quality_value_clamped_to_range(self):
        """Test that quality values are clamped to [0.0, 1.0]."""
        # Quality > 1.0 should be clamped to 1.0
        result = self.formatter.parse_accept_header("text/plain;q=2.0, application/json;q=0.9")
        assert result == ResponseFormat.TEXT
    
    def test_zero_quality_value(self):
        """Test handling of zero quality value."""
        result = self.formatter.parse_accept_header("text/plain;q=0.0, application/json;q=0.5")
        assert result == ResponseFormat.JSON
    
    def test_complex_accept_header(self):
        """Test complex Accept header with multiple types and parameters."""
        result = self.formatter.parse_accept_header(
            "text/html;q=0.9, application/json;q=0.8, text/plain;q=1.0, */*;q=0.5"
        )
        assert result == ResponseFormat.TEXT
    
    def test_first_match_wins_with_equal_quality(self):
        """Test that first matching format wins when quality values are equal."""
        # Both have quality 1.0 (default), text/plain comes first
        result = self.formatter.parse_accept_header("text/plain, application/json")
        assert result == ResponseFormat.TEXT


class TestFormatAsJson:
    """Tests for format_as_json method."""
    
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
    
    def test_format_as_json_with_valid_inputs(self):
        """Test JSON formatting with valid summary and metadata."""
        import json
        
        result = self.formatter.format_as_json(self.valid_summary, self.valid_metadata)
        
        # Verify result is a string
        assert isinstance(result, str)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        
        # Verify structure has summary and metadata fields
        assert "summary" in parsed
        assert "metadata" in parsed
        
        # Verify summary content is preserved
        assert parsed["summary"] == self.valid_summary
        
        # Verify all metadata fields are preserved
        assert parsed["metadata"]["model_id"] == "us.anthropic.claude-sonnet-4-6"
        assert parsed["metadata"]["processing_time_ms"] == 11263
        assert parsed["metadata"]["memos_included"] == 3
        assert parsed["metadata"]["memos_total"] == 3
        assert parsed["metadata"]["truncated"] is False
    
    def test_format_as_json_preserves_unicode(self):
        """Test that JSON formatting correctly encodes Unicode characters."""
        import json
        
        # Summary with Japanese text and emoji
        summary_with_unicode = "📝 日本語のテキスト\n\n🎉 絵文字も含む"
        
        result = self.formatter.format_as_json(summary_with_unicode, self.valid_metadata)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        
        # Verify Unicode characters are preserved
        assert parsed["summary"] == summary_with_unicode
        assert "📝" in parsed["summary"]
        assert "日本語" in parsed["summary"]
        assert "🎉" in parsed["summary"]
    
    def test_format_as_json_with_empty_summary_raises_error(self):
        """Test that empty summary raises ValueError."""
        with pytest.raises(ValueError, match="Summary cannot be empty"):
            self.formatter.format_as_json("", self.valid_metadata)
    
    def test_format_as_json_with_whitespace_only_summary_raises_error(self):
        """Test that whitespace-only summary raises ValueError."""
        with pytest.raises(ValueError, match="Summary cannot be empty"):
            self.formatter.format_as_json("   \n\t  ", self.valid_metadata)
    
    def test_format_as_json_with_missing_metadata_keys_raises_error(self):
        """Test that missing metadata keys raise ValueError."""
        incomplete_metadata = {
            "model_id": "test-model",
            "processing_time_ms": 1000
            # Missing: memos_included, memos_total, truncated
        }
        
        with pytest.raises(ValueError, match="Metadata missing required keys"):
            self.formatter.format_as_json(self.valid_summary, incomplete_metadata)
    
    def test_format_as_json_with_all_metadata_fields(self):
        """Test that all required metadata fields are included in output."""
        import json
        
        result = self.formatter.format_as_json(self.valid_summary, self.valid_metadata)
        parsed = json.loads(result)
        
        # Verify all required fields are present
        required_fields = ["model_id", "processing_time_ms", "memos_included", "memos_total", "truncated"]
        for field in required_fields:
            assert field in parsed["metadata"], f"Missing required field: {field}"
    
    def test_format_as_json_with_truncated_true(self):
        """Test JSON formatting with truncated flag set to True."""
        import json
        
        metadata_with_truncation = self.valid_metadata.copy()
        metadata_with_truncation["truncated"] = True
        
        result = self.formatter.format_as_json(self.valid_summary, metadata_with_truncation)
        parsed = json.loads(result)
        
        assert parsed["metadata"]["truncated"] is True
    
    def test_format_as_json_with_zero_processing_time(self):
        """Test JSON formatting with zero processing time."""
        import json
        
        metadata_with_zero_time = self.valid_metadata.copy()
        metadata_with_zero_time["processing_time_ms"] = 0
        
        result = self.formatter.format_as_json(self.valid_summary, metadata_with_zero_time)
        parsed = json.loads(result)
        
        assert parsed["metadata"]["processing_time_ms"] == 0
    
    def test_format_as_json_with_large_memo_counts(self):
        """Test JSON formatting with large memo counts."""
        import json
        
        metadata_with_large_counts = self.valid_metadata.copy()
        metadata_with_large_counts["memos_included"] = 1000
        metadata_with_large_counts["memos_total"] = 5000
        
        result = self.formatter.format_as_json(self.valid_summary, metadata_with_large_counts)
        parsed = json.loads(result)
        
        assert parsed["metadata"]["memos_included"] == 1000
        assert parsed["metadata"]["memos_total"] == 5000
    
    def test_format_as_json_does_not_mutate_inputs(self):
        """Test that format_as_json does not mutate input parameters."""
        import json
        
        original_summary = self.valid_summary
        original_metadata = self.valid_metadata.copy()
        
        result = self.formatter.format_as_json(self.valid_summary, self.valid_metadata)
        
        # Verify inputs are unchanged
        assert self.valid_summary == original_summary
        assert self.valid_metadata == original_metadata
        
        # Verify result is independent
        parsed = json.loads(result)
        parsed["summary"] = "modified"
        parsed["metadata"]["model_id"] = "modified"
        
        # Original metadata should be unchanged
        assert self.valid_metadata["model_id"] == original_metadata["model_id"]


class TestTextFormatVisualElements:
    """
    Property-based tests for text format visual elements.
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    
    Property 4: Text Format Visual Elements
    For any valid summary and metadata, when formatted as text, the response should 
    include visual separators (= and - characters), emoji icons (📝, 📊, 📄), 
    bullet points for metadata, and clearly separated summary content.
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResponseFormatter()
    
    def test_property_text_format_includes_all_visual_elements(self):
        """
        Property test: Text format includes all required visual elements.
        
        Tests that for any valid summary and metadata combination, the formatted
        text output contains:
        - Visual separators using "=" characters (header and footer)
        - Visual separators using "-" characters (section divider)
        - Emoji icon 📝 (memo summary result header)
        - Emoji icon 📊 (processing information section)
        - Emoji icon 📄 (summary content section)
        - Bullet points (•) for metadata items
        - Clearly separated summary content
        """
        from hypothesis import given, strategies as st
        
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
        
        @given(summary=summary_strategy, metadata=metadata_strategy)
        def property_test(summary, metadata):
            # Format as text
            result = self.formatter.format_as_text(summary, metadata)
            
            # Verify result is a non-empty string
            assert isinstance(result, str)
            assert len(result) > 0
            
            # Requirement 2.1: Visual separators using "=" characters
            # Should have header and footer separators
            assert "=" * 80 in result, "Missing '=' separator for header/footer"
            # Count occurrences - should have at least 2 (header and footer)
            equals_count = result.count("=" * 80)
            assert equals_count >= 2, f"Expected at least 2 '=' separators, found {equals_count}"
            
            # Requirement 2.1: Visual separators using "-" characters
            # Should have section divider
            assert "-" * 80 in result, "Missing '-' separator for section divider"
            
            # Requirement 2.2: Emoji icon 📝 for memo summary result
            assert "📝" in result, "Missing 📝 emoji icon"
            assert "📝 メモ要約結果" in result, "Missing header with 📝 emoji"
            
            # Requirement 2.2: Emoji icon 📊 for processing information
            assert "📊" in result, "Missing 📊 emoji icon"
            assert "📊 処理情報:" in result, "Missing processing info header with 📊 emoji"
            
            # Requirement 2.2: Emoji icon 📄 for summary content
            assert "📄" in result, "Missing 📄 emoji icon"
            assert "📄 要約内容:" in result, "Missing summary content header with 📄 emoji"
            
            # Requirement 2.3: Bullet points for metadata
            # Should have bullet points for each metadata item
            assert "•" in result, "Missing bullet points for metadata"
            # Count bullet points - should have at least 4 (processing time, memos, model, truncated)
            bullet_count = result.count("•")
            assert bullet_count >= 4, f"Expected at least 4 bullet points, found {bullet_count}"
            
            # Verify specific metadata items have bullet points
            assert "• 処理時間:" in result, "Missing bullet point for processing time"
            assert "• 要約対象:" in result, "Missing bullet point for memos count"
            assert "• モデル:" in result, "Missing bullet point for model"
            assert "• 切り詰め:" in result, "Missing bullet point for truncated flag"
            
            # Requirement 2.4: Clearly separated summary content
            # Summary should be present in the output
            assert summary in result, "Summary content not found in output"
            
            # Summary should appear after the 📄 emoji section
            # Search for summary only after the summary section header to avoid false matches
            summary_section_index = result.find("📄 要約内容:")
            assert summary_section_index != -1, "Summary section header not found"
            summary_index = result.find(summary, summary_section_index)
            assert summary_index > summary_section_index, "Summary not in correct section"
            
            # Summary should be separated from metadata by the "-" divider
            divider_index = result.find("-" * 80)
            assert summary_index > divider_index, "Summary not separated from metadata"
        
        # Run the property test
        property_test()
    
    def test_property_text_format_visual_elements_with_edge_cases(self):
        """
        Property test: Text format handles edge cases while maintaining visual elements.
        
        Tests edge cases like:
        - Zero processing time (should show "N/A")
        - Empty model_id
        - Zero memos
        - Very long summaries
        - Unicode characters in summary
        """
        from hypothesis import given, strategies as st
        
        # Strategy for edge case summaries
        summary_strategy = st.one_of(
            st.text(min_size=1, max_size=10).filter(lambda s: s.strip()),  # Short
            st.text(min_size=1000, max_size=2000).filter(lambda s: s.strip()),  # Long
            st.text(alphabet="日本語テスト", min_size=1, max_size=100).filter(lambda s: s.strip()),  # Japanese
            st.text(alphabet="🎉🎊🎈", min_size=1, max_size=50).filter(lambda s: s.strip())  # Emoji
        )
        
        # Strategy for edge case metadata
        metadata_strategy = st.fixed_dictionaries({
            "model_id": st.one_of(
                st.just(""),  # Empty model_id
                st.text(min_size=1, max_size=100)
            ),
            "processing_time_ms": st.one_of(
                st.just(0),  # Zero processing time
                st.integers(min_value=1, max_value=100000)
            ),
            "memos_included": st.integers(min_value=0, max_value=100),
            "memos_total": st.integers(min_value=0, max_value=100),
            "truncated": st.booleans()
        })
        
        @given(summary=summary_strategy, metadata=metadata_strategy)
        def property_test(summary, metadata):
            # Format as text
            result = self.formatter.format_as_text(summary, metadata)
            
            # All visual elements should still be present regardless of edge cases
            assert "=" * 80 in result
            assert "-" * 80 in result
            assert "📝" in result
            assert "📊" in result
            assert "📄" in result
            assert "•" in result
            
            # Summary should be preserved
            assert summary in result
            
            # Special handling for zero processing time
            if metadata["processing_time_ms"] == 0:
                assert "N/A" in result, "Zero processing time should show 'N/A'"
            else:
                # Should show time in seconds with 2 decimal places
                processing_time_sec = metadata["processing_time_ms"] / 1000.0
                expected_time = f"{processing_time_sec:.2f}秒"
                assert expected_time in result, f"Expected '{expected_time}' in output"
        
        # Run the property test
        property_test()
    
    def test_property_text_format_structure_order(self):
        """
        Property test: Text format maintains correct structural order.
        
        Verifies that visual elements appear in the correct order:
        1. Header with 📝 and "=" separators
        2. Processing info section with 📊 and bullet points
        3. Section divider with "-" characters
        4. Summary content section with 📄
        5. Footer with "=" separator
        """
        from hypothesis import given, strategies as st
        
        summary_strategy = st.text(min_size=1, max_size=200).filter(lambda s: s.strip())
        metadata_strategy = st.fixed_dictionaries({
            "model_id": st.text(min_size=1, max_size=50),
            "processing_time_ms": st.integers(min_value=0, max_value=50000),
            "memos_included": st.integers(min_value=0, max_value=100),
            "memos_total": st.integers(min_value=0, max_value=100),
            "truncated": st.booleans()
        })
        
        @given(summary=summary_strategy, metadata=metadata_strategy)
        def property_test(summary, metadata):
            result = self.formatter.format_as_text(summary, metadata)
            
            # Find positions of key elements
            # Use rfind for emoji that might appear in metadata to get the last occurrence
            header_emoji_pos = result.find("📝 メモ要約結果")
            processing_emoji_pos = result.find("📊 処理情報:")
            divider_pos = result.find("-" * 80)
            summary_emoji_pos = result.find("📄 要約内容:")
            
            # Verify all elements are found
            assert header_emoji_pos != -1, "Header emoji not found"
            assert processing_emoji_pos != -1, "Processing emoji not found"
            assert divider_pos != -1, "Divider not found"
            assert summary_emoji_pos != -1, "Summary emoji not found"
            
            # Verify order: header < processing < divider < summary section
            assert header_emoji_pos < processing_emoji_pos, \
                "Header emoji should appear before processing emoji"
            assert processing_emoji_pos < divider_pos, \
                "Processing emoji should appear before divider"
            assert divider_pos < summary_emoji_pos, \
                "Divider should appear before summary emoji"
            
            # Verify summary content appears after summary section header
            # Search for summary only after the summary section header
            summary_pos = result.find(summary, summary_emoji_pos)
            assert summary_pos > summary_emoji_pos, \
                "Summary content should appear after summary section header"
            
            # Verify bullet points appear in processing section (between 📊 and divider)
            first_bullet_pos = result.find("•")
            assert processing_emoji_pos < first_bullet_pos < divider_pos, \
                "Bullet points should appear in processing section"
        
        # Run the property test
        property_test()


class TestProcessingTimeFormatting:
    """
    Property-based tests for processing time formatting.
    
    **Validates: Requirements 2.5, 4.6**
    
    Property 5: Processing Time Formatting
    For any valid summary and metadata, when formatted as text and processing_time_ms 
    is greater than zero, the response should display processing time in seconds with 
    two decimal places.
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResponseFormatter()
    
    def test_property_processing_time_formatted_correctly(self):
        """
        Property test: Processing time is formatted in seconds with two decimal places.
        
        Tests that for any valid summary and metadata with positive processing_time_ms,
        the formatted text output displays the processing time converted to seconds
        with exactly two decimal places.
        """
        from hypothesis import given, strategies as st
        
        # Strategy for generating valid summaries (non-empty strings)
        summary_strategy = st.text(min_size=1, max_size=500).filter(lambda s: s.strip())
        
        # Strategy for generating valid metadata with positive processing times
        metadata_strategy = st.fixed_dictionaries({
            "model_id": st.text(min_size=1, max_size=100),
            "processing_time_ms": st.integers(min_value=1, max_value=100000),  # Positive only
            "memos_included": st.integers(min_value=0, max_value=10000),
            "memos_total": st.integers(min_value=0, max_value=10000),
            "truncated": st.booleans()
        })
        
        @given(summary=summary_strategy, metadata=metadata_strategy)
        def property_test(summary, metadata):
            # Format as text
            result = self.formatter.format_as_text(summary, metadata)
            
            # Calculate expected processing time in seconds with 2 decimal places
            processing_time_ms = metadata["processing_time_ms"]
            processing_time_sec = processing_time_ms / 1000.0
            expected_time_str = f"{processing_time_sec:.2f}秒"
            
            # Verify the formatted time appears in the output
            assert expected_time_str in result, \
                f"Expected '{expected_time_str}' in output for {processing_time_ms}ms"
            
            # Verify it appears in the processing info section with bullet point
            assert f"• 処理時間: {expected_time_str}" in result, \
                f"Expected '• 処理時間: {expected_time_str}' in output"
            
            # Verify "N/A" does NOT appear when processing time is positive
            # Check specifically in the processing time line with bullet point
            processing_time_line = [line for line in result.split('\n') if '• 処理時間:' in line][0]
            assert "N/A" not in processing_time_line, \
                "Should not show 'N/A' when processing time is positive"
        
        # Run the property test
        property_test()
    
    def test_property_zero_processing_time_shows_na(self):
        """
        Property test: Zero processing time displays "N/A".
        
        Tests that when processing_time_ms is zero, the formatted text output
        displays "N/A" instead of "0.00秒".
        """
        from hypothesis import given, strategies as st
        
        summary_strategy = st.text(min_size=1, max_size=500).filter(lambda s: s.strip())
        
        # Metadata with zero processing time
        metadata_strategy = st.fixed_dictionaries({
            "model_id": st.text(min_size=1, max_size=100),
            "processing_time_ms": st.just(0),  # Always zero
            "memos_included": st.integers(min_value=0, max_value=10000),
            "memos_total": st.integers(min_value=0, max_value=10000),
            "truncated": st.booleans()
        })
        
        @given(summary=summary_strategy, metadata=metadata_strategy)
        def property_test(summary, metadata):
            # Format as text
            result = self.formatter.format_as_text(summary, metadata)
            
            # Verify "N/A" appears in the processing time line
            assert "• 処理時間: N/A" in result, \
                "Expected '• 処理時間: N/A' when processing time is zero"
            
            # Verify no time in seconds format appears
            assert "0.00秒" not in result, \
                "Should not show '0.00秒' when processing time is zero"
        
        # Run the property test
        property_test()
    
    def test_property_negative_processing_time_shows_na(self):
        """
        Property test: Negative processing time displays "N/A".
        
        Tests that when processing_time_ms is negative (edge case), the formatted 
        text output displays "N/A" instead of a negative time value.
        """
        from hypothesis import given, strategies as st
        
        summary_strategy = st.text(min_size=1, max_size=500).filter(lambda s: s.strip())
        
        # Metadata with negative processing time
        metadata_strategy = st.fixed_dictionaries({
            "model_id": st.text(min_size=1, max_size=100),
            "processing_time_ms": st.integers(min_value=-10000, max_value=-1),  # Negative only
            "memos_included": st.integers(min_value=0, max_value=10000),
            "memos_total": st.integers(min_value=0, max_value=10000),
            "truncated": st.booleans()
        })
        
        @given(summary=summary_strategy, metadata=metadata_strategy)
        def property_test(summary, metadata):
            # Format as text
            result = self.formatter.format_as_text(summary, metadata)
            
            # Verify "N/A" appears in the processing time line
            assert "• 処理時間: N/A" in result, \
                "Expected '• 処理時間: N/A' when processing time is negative"
            
            # Verify no negative time appears
            processing_time_ms = metadata["processing_time_ms"]
            processing_time_sec = processing_time_ms / 1000.0
            negative_time_str = f"{processing_time_sec:.2f}秒"
            assert negative_time_str not in result, \
                f"Should not show negative time '{negative_time_str}'"
        
        # Run the property test
        property_test()
    
    def test_property_processing_time_precision(self):
        """
        Property test: Processing time always has exactly two decimal places.
        
        Tests that the processing time is always formatted with exactly two decimal
        places, regardless of the actual value (e.g., 1000ms -> "1.00秒", not "1.0秒" or "1秒").
        """
        from hypothesis import given, strategies as st
        import re
        
        summary_strategy = st.text(min_size=1, max_size=500).filter(lambda s: s.strip())
        
        # Include various processing times that might have different decimal representations
        metadata_strategy = st.fixed_dictionaries({
            "model_id": st.text(min_size=1, max_size=100),
            "processing_time_ms": st.one_of(
                st.just(1000),  # Exactly 1 second
                st.just(1500),  # 1.5 seconds
                st.just(1234),  # 1.234 seconds (should round to 1.23)
                st.just(1),     # 0.001 seconds
                st.just(999),   # 0.999 seconds
                st.integers(min_value=1, max_value=100000)  # Random positive values
            ),
            "memos_included": st.integers(min_value=0, max_value=10000),
            "memos_total": st.integers(min_value=0, max_value=10000),
            "truncated": st.booleans()
        })
        
        @given(summary=summary_strategy, metadata=metadata_strategy)
        def property_test(summary, metadata):
            # Format as text
            result = self.formatter.format_as_text(summary, metadata)
            
            # Extract the processing time line more specifically (with bullet point)
            processing_time_lines = [line for line in result.split('\n') if '• 処理時間:' in line]
            assert len(processing_time_lines) == 1, "Should have exactly one processing time line"
            processing_time_line = processing_time_lines[0]
            
            # Use regex to find the time format: should be X.XX秒 (two decimal places)
            # Pattern: one or more digits, dot, exactly two digits, followed by 秒
            time_pattern = r'\d+\.\d{2}秒'
            matches = re.findall(time_pattern, processing_time_line)
            
            # Should have exactly one match
            assert len(matches) == 1, \
                f"Expected exactly one time with 2 decimal places, found: {matches}"
            
            # Verify the matched value is correct
            processing_time_ms = metadata["processing_time_ms"]
            processing_time_sec = processing_time_ms / 1000.0
            expected_time_str = f"{processing_time_sec:.2f}秒"
            assert matches[0] == expected_time_str, \
                f"Expected '{expected_time_str}', found '{matches[0]}'"
        
        # Run the property test
        property_test()
    
    def test_property_processing_time_edge_values(self):
        """
        Property test: Processing time formatting handles edge values correctly.
        
        Tests specific edge cases:
        - Very small times (1ms = 0.001s -> "0.00秒")
        - Very large times (99999ms = 99.999s -> "100.00秒")
        - Times that round up/down
        """
        from hypothesis import given, strategies as st
        
        summary_strategy = st.text(min_size=1, max_size=200).filter(lambda s: s.strip())
        
        # Edge case processing times
        edge_case_times = st.sampled_from([
            1,      # 0.001s -> "0.00秒"
            10,     # 0.010s -> "0.01秒"
            100,    # 0.100s -> "0.10秒"
            999,    # 0.999s -> "1.00秒" (rounds up)
            1000,   # 1.000s -> "1.00秒"
            1001,   # 1.001s -> "1.00秒" (rounds down)
            1005,   # 1.005s -> "1.00秒" or "1.01秒" (depends on rounding)
            10000,  # 10.000s -> "10.00秒"
            99999,  # 99.999s -> "100.00秒" (rounds up)
        ])
        
        metadata_strategy = st.fixed_dictionaries({
            "model_id": st.text(min_size=1, max_size=50),
            "processing_time_ms": edge_case_times,
            "memos_included": st.integers(min_value=0, max_value=100),
            "memos_total": st.integers(min_value=0, max_value=100),
            "truncated": st.booleans()
        })
        
        @given(summary=summary_strategy, metadata=metadata_strategy)
        def property_test(summary, metadata):
            # Format as text
            result = self.formatter.format_as_text(summary, metadata)
            
            # Calculate expected time with Python's default rounding
            processing_time_ms = metadata["processing_time_ms"]
            processing_time_sec = processing_time_ms / 1000.0
            expected_time_str = f"{processing_time_sec:.2f}秒"
            
            # Verify the expected time appears in output
            assert expected_time_str in result, \
                f"Expected '{expected_time_str}' for {processing_time_ms}ms"
            
            # Verify it's in the correct format (X.XX秒)
            import re
            processing_time_line = [line for line in result.split('\n') if '• 処理時間:' in line][0]
            time_pattern = r'\d+\.\d{2}秒'
            matches = re.findall(time_pattern, processing_time_line)
            assert len(matches) == 1, f"Expected one time match, found: {matches}"
        
        # Run the property test
        property_test()


class TestFormatAsText:
    """
    Unit tests for format_as_text method.
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 5.2, 5.3**
    
    Tests specific examples and edge cases for text formatting including:
    - Valid summary and metadata
    - Visual separators and emoji presence
    - Metadata display format
    - Japanese character encoding
    - Processing time formatting (positive, zero, negative values)
    """
    
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
    
    def test_format_as_text_with_valid_inputs(self):
        """Test text formatting with valid summary and metadata."""
        result = self.formatter.format_as_text(self.valid_summary, self.valid_metadata)
        
        # Verify result is a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify summary content is preserved
        assert self.valid_summary in result
        
        # Verify all metadata values are present
        assert "us.anthropic.claude-sonnet-4-6" in result
        assert "3/3件のメモ" in result
        assert "なし" in result  # truncated=False -> "なし"
    
    def test_format_as_text_visual_separators(self):
        """Test that text format includes visual separators (= and - characters)."""
        result = self.formatter.format_as_text(self.valid_summary, self.valid_metadata)
        
        # Requirement 2.1: Visual separators using "=" characters
        assert "=" * 80 in result, "Missing '=' separator"
        # Should have at least 2 occurrences (header and footer)
        equals_count = result.count("=" * 80)
        assert equals_count >= 2, f"Expected at least 2 '=' separators, found {equals_count}"
        
        # Requirement 2.1: Visual separators using "-" characters
        assert "-" * 80 in result, "Missing '-' separator"
    
    def test_format_as_text_emoji_presence(self):
        """Test that text format includes emoji icons (📝, 📊, 📄)."""
        result = self.formatter.format_as_text(self.valid_summary, self.valid_metadata)
        
        # Requirement 2.2: Emoji icons for visual clarity
        assert "📝" in result, "Missing 📝 emoji icon"
        assert "📊" in result, "Missing 📊 emoji icon"
        assert "📄" in result, "Missing 📄 emoji icon"
        
        # Verify emoji appear in correct context
        assert "📝 メモ要約結果" in result
        assert "📊 処理情報:" in result
        assert "📄 要約内容:" in result
    
    def test_format_as_text_metadata_display_format(self):
        """Test that metadata is displayed in labeled list format with bullet points."""
        result = self.formatter.format_as_text(self.valid_summary, self.valid_metadata)
        
        # Requirement 2.3: Metadata in labeled list format with bullet points
        assert "•" in result, "Missing bullet points"
        
        # Verify specific metadata items with bullet points
        assert "• 処理時間:" in result
        assert "• 要約対象:" in result
        assert "• モデル:" in result
        assert "• 切り詰め:" in result
        
        # Verify at least 4 bullet points (one for each metadata item)
        bullet_count = result.count("•")
        assert bullet_count >= 4, f"Expected at least 4 bullet points, found {bullet_count}"
    
    def test_format_as_text_japanese_character_encoding(self):
        """Test that Japanese characters are correctly encoded in text format."""
        # Summary with Japanese text
        japanese_summary = "日本語のテキストです。\n\nこれは要約内容を含みます。"
        
        result = self.formatter.format_as_text(japanese_summary, self.valid_metadata)
        
        # Requirement 5.2: Correctly encode Japanese characters
        assert "日本語のテキストです。" in result
        assert "これは要約内容を含みます。" in result
        
        # Verify Japanese text in metadata labels is preserved
        assert "メモ要約結果" in result
        assert "処理情報" in result
        assert "要約内容" in result
        assert "要約対象" in result
        assert "件のメモ" in result
        assert "切り詰め" in result
    
    def test_format_as_text_emoji_character_encoding(self):
        """Test that emoji characters are correctly encoded in text format."""
        # Summary with emoji
        emoji_summary = "🎉 プロジェクト完了！\n\n✅ すべてのタスクが完了しました。"
        
        result = self.formatter.format_as_text(emoji_summary, self.valid_metadata)
        
        # Requirement 5.3: Correctly encode emoji characters
        assert "🎉" in result
        assert "✅" in result
        assert emoji_summary in result
        
        # Verify emoji in format structure are preserved
        assert "📝" in result
        assert "📊" in result
        assert "📄" in result
    
    def test_format_as_text_processing_time_positive(self):
        """Test processing time formatting with positive value (in seconds with 2 decimal places)."""
        result = self.formatter.format_as_text(self.valid_summary, self.valid_metadata)
        
        # Requirement 2.5: Format processing time in seconds with two decimal places
        processing_time_ms = self.valid_metadata["processing_time_ms"]
        processing_time_sec = processing_time_ms / 1000.0
        expected_time = f"{processing_time_sec:.2f}秒"
        
        assert expected_time in result, f"Expected '{expected_time}' in output"
        assert f"• 処理時間: {expected_time}" in result
        
        # Verify "N/A" does NOT appear
        processing_time_line = [line for line in result.split('\n') if '• 処理時間:' in line][0]
        assert "N/A" not in processing_time_line
    
    def test_format_as_text_processing_time_zero(self):
        """Test processing time formatting with zero value (should display N/A)."""
        metadata_with_zero_time = self.valid_metadata.copy()
        metadata_with_zero_time["processing_time_ms"] = 0
        
        result = self.formatter.format_as_text(self.valid_summary, metadata_with_zero_time)
        
        # Requirement 4.7: Display "N/A" for zero processing time
        assert "• 処理時間: N/A" in result
        
        # Verify no time in seconds format appears
        assert "0.00秒" not in result
    
    def test_format_as_text_processing_time_negative(self):
        """Test processing time formatting with negative value (should display N/A)."""
        metadata_with_negative_time = self.valid_metadata.copy()
        metadata_with_negative_time["processing_time_ms"] = -1000
        
        result = self.formatter.format_as_text(self.valid_summary, metadata_with_negative_time)
        
        # Requirement 4.7: Display "N/A" for negative processing time
        assert "• 処理時間: N/A" in result
        
        # Verify no negative time appears
        assert "-1.00秒" not in result
    
    def test_format_as_text_processing_time_small_value(self):
        """Test processing time formatting with small value (1ms = 0.00秒)."""
        metadata_with_small_time = self.valid_metadata.copy()
        metadata_with_small_time["processing_time_ms"] = 1
        
        result = self.formatter.format_as_text(self.valid_summary, metadata_with_small_time)
        
        # Should format as 0.00秒 (1ms = 0.001s -> 0.00秒 with 2 decimal places)
        assert "• 処理時間: 0.00秒" in result
    
    def test_format_as_text_processing_time_large_value(self):
        """Test processing time formatting with large value."""
        metadata_with_large_time = self.valid_metadata.copy()
        metadata_with_large_time["processing_time_ms"] = 99999
        
        result = self.formatter.format_as_text(self.valid_summary, metadata_with_large_time)
        
        # Should format as 100.00秒 (99999ms = 99.999s -> 100.00秒 with rounding)
        processing_time_sec = 99999 / 1000.0
        expected_time = f"{processing_time_sec:.2f}秒"
        assert expected_time in result
    
    def test_format_as_text_processing_time_exact_seconds(self):
        """Test processing time formatting with exact seconds (no decimal part)."""
        metadata_with_exact_seconds = self.valid_metadata.copy()
        metadata_with_exact_seconds["processing_time_ms"] = 5000
        
        result = self.formatter.format_as_text(self.valid_summary, metadata_with_exact_seconds)
        
        # Should format as 5.00秒 (not 5秒 or 5.0秒)
        assert "• 処理時間: 5.00秒" in result
    
    def test_format_as_text_truncated_true(self):
        """Test text formatting with truncated flag set to True."""
        metadata_with_truncation = self.valid_metadata.copy()
        metadata_with_truncation["truncated"] = True
        
        result = self.formatter.format_as_text(self.valid_summary, metadata_with_truncation)
        
        # Should display "あり" for truncated=True
        assert "• 切り詰め: あり" in result
    
    def test_format_as_text_truncated_false(self):
        """Test text formatting with truncated flag set to False."""
        result = self.formatter.format_as_text(self.valid_summary, self.valid_metadata)
        
        # Should display "なし" for truncated=False
        assert "• 切り詰め: なし" in result
    
    def test_format_as_text_zero_memos(self):
        """Test text formatting with zero memos."""
        metadata_with_zero_memos = self.valid_metadata.copy()
        metadata_with_zero_memos["memos_included"] = 0
        metadata_with_zero_memos["memos_total"] = 0
        
        result = self.formatter.format_as_text(self.valid_summary, metadata_with_zero_memos)
        
        # Should display "0/0件のメモ"
        assert "• 要約対象: 0/0件のメモ" in result
    
    def test_format_as_text_large_memo_counts(self):
        """Test text formatting with large memo counts."""
        metadata_with_large_counts = self.valid_metadata.copy()
        metadata_with_large_counts["memos_included"] = 1000
        metadata_with_large_counts["memos_total"] = 5000
        
        result = self.formatter.format_as_text(self.valid_summary, metadata_with_large_counts)
        
        # Should display "1000/5000件のメモ"
        assert "• 要約対象: 1000/5000件のメモ" in result
    
    def test_format_as_text_empty_model_id(self):
        """Test text formatting with empty model_id."""
        metadata_with_empty_model = self.valid_metadata.copy()
        metadata_with_empty_model["model_id"] = ""
        
        result = self.formatter.format_as_text(self.valid_summary, metadata_with_empty_model)
        
        # Should display empty string (or could be "N/A" depending on implementation)
        # Current implementation uses get() with "N/A" default, but key exists with empty value
        assert "• モデル:" in result
    
    def test_format_as_text_long_summary(self):
        """Test text formatting with long summary content."""
        long_summary = "これは非常に長い要約です。\n\n" + "詳細な内容が続きます。" * 100
        
        result = self.formatter.format_as_text(long_summary, self.valid_metadata)
        
        # Verify long summary is preserved
        assert long_summary in result
        
        # Verify structure is still intact
        assert "📝 メモ要約結果" in result
        assert "📊 処理情報:" in result
        assert "📄 要約内容:" in result
    
    def test_format_as_text_multiline_summary(self):
        """Test text formatting with multiline summary."""
        multiline_summary = "第1行\n第2行\n第3行\n\n段落が変わります。\n\n最後の段落。"
        
        result = self.formatter.format_as_text(multiline_summary, self.valid_metadata)
        
        # Verify multiline summary is preserved
        assert multiline_summary in result
        assert "第1行" in result
        assert "第2行" in result
        assert "第3行" in result
    
    def test_format_as_text_summary_with_special_characters(self):
        """Test text formatting with summary containing special characters."""
        special_summary = "特殊文字: @#$%^&*()_+-=[]{}|;':\",./<>?\n\n記号も含みます！"
        
        result = self.formatter.format_as_text(special_summary, self.valid_metadata)
        
        # Verify special characters are preserved
        assert special_summary in result
    
    def test_format_as_text_with_empty_summary_raises_error(self):
        """Test that empty summary raises ValueError."""
        with pytest.raises(ValueError, match="Summary cannot be empty"):
            self.formatter.format_as_text("", self.valid_metadata)
    
    def test_format_as_text_with_whitespace_only_summary_raises_error(self):
        """Test that whitespace-only summary raises ValueError."""
        with pytest.raises(ValueError, match="Summary cannot be empty"):
            self.formatter.format_as_text("   \n\t  ", self.valid_metadata)
    
    def test_format_as_text_with_missing_metadata_keys_raises_error(self):
        """Test that missing metadata keys raise ValueError."""
        incomplete_metadata = {
            "model_id": "test-model",
            "processing_time_ms": 1000
            # Missing: memos_included, memos_total, truncated
        }
        
        with pytest.raises(ValueError, match="Metadata missing required keys"):
            self.formatter.format_as_text(self.valid_summary, incomplete_metadata)
    
    def test_format_as_text_does_not_mutate_inputs(self):
        """Test that format_as_text does not mutate input parameters."""
        original_summary = self.valid_summary
        original_metadata = self.valid_metadata.copy()
        
        result = self.formatter.format_as_text(self.valid_summary, self.valid_metadata)
        
        # Verify inputs are unchanged
        assert self.valid_summary == original_summary
        assert self.valid_metadata == original_metadata
        
        # Verify result is independent
        # Modifying result should not affect inputs
        result = result.replace("メモ要約結果", "MODIFIED")
        assert "メモ要約結果" not in result
        # But original metadata should be unchanged
        assert self.valid_metadata == original_metadata
    
    def test_format_as_text_structure_order(self):
        """Test that text format maintains correct structural order."""
        result = self.formatter.format_as_text(self.valid_summary, self.valid_metadata)
        
        # Find positions of key elements
        header_pos = result.find("📝 メモ要約結果")
        processing_pos = result.find("📊 処理情報:")
        divider_pos = result.find("-" * 80)
        summary_section_pos = result.find("📄 要約内容:")
        summary_content_pos = result.find(self.valid_summary)
        
        # Verify all elements are found
        assert header_pos != -1
        assert processing_pos != -1
        assert divider_pos != -1
        assert summary_section_pos != -1
        assert summary_content_pos != -1
        
        # Verify correct order
        assert header_pos < processing_pos, "Header should come before processing info"
        assert processing_pos < divider_pos, "Processing info should come before divider"
        assert divider_pos < summary_section_pos, "Divider should come before summary section"
        assert summary_section_pos < summary_content_pos, "Summary section header should come before content"
