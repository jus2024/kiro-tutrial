"""
Integration tests for Lambda handler with ResponseFormatter.

Tests the end-to-end functionality of the Lambda handler with different Accept headers,
verifying that the response format matches the requested format.

**Validates: Requirements 1.1, 1.2, 1.3, 3.1**
"""

import json
import os
from unittest.mock import MagicMock, patch
import pytest

# Set environment variables before importing handler
os.environ['MEMO_TABLE_NAME'] = 'test-memo-table'
os.environ['BEDROCK_MODEL_ID'] = 'us.anthropic.claude-sonnet-4-6'
os.environ['BEDROCK_REGION'] = 'us-west-2'
os.environ['MAX_RETRIES'] = '3'
os.environ['MAX_CONTENT_TOKENS'] = '180000'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['POWERTOOLS_SERVICE_NAME'] = 'ai-summary-api'
os.environ['POWERTOOLS_TRACE_DISABLED'] = '1'
os.environ['POWERTOOLS_METRICS_NAMESPACE'] = 'AIMemoryAPI'

from src.functions.all_memos_summary.handler import lambda_handler
from tests.unit.test_all_memos_summary_fixtures import (
    create_test_memos,
    MockBedrockClient,
)


def setup_mock_dynamodb(mock_dynamodb_boto3, memos):
    """Configure the injected mock_dynamodb_boto3 to return the given memos."""
    mock_table = MagicMock()
    mock_table.query.return_value = {
        'Items': [memo.to_dynamodb_item() for memo in memos],
        'Count': len(memos),
    }
    mock_dynamodb_resource = MagicMock()
    mock_dynamodb_resource.Table.return_value = mock_table
    mock_dynamodb_boto3.resource.return_value = mock_dynamodb_resource


