"""Unit tests for BedrockService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.services.bedrock_service import BedrockService


class TestBedrockServiceInitialization:
    """Test suite for BedrockService initialization."""
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_init_with_required_parameters(self, mock_boto_client):
        """Test initialization with required parameters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        assert service.model_id == 'us.anthropic.claude-sonnet-4-6'
        assert service.region == 'us-west-2'
        assert service.max_retries == 3  # Default value
        assert service.client == mock_client
        
        # Verify boto3 client was created with correct parameters
        mock_boto_client.assert_called_once_with(
            'bedrock-runtime',
            region_name='us-west-2'
        )
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_init_with_custom_max_retries(self, mock_boto_client):
        """Test initialization with custom max_retries."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2',
            max_retries=5
        )
        
        assert service.model_id == 'us.anthropic.claude-sonnet-4-6'
        assert service.region == 'us-west-2'
        assert service.max_retries == 5
        assert service.client == mock_client
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_init_with_different_region(self, mock_boto_client):
        """Test initialization with different AWS region."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-east-1'
        )
        
        assert service.region == 'us-east-1'
        
        # Verify boto3 client was created with correct region
        mock_boto_client.assert_called_once_with(
            'bedrock-runtime',
            region_name='us-east-1'
        )
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_init_with_different_model_id(self, mock_boto_client):
        """Test initialization with different model ID."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='anthropic.claude-3-5-sonnet-20241022-v2:0',
            region='us-west-2'
        )
        
        assert service.model_id == 'anthropic.claude-3-5-sonnet-20241022-v2:0'
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_client_is_bedrock_runtime(self, mock_boto_client):
        """Test that the client is initialized as bedrock-runtime."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        # Verify the service name is 'bedrock-runtime'
        mock_boto_client.assert_called_once()
        call_args = mock_boto_client.call_args
        assert call_args[0][0] == 'bedrock-runtime'



class TestBuildSummaryPrompt:
    """Test suite for build_summary_prompt method."""
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_build_prompt_with_single_memo(self, mock_boto_client):
        """Test prompt building with a single memo."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "タイトル: テストメモ\n内容: これはテストメモです。"
        memo_count = 1
        
        prompt = service.build_summary_prompt(aggregated_content, memo_count)
        
        # Verify prompt contains memo count
        assert "1件のメモ" in prompt
        
        # Verify prompt contains aggregated content
        assert aggregated_content in prompt
        
        # Verify prompt is in Japanese and contains key instructions
        assert "包括的な要約を生成してください" in prompt
        assert "全体的なテーマやトピック" in prompt
        assert "重要な情報やポイント" in prompt
        assert "メモ間の関連性やパターン" in prompt
        assert "主要な結論や洞察" in prompt
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_build_prompt_with_multiple_memos(self, mock_boto_client):
        """Test prompt building with multiple memos."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = """タイトル: メモ1
内容: 最初のメモです。

タイトル: メモ2
内容: 二番目のメモです。

