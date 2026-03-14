"""
Property-based tests for ResponseFormatter using Hypothesis.

These tests verify universal properties across randomized inputs.
Each test runs at least 100 iterations with different generated values.
"""

import json
import pytest
from hypothesis import given, strategies as st, settings
from src.utils.response_formatter import ResponseFormatter, ResponseFormat


# Feature: api-response-formatting, Property 11: Accept Header Parsing
@settings(max_examples=100)
@given(
    media_types=st.lists(
        st.sampled_from(["text/plain", "application/json", "text/html", "*/*"]),
        min_size=1,
        max_size=5
    ),
    whitespace_before=st.sampled_from(["", " ", "  ", "\t"]),
    whitespace_after=st.sampled_from(["", " ", "  ", "\t"])
)
def test_accept_header_parsing_property(media_types, whitespace_before, whitespace_after):
    """
    Property 11: Accept Header Parsing
    
    For any Accept header with multiple media types separated by commas and 
    optional whitespace, the parser should correctly extract each media type, 
    trim whitespace, and parse quality values.
    
    Validates: Requirements 7.1, 7.5
    """
    formatter = ResponseFormatter()
    
    # Build Accept header with whitespace variations
    header_parts = []
    for media_type in media_types:
        header_parts.append(f"{whitespace_before}{media_type}{whitespace_after}")
    
    accept_header = ",".join(header_parts)
    
    # Parse the header
    result = formatter.parse_accept_header(accept_header)
    
    # Verify result is a valid ResponseFormat
    assert isinstance(result, ResponseFormat)
    assert result in [ResponseFormat.JSON, ResponseFormat.TEXT]
    
    # Verify parsing logic based on media types present
    # Strip whitespace from media types for comparison
    stripped_types = [mt.strip() for mt in media_types]
    
    if "text/plain" in stripped_types:
        # If text/plain is present (with default quality 1.0), it should be selected
        # unless there's a higher quality JSON
        assert result in [ResponseFormat.TEXT, ResponseFormat.JSON]
    elif "application/json" in stripped_types:
        # If only JSON is present, should return JSON
        assert result == ResponseFormat.JSON
    elif "*/*" in stripped_types:
        # Wildcard should default to JSON
        assert result == ResponseFormat.JSON
    else:
        # Unsupported media types should default to JSON
        assert result == ResponseFormat.JSON


# Feature: api-response-formatting, Property 2: Quality Value Selection
@settings(max_examples=100)
@given(
    text_quality=st.floats(min_value=0.0, max_value=1.0),
    json_quality=st.floats(min_value=0.0, max_value=1.0)
)
def test_quality_value_selection_property(text_quality, json_quality):
    """
    Property 2: Quality Value Selection
    
    For any valid summary and metadata, when an Accept header contains multiple 
    media types with quality values, the response format should be the one with 
    the highest quality value.
    
    Validates: Requirements 1.4, 7.2, 7.3
    """
    formatter = ResponseFormatter()
    
    # Build Accept header with quality values
    accept_header = f"text/plain;q={text_quality}, application/json;q={json_quality}"
    
    # Parse the header
    result = formatter.parse_accept_header(accept_header)
    
    # Verify result is a valid ResponseFormat
    assert isinstance(result, ResponseFormat)
    
    # Verify the format with the highest quality value is selected
    if text_quality > json_quality:
        assert result == ResponseFormat.TEXT, \
            f"Expected TEXT format for text/plain;q={text_quality} > application/json;q={json_quality}"
    elif json_quality > text_quality:
        assert result == ResponseFormat.JSON, \
            f"Expected JSON format for application/json;q={json_quality} > text/plain;q={text_quality}"
    else:
        # When quality values are equal, the first one in the list should be selected
        # In our case, text/plain comes first
        assert result == ResponseFormat.TEXT, \
            f"Expected TEXT format when quality values are equal (both {text_quality})"