class TestLambdaHandlerResponseFormatting:
    """Integration tests for Lambda handler with ResponseFormatter."""

    def create_mock_context(self, request_id: str = "test-request-id"):
        context = MagicMock()
        context.aws_request_id = request_id
        context.function_name = "AllMemosSummaryFunction"
        context.memory_limit_in_mb = 1024
        context.invoked_function_arn = (
            "arn:aws:lambda:us-west-2:123456789012:function:AllMemosSummaryFunction"
        )
        return context

    @patch('repositories.memo_repository.boto3')
    @patch('services.bedrock_service.boto3')
    def test_post_request_with_text_plain_accept_header(
        self, mock_bedrock_boto3, mock_dynamodb_boto3
    ):
        """
        Test POST request with Accept: text/plain header returns text format.

        **Validates: Requirement 1.1**
        """
        test_memos = create_test_memos(count=3, content_size=100)
        setup_mock_dynamodb(mock_dynamodb_boto3, test_memos)

        summary_text = "これは日本語のテスト要約です。"
        mock_bedrock_boto3.client.return_value = MockBedrockClient(response_text=summary_text)

        event = {
            'body': '{}',
            'httpMethod': 'POST',
            'path': '/memos/summary',
            'headers': {'Accept': 'text/plain'},
        }

        response = lambda_handler(event, self.create_mock_context())

        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'text/plain; charset=utf-8'

        body = response['body']
        assert isinstance(body, str)
        assert '📝 メモ要約結果' in body
        assert '📊 処理情報:' in body
        assert '📄 要約内容:' in body
        assert summary_text in body
        assert '=' * 80 in body
        assert '-' * 80 in body

    @patch('repositories.memo_repository.boto3')
    @patch('services.bedrock_service.boto3')
    def test_post_request_with_application_json_accept_header(
        self, mock_bedrock_boto3, mock_dynamodb_boto3
    ):
        """
        Test POST request with Accept: application/json header returns JSON format.

        **Validates: Requirement 1.2**
        """
        test_memos = create_test_memos(count=5, content_size=150)
        setup_mock_dynamodb(mock_dynamodb_boto3, test_memos)

        summary_text = "JSON format test summary"
        mock_bedrock_boto3.client.return_value = MockBedrockClient(response_text=summary_text)

        event = {
            'body': '{}',
            'httpMethod': 'POST',
            'path': '/memos/summary',
            'headers': {'Accept': 'application/json'},
        }

        response = lambda_handler(event, self.create_mock_context())

        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'application/json; charset=utf-8'

        body = json.loads(response['body'])
        assert 'summary' in body
        assert 'metadata' in body
        assert body['summary'] == summary_text

        metadata = body['metadata']
        assert 'model_id' in metadata
        assert 'processing_time_ms' in metadata
        assert 'memos_included' in metadata
        assert 'memos_total' in metadata
        assert 'truncated' in metadata
        assert metadata['memos_included'] == 5
        assert metadata['memos_total'] == 5

    @patch('repositories.memo_repository.boto3')
    @patch('services.bedrock_service.boto3')
    def test_post_request_without_accept_header(
        self, mock_bedrock_boto3, mock_dynamodb_boto3
    ):
        """
        Test POST request without Accept header defaults to JSON format.

        **Validates: Requirements 1.3, 3.1 (backward compatibility)**
        """
        test_memos = create_test_memos(count=2, content_size=80)
        setup_mock_dynamodb(mock_dynamodb_boto3, test_memos)

        summary_text = "Default format test"
        mock_bedrock_boto3.client.return_value = MockBedrockClient(response_text=summary_text)

        event = {
            'body': '{}',
            'httpMethod': 'POST',
            'path': '/memos/summary',
            'headers': {},
        }

        response = lambda_handler(event, self.create_mock_context())

        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'application/json; charset=utf-8'

        body = json.loads(response['body'])
        assert 'summary' in body
        assert 'metadata' in body
        assert body['summary'] == summary_text

    @patch('repositories.memo_repository.boto3')
    @patch('services.bedrock_service.boto3')
    def test_response_format_matches_accept_header(
        self, mock_bedrock_boto3, mock_dynamodb_boto3
    ):
        """
        Test that response format matches the Accept header preference.

        **Validates: Requirements 1.1, 1.2, 1.3**
        """
        test_memos = create_test_memos(count=4, content_size=120)
        setup_mock_dynamodb(mock_dynamodb_boto3, test_memos)

        summary_text = "Format matching test"
        mock_bedrock_boto3.client.return_value = MockBedrockClient(response_text=summary_text)

        test_cases = [
            ('text/plain', 'text/plain; charset=utf-8', False),
            ('application/json', 'application/json; charset=utf-8', True),
            (None, 'application/json; charset=utf-8', True),
            ('*/*', 'application/json; charset=utf-8', True),
        ]

        for accept_header, expected_content_type, is_json in test_cases:
            event = {
                'body': '{}',
                'httpMethod': 'POST',
                'path': '/memos/summary',
                'headers': {'Accept': accept_header} if accept_header else {},
            }

            response = lambda_handler(event, self.create_mock_context())

            assert response['statusCode'] == 200, f"Failed for Accept: {accept_header}"
            assert response['headers']['Content-Type'] == expected_content_type, \
                f"Wrong Content-Type for Accept: {accept_header}"

            if is_json:
                body = json.loads(response['body'])
                assert 'summary' in body
                assert 'metadata' in body
            else:
                assert '📝 メモ要約結果' in response['body']
                assert summary_text in response['body']

    @patch('repositories.memo_repository.boto3')
    @patch('services.bedrock_service.boto3')
    def test_backward_compatibility_with_existing_clients(
        self, mock_bedrock_boto3, mock_dynamodb_boto3
    ):
        """
        Test backward compatibility: no Accept header → JSON with expected structure.

        **Validates: Requirement 3.1**
        """
        test_memos = create_test_memos(count=3, content_size=100)
        setup_mock_dynamodb(mock_dynamodb_boto3, test_memos)

        summary_text = "Backward compatibility test"
        mock_bedrock_boto3.client.return_value = MockBedrockClient(response_text=summary_text)

        event = {
            'body': '{}',
            'httpMethod': 'POST',
            'path': '/memos/summary',
            'headers': {},
        }

        response = lambda_handler(event, self.create_mock_context())

        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'application/json; charset=utf-8'

        body = json.loads(response['body'])
        assert 'summary' in body
        assert 'metadata' in body

        metadata = body['metadata']
        assert 'model_id' in metadata
        assert 'processing_time_ms' in metadata
        assert 'memos_included' in metadata
        assert 'memos_total' in metadata
        assert 'truncated' in metadata

        assert metadata['model_id'] == 'us.anthropic.claude-sonnet-4-6'
        assert isinstance(metadata['processing_time_ms'], int)
        assert metadata['processing_time_ms'] >= 0
        assert metadata['memos_included'] == 3
        assert metadata['memos_total'] == 3
        assert isinstance(metadata['truncated'], bool)

    @patch('repositories.memo_repository.boto3')
    @patch('services.bedrock_service.boto3')
    def test_case_insensitive_accept_header(
        self, mock_bedrock_boto3, mock_dynamodb_boto3
    ):
        """
        Test that lowercase 'accept' header is handled (API Gateway normalisation).
        """
        test_memos = create_test_memos(count=2, content_size=50)
        setup_mock_dynamodb(mock_dynamodb_boto3, test_memos)

        summary_text = "Case insensitive test"
        mock_bedrock_boto3.client.return_value = MockBedrockClient(response_text=summary_text)

        event = {
            'body': '{}',
            'httpMethod': 'POST',
            'path': '/memos/summary',
            'headers': {'accept': 'text/plain'},  # lowercase
        }

        response = lambda_handler(event, self.create_mock_context())

        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'text/plain; charset=utf-8'
        assert '📝 メモ要約結果' in response['body']

    @patch('repositories.memo_repository.boto3')
    @patch('services.bedrock_service.boto3')
    def test_cors_headers_present_in_all_responses(
        self, mock_bedrock_boto3, mock_dynamodb_boto3
    ):
        """
        Test that CORS headers are present regardless of response format.
        """
        test_memos = create_test_memos(count=1, content_size=50)
        setup_mock_dynamodb(mock_dynamodb_boto3, test_memos)
        mock_bedrock_boto3.client.return_value = MockBedrockClient(response_text="CORS test")

        for accept_header in ['text/plain', 'application/json']:
            event = {
                'body': '{}',
                'httpMethod': 'POST',
                'path': '/memos/summary',
                'headers': {'Accept': accept_header},
            }

            response = lambda_handler(event, self.create_mock_context())

            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
            assert 'Access-Control-Allow-Methods' in response['headers']
            assert 'POST, OPTIONS' in response['headers']['Access-Control-Allow-Methods']
            assert 'Access-Control-Allow-Headers' in response['headers']
            assert 'Content-Type, Accept' in response['headers']['Access-Control-Allow-Headers']