タイトル: メモ3
内容: 三番目のメモです。"""
        memo_count = 3
        
        prompt = service.build_summary_prompt(aggregated_content, memo_count)
        
        # Verify prompt contains correct memo count
        assert "3件のメモ" in prompt
        
        # Verify prompt contains all aggregated content
        assert "メモ1" in prompt
        assert "メモ2" in prompt
        assert "メモ3" in prompt
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_build_prompt_with_japanese_characters(self, mock_boto_client):
        """Test prompt building with various Japanese characters."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        # Test with hiragana, katakana, and kanji
        aggregated_content = "ひらがな、カタカナ、漢字を含むメモです。"
        memo_count = 1
        
        prompt = service.build_summary_prompt(aggregated_content, memo_count)
        
        # Verify Japanese characters are preserved
        assert "ひらがな" in prompt
        assert "カタカナ" in prompt
        assert "漢字" in prompt
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_build_prompt_with_large_memo_count(self, mock_boto_client):
        """Test prompt building with large number of memos."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "大量のメモ内容"
        memo_count = 100
        
        prompt = service.build_summary_prompt(aggregated_content, memo_count)
        
        # Verify prompt contains correct memo count
        assert "100件のメモ" in prompt
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_build_prompt_structure(self, mock_boto_client):
        """Test that prompt has the expected structure."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "テスト内容"
        memo_count = 5
        
        prompt = service.build_summary_prompt(aggregated_content, memo_count)
        
        # Verify prompt structure
        # Should start with memo count introduction
        assert prompt.startswith("以下は5件のメモの内容です")
        
        # Should contain section header for memo content
        assert "メモの内容：" in prompt
        
        # Should end with instruction to generate summary
        assert prompt.endswith("上記のメモ全体を分析し、日本語で包括的な要約を生成してください。")
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_build_prompt_with_empty_content(self, mock_boto_client):
        """Test prompt building with empty aggregated content."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = ""
        memo_count = 0
        
        prompt = service.build_summary_prompt(aggregated_content, memo_count)
        
        # Verify prompt is still generated with 0 memos
        assert "0件のメモ" in prompt
        assert "包括的な要約を生成してください" in prompt
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_build_prompt_with_special_characters(self, mock_boto_client):
        """Test prompt building with special characters in content."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        # Test with newlines, quotes, and other special characters
        aggregated_content = 'メモ内容:\n"引用文"\n改行\tタブ'
        memo_count = 1
        
        prompt = service.build_summary_prompt(aggregated_content, memo_count)
        
        # Verify special characters are preserved
        assert '"引用文"' in prompt
        assert '\n' in prompt
        assert '\t' in prompt