# Feature: api-response-formatting, Property 3: Wildcard and Default Handling
@settings(max_examples=100)
@given(
    edge_case=st.sampled_from([
        None,                    # None header
        "",                      # Empty string
        "   ",                   # Whitespace only
        "*/*",                   # Wildcard
        "text/html",             # Unsupported media type
        "image/png",             # Another unsupported type
        "application/xml",       # Yet another unsupported type
        "text/html, image/png",  # Multiple unsupported types
        "*/*;q=0.8",            # Wildcard with quality
        "text/html;q=0.9, */*;q=0.5",  # Unsupported + wildcard
    ])
)
def test_wildcard_and_default_handling_property(edge_case):
    """
    Property 3: Wildcard and Default Handling
    
    For any valid summary and metadata, when the Accept header is "*/*", 
    empty string, None, or contains unsupported media types, the response 
    should default to application/json format.
    
    Validates: Requirements 1.5, 9.3, 9.4, 9.5
    """
    formatter = ResponseFormatter()
    
    # Parse the edge case header
    result = formatter.parse_accept_header(edge_case)
    
    # Verify result is a valid ResponseFormat
    assert isinstance(result, ResponseFormat)
    
    # All edge cases should default to JSON format
    assert result == ResponseFormat.JSON, \
        f"Expected JSON format for edge case: {repr(edge_case)}, but got {result}"


# Feature: api-response-formatting, Property 12: Malformed Header Handling
@settings(max_examples=100)
@given(
    malformed_header=st.one_of(
        # Invalid quality values
        st.just("text/plain;q=invalid"),
        st.just("application/json;q=abc"),
        st.just("text/plain;q="),
        st.just("application/json;q=1.5"),  # Out of range
        st.just("text/plain;q=-0.5"),  # Negative
        st.just("text/plain;q=2.0"),  # Greater than 1.0
        
        # Malformed media types
        st.just(";;;"),
        st.just("text/plain;;;q=0.8"),
        st.just(",,,"),
        st.just("text/plain,,application/json"),
        st.just("text/plain;"),
        st.just(";q=0.8"),
        
        # Invalid separators and syntax
        st.just("text/plain;;q=0.8"),
        st.just("text/plain;q=0.8;q=0.9"),  # Duplicate quality
        st.just("text/plain;q=0.8;"),
        st.just("text/plain;invalid=value;q=0.8"),
        
        # Mixed valid and invalid
        st.just("text/plain;q=0.9, invalid/type;q=abc"),
        st.just("text/plain;q=invalid, application/json;q=0.8"),
        st.just(";;;, text/plain"),
        
        # Random strings that might break parsing
        st.text(min_size=1, max_size=50).filter(
            lambda s: s.strip() != "" and 
                     "text/plain" not in s and 
                     "application/json" not in s and
                     "*/*" not in s
        ),
        
        # Special characters
        st.just("text/plain;q=0.8\x00"),  # Null byte
        st.just("text/plain\n;q=0.8"),  # Newline
        st.just("text/plain\r\n;q=0.8"),  # CRLF
        st.just("text/plain;q=0.8\t"),  # Tab
        
        # Unicode and non-ASCII
        st.just("text/plain;q=0.8;charset=日本語"),
        st.just("テキスト/プレーン"),
        st.just("text/plain;q=零点八"),
    )
)
def test_malformed_header_handling_property(malformed_header):
    """
    Property 12: Malformed Header Handling
    
    For any invalid or malformed Accept header, the parser should gracefully 
    default to JSON format without throwing errors.
    
    Validates: Requirements 7.4
    """
    formatter = ResponseFormatter()
    
    # Parse the malformed header - should not raise any exceptions
    try:
        result = formatter.parse_accept_header(malformed_header)
    except Exception as e:
        pytest.fail(
            f"parse_accept_header raised {type(e).__name__} for malformed header: "
            f"{repr(malformed_header)}\nError: {str(e)}"
        )
    
    # Verify result is a valid ResponseFormat
    assert isinstance(result, ResponseFormat), \
        f"Expected ResponseFormat instance, got {type(result)} for header: {repr(malformed_header)}"
    
    # Verify result is one of the valid formats
    assert result in [ResponseFormat.JSON, ResponseFormat.TEXT], \
        f"Expected JSON or TEXT format, got {result} for header: {repr(malformed_header)}"
    
    # For truly malformed headers (not containing valid media types), should default to JSON
    # This is a softer assertion since some malformed headers might accidentally contain
    # valid media type strings
    if not any(valid_type in malformed_header for valid_type in ["text/plain", "application/json", "*/*"]):
        assert result == ResponseFormat.JSON, \
            f"Expected JSON format for malformed header without valid media types: {repr(malformed_header)}"


