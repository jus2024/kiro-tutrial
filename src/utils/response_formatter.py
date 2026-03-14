"""
Response formatter utility for API responses.

This module provides utilities for formatting API responses in different formats
(JSON, text) based on client Accept headers, supporting content negotiation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class ResponseFormat(Enum):
    """Supported response format types."""
    
    JSON = "application/json"
    TEXT = "text/plain"


@dataclass
class FormattedResponse:
    """
    Formatted response data structure.
    
    Attributes:
        content: The formatted response body content
        content_type: The MIME type of the response (e.g., "application/json; charset=utf-8")
        status_code: HTTP status code for the response
        headers: Dictionary of HTTP headers to include in the response
    """
    
    content: str
    content_type: str
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)


class ResponseFormatter:
    """
    Formats API responses based on client Accept headers.
    
    Supports content negotiation between JSON and human-readable text formats,
    with proper CORS headers and UTF-8 encoding.
    """
    
    def format_response(
        self,
        summary: str,
        metadata: Dict[str, Any],
        accept_header: Optional[str] = None
    ) -> FormattedResponse:
        """
        Format a summary response based on the Accept header.

        Args:
            summary: AI-generated summary text
            metadata: Processing metadata (model_id, processing_time_ms, etc.)
            accept_header: HTTP Accept header value from the request

        Returns:
            FormattedResponse object with formatted content and headers

        Raises:
            ValueError: If summary is empty or metadata is missing required keys
        """
        # Step 1: Determine response format from Accept header
        response_format = self.parse_accept_header(accept_header)

        # Step 2: Format content based on determined format
        if response_format == ResponseFormat.TEXT:
            content = self.format_as_text(summary, metadata)
            content_type = "text/plain; charset=utf-8"
        else:
            content = self.format_as_json(summary, metadata)
            content_type = "application/json; charset=utf-8"

        # Step 3: Build response headers
        headers = {
            "Content-Type": content_type,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept"
        }

        # Step 4: Create response object
        response = FormattedResponse(
            content=content,
            content_type=content_type,
            status_code=200,
            headers=headers
        )

        return response
    
    def format_as_text(
        self,
        summary: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Format response as human-readable text.
        
        Args:
            summary: AI-generated summary text
            metadata: Processing metadata
            
        Returns:
            Formatted text string with visual separators and emoji
            
        Raises:
            ValueError: If summary is empty or metadata is missing required keys
        """
        # Validate inputs
        if not summary or not summary.strip():
            raise ValueError("Summary cannot be empty")

        required_keys = ["model_id", "processing_time_ms", "memos_included", "memos_total", "truncated"]
        missing_keys = [key for key in required_keys if key not in metadata]
        if missing_keys:
            raise ValueError(f"Metadata missing required keys: {missing_keys}")

        # Initialize output buffer
        output = []
        
        # Step 1: Add header section with "=" separators and 📝 emoji
        output.append("\n" + "=" * 80)
        output.append("📝 メモ要約結果")
        output.append("=" * 80 + "\n")
        
        # Step 2: Add metadata section with 📊 emoji and bullet points
        output.append("📊 処理情報:")
        
        # Format processing time in seconds with two decimal places (or "N/A" if <= 0)
        processing_time_ms = metadata["processing_time_ms"]
        if processing_time_ms > 0:
            processing_time_sec = processing_time_ms / 1000.0
            output.append(f"  • 処理時間: {processing_time_sec:.2f}秒")
        else:
            output.append("  • 処理時間: N/A")
        
        # Display memos_included/memos_total count
        memos_included = metadata["memos_included"]
        memos_total = metadata["memos_total"]
        output.append(f"  • 要約対象: {memos_included}/{memos_total}件のメモ")
        
        # Display model_id
        model_id = metadata.get("model_id", "N/A")
        output.append(f"  • モデル: {model_id}")
        
        # Display truncated flag
        truncated = metadata["truncated"]
        truncated_text = "あり" if truncated else "なし"
        output.append(f"  • 切り詰め: {truncated_text}")
        
        output.append("\n" + "-" * 80 + "\n")
        
        # Step 3: Add summary content section with 📄 emoji and "-" separator
        output.append("📄 要約内容:\n")
        output.append(summary)
        output.append("\n" + "=" * 80 + "\n")
        
        # Step 4: Join all parts
        result = "\n".join(output)
        
        return result
    
    def format_as_json(
        self,
        summary: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Format response as JSON (existing format).

        Args:
            summary: AI-generated summary text
            metadata: Processing metadata

        Returns:
            JSON string with summary and metadata fields

        Raises:
            ValueError: If summary is empty or metadata is missing required keys
        """
        import json

        # Validate inputs
        if not summary or not summary.strip():
            raise ValueError("Summary cannot be empty")

        required_keys = ["model_id", "processing_time_ms", "memos_included", "memos_total", "truncated"]
        missing_keys = [key for key in required_keys if key not in metadata]
        if missing_keys:
            raise ValueError(f"Metadata missing required keys: {missing_keys}")

        # Create JSON structure with summary and metadata fields
        response_body = {
            "summary": summary,
            "metadata": {
                "model_id": metadata["model_id"],
                "processing_time_ms": metadata["processing_time_ms"],
                "memos_included": metadata["memos_included"],
                "memos_total": metadata["memos_total"],
                "truncated": metadata["truncated"]
            }
        }

        # Return JSON string with proper UTF-8 encoding
        return json.dumps(response_body, ensure_ascii=False)
    
    def parse_accept_header(self, accept_header: Optional[str]) -> ResponseFormat:
        """
        Parse Accept header to determine response format.
        
        Args:
            accept_header: HTTP Accept header value
            
        Returns:
            ResponseFormat enum value (JSON or TEXT)
        """
        # Default to JSON if no header provided or empty
        if accept_header is None or accept_header.strip() == "":
            return ResponseFormat.JSON
        
        # Parse media types with quality values
        media_types = []
        
        for media_type_str in accept_header.split(","):
            parts = media_type_str.split(";")
            media_type = parts[0].strip()
            
            # Extract quality value (default 1.0)
            quality = 1.0
            if len(parts) > 1:
                for param in parts[1:]:
                    param = param.strip()
                    if param.startswith("q="):
                        try:
                            quality = float(param[2:])
                            # Clamp quality to valid range [0.0, 1.0]
                            quality = max(0.0, min(1.0, quality))
                        except (ValueError, IndexError):
                            # Invalid quality value, use default
                            quality = 1.0
            
            media_types.append((media_type, quality))
        
        # Sort by quality value (descending)
        media_types.sort(key=lambda x: x[1], reverse=True)
        
        # Find first matching format
        for media_type, quality in media_types:
            if media_type == "text/plain":
                return ResponseFormat.TEXT
            elif media_type == "application/json":
                return ResponseFormat.JSON
            elif media_type == "*/*":
                return ResponseFormat.JSON  # Default for wildcard
        
        # Default to JSON if no match
        return ResponseFormat.JSON