class TestInvokeWithRetry:
    """Test suite for invoke_with_retry method."""
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_successful_invocation_on_first_attempt(self, mock_boto_client):
        """Test successful Bedrock invocation on first attempt."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful response
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Test summary"}]}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        request_body = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 4096,
            'messages': [{'role': 'user', 'content': 'Test prompt'}]
        }
        
        result = service.invoke_with_retry(request_body)
        
        assert result == "Test summary"
        assert mock_client.invoke_model.call_count == 1
        mock_client.invoke_model.assert_called_once_with(
            modelId='us.anthropic.claude-sonnet-4-6',
            body='{"anthropic_version": "bedrock-2023-05-31", "max_tokens": 4096, "messages": [{"role": "user", "content": "Test prompt"}]}'
        )
    
    @patch('src.services.bedrock_service.time.sleep')
    @patch('src.services.bedrock_service.boto3.client')
    def test_retry_on_throttling_exception(self, mock_boto_client, mock_sleep):
        """Test retry logic when ThrottlingException occurs."""
        from botocore.exceptions import ClientError
        from src.services.bedrock_service import ServiceUnavailableError
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # First two attempts fail with ThrottlingException, third succeeds
        throttling_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'invoke_model'
        )
        
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Success after retry"}]}'))
        }
        
        mock_client.invoke_model.side_effect = [
            throttling_error,
            throttling_error,
            mock_response
        ]
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        request_body = {'messages': [{'role': 'user', 'content': 'Test'}]}
        
        result = service.invoke_with_retry(request_body)
        
        assert result == "Success after retry"
        assert mock_client.invoke_model.call_count == 3
        
        # Verify exponential backoff delays: 1s, 2s
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
    
    @patch('src.services.bedrock_service.time.sleep')
    @patch('src.services.bedrock_service.boto3.client')
    def test_retry_on_service_unavailable_exception(self, mock_boto_client, mock_sleep):
        """Test retry logic when ServiceUnavailableException occurs."""
        from botocore.exceptions import ClientError
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # First attempt fails, second succeeds
        service_error = ClientError(
            {'Error': {'Code': 'ServiceUnavailableException', 'Message': 'Service unavailable'}},
            'invoke_model'
        )
        
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Success after retry"}]}'))
        }
        
        mock_client.invoke_model.side_effect = [
            service_error,
            mock_response
        ]
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        request_body = {'messages': [{'role': 'user', 'content': 'Test'}]}
        
        result = service.invoke_with_retry(request_body)
        
        assert result == "Success after retry"
        assert mock_client.invoke_model.call_count == 2
        
        # Verify first backoff delay: 1s
        mock_sleep.assert_called_once_with(1)
    
    @patch('src.services.bedrock_service.time.sleep')
    @patch('src.services.bedrock_service.boto3.client')
    def test_all_retries_exhausted_raises_service_unavailable(self, mock_boto_client, mock_sleep):
        """Test that ServiceUnavailableError is raised after all retries fail."""
        from botocore.exceptions import ClientError
        from src.services.bedrock_service import ServiceUnavailableError
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # All 3 attempts fail with ThrottlingException
        throttling_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'invoke_model'
        )
        
        mock_client.invoke_model.side_effect = [
            throttling_error,
            throttling_error,
            throttling_error
        ]
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2',
            max_retries=3
        )
        
        request_body = {'messages': [{'role': 'user', 'content': 'Test'}]}
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            service.invoke_with_retry(request_body)
        
        assert "AI service temporarily unavailable" in str(exc_info.value)
        assert mock_client.invoke_model.call_count == 3
        
        # Verify all backoff delays were used: 1s, 2s
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_non_retryable_error_raises_immediately(self, mock_boto_client):
        """Test that non-retryable errors are raised immediately without retry."""
        from botocore.exceptions import ClientError
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Non-retryable error (ValidationException)
        validation_error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid request'}},
            'invoke_model'
        )
        
        mock_client.invoke_model.side_effect = validation_error
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        request_body = {'messages': [{'role': 'user', 'content': 'Test'}]}
        
        with pytest.raises(ClientError) as exc_info:
            service.invoke_with_retry(request_body)
        
        assert exc_info.value.response['Error']['Code'] == 'ValidationException'
        # Should only be called once (no retries)
        assert mock_client.invoke_model.call_count == 1
    
    @patch('src.services.bedrock_service.time.sleep')
    @patch('src.services.bedrock_service.boto3.client')
    def test_exponential_backoff_delays(self, mock_boto_client, mock_sleep):
        """Test that exponential backoff uses correct delays: 1s, 2s, 4s."""
        from botocore.exceptions import ClientError
        from src.services.bedrock_service import ServiceUnavailableError
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # All attempts fail to verify all backoff delays
        throttling_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'invoke_model'
        )
        
        mock_client.invoke_model.side_effect = [
            throttling_error,
            throttling_error,
            throttling_error
        ]
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2',
            max_retries=3
        )
        
        request_body = {'messages': [{'role': 'user', 'content': 'Test'}]}
        
        with pytest.raises(ServiceUnavailableError):
            service.invoke_with_retry(request_body)
        
        # Verify exponential backoff: 1s after first failure, 2s after second failure
        assert mock_sleep.call_count == 2
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert calls == [1, 2]
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_response_parsing_with_valid_format(self, mock_boto_client):
        """Test that response is correctly parsed from Bedrock format."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock response with Claude format
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Parsed summary text"}]}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        request_body = {'messages': [{'role': 'user', 'content': 'Test'}]}
        
        result = service.invoke_with_retry(request_body)
        
        assert result == "Parsed summary text"
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_response_parsing_with_invalid_format_raises_error(self, mock_boto_client):
        """Test that invalid response format raises ValueError."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock response with invalid format (missing content)
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"invalid": "format"}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        request_body = {'messages': [{'role': 'user', 'content': 'Test'}]}
        
        with pytest.raises(ValueError) as exc_info:
            service.invoke_with_retry(request_body)
        
        assert "Unexpected response format" in str(exc_info.value)
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_response_parsing_with_empty_content_array(self, mock_boto_client):
        """Test that empty content array raises ValueError."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock response with empty content array
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": []}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        request_body = {'messages': [{'role': 'user', 'content': 'Test'}]}
        
        with pytest.raises(ValueError) as exc_info:
            service.invoke_with_retry(request_body)
        
        assert "Unexpected response format" in str(exc_info.value)
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_request_body_serialization(self, mock_boto_client):
        """Test that request body is correctly serialized to JSON."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Test"}]}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        request_body = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 4096,
            'messages': [{'role': 'user', 'content': 'Test prompt'}]
        }
        
        service.invoke_with_retry(request_body)
        
        # Verify the body parameter is a JSON string
        call_args = mock_client.invoke_model.call_args
        assert 'body' in call_args.kwargs
        body_arg = call_args.kwargs['body']
        assert isinstance(body_arg, str)
        assert '"anthropic_version": "bedrock-2023-05-31"' in body_arg
        assert '"max_tokens": 4096' in body_arg
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_response_with_japanese_text(self, mock_boto_client):
        """Test that Japanese text in response is correctly handled."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock response with Japanese text
        japanese_text = "これは日本語のテスト要約です。"
        mock_response = {
            'body': Mock(read=Mock(return_value=f'{{"content": [{{"text": "{japanese_text}"}}]}}'.encode('utf-8')))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        request_body = {'messages': [{'role': 'user', 'content': 'Test'}]}
        
        result = service.invoke_with_retry(request_body)
        
        assert result == japanese_text
        assert "日本語" in result


class TestGenerateAllMemosSummary:
    """Test suite for generate_all_memos_summary method."""
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_generate_summary_with_single_memo(self, mock_boto_client):
        """Test summary generation with a single memo."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful Bedrock response
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Generated summary for single memo"}]}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "タイトル: テストメモ\n内容: これはテストメモです。"
        memo_count = 1
        
        result = service.generate_all_memos_summary(aggregated_content, memo_count)
        
        assert result == "Generated summary for single memo"
        
        # Verify invoke_model was called once
        assert mock_client.invoke_model.call_count == 1
        
        # Verify request body structure
        call_args = mock_client.invoke_model.call_args
        assert call_args.kwargs['modelId'] == 'us.anthropic.claude-sonnet-4-6'
        
        # Parse the body to verify structure
        import json
        body = json.loads(call_args.kwargs['body'])
        assert body['anthropic_version'] == 'bedrock-2023-05-31'
        assert body['max_tokens'] == 4096
        assert len(body['messages']) == 1
        assert body['messages'][0]['role'] == 'user'
        assert '1件のメモ' in body['messages'][0]['content']
        assert aggregated_content in body['messages'][0]['content']
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_generate_summary_with_multiple_memos(self, mock_boto_client):
        """Test summary generation with multiple memos."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful Bedrock response
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Generated summary for multiple memos"}]}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = """タイトル: メモ1
内容: 最初のメモです。

タイトル: メモ2
内容: 二番目のメモです。"""
        memo_count = 2
        
        result = service.generate_all_memos_summary(aggregated_content, memo_count)
        
        assert result == "Generated summary for multiple memos"
        
        # Verify request body contains correct memo count
        call_args = mock_client.invoke_model.call_args
        import json
        body = json.loads(call_args.kwargs['body'])
        assert '2件のメモ' in body['messages'][0]['content']
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_generate_summary_request_body_structure(self, mock_boto_client):
        """Test that request body has correct structure for Bedrock API."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful Bedrock response
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Test summary"}]}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "テスト内容"
        memo_count = 5
        
        service.generate_all_memos_summary(aggregated_content, memo_count)
        
        # Verify request body structure
        call_args = mock_client.invoke_model.call_args
        import json
        body = json.loads(call_args.kwargs['body'])
        
        # Verify required fields
        assert 'anthropic_version' in body
        assert body['anthropic_version'] == 'bedrock-2023-05-31'
        
        assert 'max_tokens' in body
        assert body['max_tokens'] == 4096
        
        assert 'messages' in body
        assert isinstance(body['messages'], list)
        assert len(body['messages']) == 1
        
        # Verify message structure
        message = body['messages'][0]
        assert message['role'] == 'user'
        assert 'content' in message
        assert isinstance(message['content'], str)
        assert len(message['content']) > 0
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_generate_summary_with_japanese_content(self, mock_boto_client):
        """Test summary generation with Japanese content."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock response with Japanese summary
        japanese_summary = "これは全メモの要約です。主なテーマは技術とビジネスです。"
        mock_response = {
            'body': Mock(read=Mock(return_value=f'{{"content": [{{"text": "{japanese_summary}"}}]}}'.encode('utf-8')))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "日本語のメモ内容です。"
        memo_count = 3
        
        result = service.generate_all_memos_summary(aggregated_content, memo_count)
        
        assert result == japanese_summary
        assert "要約" in result
        assert "テーマ" in result
    
    @patch('src.services.bedrock_service.time.sleep')
    @patch('src.services.bedrock_service.boto3.client')
    def test_generate_summary_with_retry_on_throttling(self, mock_boto_client, mock_sleep):
        """Test that generate_all_memos_summary retries on throttling errors."""
        from botocore.exceptions import ClientError
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # First attempt fails with throttling, second succeeds
        throttling_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'invoke_model'
        )
        
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Success after retry"}]}'))
        }
        
        mock_client.invoke_model.side_effect = [
            throttling_error,
            mock_response
        ]
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "テスト内容"
        memo_count = 1
        
        result = service.generate_all_memos_summary(aggregated_content, memo_count)
        
        assert result == "Success after retry"
        assert mock_client.invoke_model.call_count == 2
        mock_sleep.assert_called_once_with(1)
    
    @patch('src.services.bedrock_service.time.sleep')
    @patch('src.services.bedrock_service.boto3.client')
    def test_generate_summary_raises_service_unavailable_after_retries(self, mock_boto_client, mock_sleep):
        """Test that ServiceUnavailableError is raised after all retries fail."""
        from botocore.exceptions import ClientError
        from src.services.bedrock_service import ServiceUnavailableError
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # All attempts fail with throttling
        throttling_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'invoke_model'
        )
        
        mock_client.invoke_model.side_effect = [
            throttling_error,
            throttling_error,
            throttling_error
        ]
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "テスト内容"
        memo_count = 1
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            service.generate_all_memos_summary(aggregated_content, memo_count)
        
        assert "AI service temporarily unavailable" in str(exc_info.value)
        assert mock_client.invoke_model.call_count == 3
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_generate_summary_raises_client_error_for_non_retryable_errors(self, mock_boto_client):
        """Test that non-retryable errors are raised immediately."""
        from botocore.exceptions import ClientError
        
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Non-retryable error
        validation_error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid request'}},
            'invoke_model'
        )
        
        mock_client.invoke_model.side_effect = validation_error
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "テスト内容"
        memo_count = 1
        
        with pytest.raises(ClientError) as exc_info:
            service.generate_all_memos_summary(aggregated_content, memo_count)
        
        assert exc_info.value.response['Error']['Code'] == 'ValidationException'
        # Should only be called once (no retries)
        assert mock_client.invoke_model.call_count == 1
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_generate_summary_with_large_memo_count(self, mock_boto_client):
        """Test summary generation with large number of memos."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful Bedrock response
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Summary of 100 memos"}]}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService(
            model_id='us.anthropic.claude-sonnet-4-6',
            region='us-west-2'
        )
        
        aggregated_content = "大量のメモ内容"
        memo_count = 100
        
        result = service.generate_all_memos_summary(aggregated_content, memo_count)
        
        assert result == "Summary of 100 memos"
        
        # Verify request contains correct memo count
        call_args = mock_client.invoke_model.call_args
        import json
        body = json.loads(call_args.kwargs['body'])
        assert '100件のメモ' in body['messages'][0]['content']
    
    @patch('src.services.bedrock_service.boto3.client')
    def test_generate_summary_uses_correct_model_id(self, mock_boto_client):
        """Test that generate_all_memos_summary uses the correct model ID."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful Bedrock response
        mock_response = {
            'body': Mock(read=Mock(return_value=b'{"content": [{"text": "Test summary"}]}'))
        }
        mock_client.invoke_model.return_value = mock_response
        
        # Test with different model ID
        custom_model_id = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
        service = BedrockService(
            model_id=custom_model_id,
            region='us-west-2'
        )
        
        aggregated_content = "テスト内容"
        memo_count = 1
        
        service.generate_all_memos_summary(aggregated_content, memo_count)
        
        # Verify correct model ID was used
        call_args = mock_client.invoke_model.call_args
        assert call_args.kwargs['modelId'] == custom_model_id