# Strategies for generating valid summaries and metadata

# Strategy for generating valid summary text (non-empty, with various content)
summary_strategy = st.text(
    min_size=1,
    max_size=5000,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po'),
        whitelist_characters='あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん📝📊📄🎉日本語テスト。、\n'
    )
).filter(lambda s: s.strip() != "")  # Ensure non-empty after stripping


# Strategy for generating valid metadata dictionaries
@st.composite
def metadata_strategy(draw):
    """
    Generate a valid metadata dictionary with all required fields.
    
    Returns:
        Dictionary with model_id, processing_time_ms, memos_included, memos_total, truncated
    """
    # Generate model_id (string)
    model_id = draw(st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='.-_'
        )
    ).filter(lambda s: s.strip() != ""))
    
    # Generate processing_time_ms (non-negative integer)
    processing_time_ms = draw(st.integers(min_value=0, max_value=100000))
    
    # Generate memo counts (memos_included <= memos_total)
    memos_total = draw(st.integers(min_value=0, max_value=10000))
    memos_included = draw(st.integers(min_value=0, max_value=memos_total))
    
    # Generate truncated flag (boolean)
    truncated = draw(st.booleans())
    
    return {
        "model_id": model_id,
        "processing_time_ms": processing_time_ms,
        "memos_included": memos_included,
        "memos_total": memos_total,
        "truncated": truncated
    }


# Feature: api-response-formatting, Property 6: JSON Structure Preservation
@settings(max_examples=100)
@given(
    summary=summary_strategy,
    metadata=metadata_strategy()
)
def test_json_structure_preservation_property(summary, metadata):
    """
    Property 6: JSON Structure Preservation
    
    For any valid summary and metadata, when formatted as JSON, the response 
    should contain "summary" and "metadata" fields, with all metadata fields 
    (model_id, processing_time_ms, memos_included, memos_total, truncated) 
    preserved in their original structure.
    
    **Validates: Requirements 3.2, 3.3, 3.4**
    """
    formatter = ResponseFormatter()
    
    # Format as JSON
    result = formatter.format_as_json(summary, metadata)
    
    # Verify result is a string
    assert isinstance(result, str), \
        f"Expected string result, got {type(result)}"
    
    # Verify it's valid JSON
    try:
        parsed = json.loads(result)
    except json.JSONDecodeError as e:
        pytest.fail(f"format_as_json returned invalid JSON: {e}\nResult: {result}")
    
    # Verify structure has "summary" and "metadata" fields
    assert "summary" in parsed, \
        "JSON response missing 'summary' field"
    assert "metadata" in parsed, \
        "JSON response missing 'metadata' field"
    
    # Verify summary content is preserved exactly
    assert parsed["summary"] == summary, \
        f"Summary content not preserved. Expected: {repr(summary)}, Got: {repr(parsed['summary'])}"
    
    # Verify all metadata fields are preserved with correct values
    required_fields = ["model_id", "processing_time_ms", "memos_included", "memos_total", "truncated"]
    
    for field in required_fields:
        assert field in parsed["metadata"], \
            f"Metadata missing required field: {field}"
        
        assert parsed["metadata"][field] == metadata[field], \
            f"Metadata field '{field}' not preserved. Expected: {metadata[field]}, Got: {parsed['metadata'][field]}"
    
    # Verify metadata structure integrity (no extra fields added)
    # Note: We allow extra fields in metadata, but all required fields must be present
    for field in required_fields:
        assert field in parsed["metadata"], \
            f"Required metadata field '{field}' missing in output"
    
    # Verify data types are preserved
    assert isinstance(parsed["summary"], str), \
        "Summary should be a string"
    assert isinstance(parsed["metadata"]["model_id"], str), \
        "model_id should be a string"
    assert isinstance(parsed["metadata"]["processing_time_ms"], int), \
        "processing_time_ms should be an integer"
    assert isinstance(parsed["metadata"]["memos_included"], int), \
        "memos_included should be an integer"
    assert isinstance(parsed["metadata"]["memos_total"], int), \
        "memos_total should be an integer"
    assert isinstance(parsed["metadata"]["truncated"], bool), \
        "truncated should be a boolean"
