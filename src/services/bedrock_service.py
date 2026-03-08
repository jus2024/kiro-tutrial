"""
BedrockService - AWS Bedrock AI service integration
Handles AI invocations with retry logic for all-memos summary generation
"""
import boto3
import time
import json
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError


class ServiceUnavailableError(Exception):
    """Raised when AI service is unavailable after retries."""
    pass


class BedrockService:
    """Service for AWS Bedrock AI interactions with retry logic."""
    
    def __init__(
        self,
        model_id: str,
        region: str,
        max_retries: int = 3
    ):
        """
        Initialize Bedrock service.
        
        Args:
            model_id: Bedrock model identifier (e.g., 'us.anthropic.claude-sonnet-4-6')
            region: AWS region for Bedrock service (e.g., 'us-west-2')
            max_retries: Maximum number of retry attempts for retryable errors (default: 3)
        """
        self.model_id = model_id
        self.region = region
        self.max_retries = max_retries
        
        # Initialize boto3 bedrock-runtime client
        self.client = boto3.client('bedrock-runtime', region_name=region)
    
    def build_summary_prompt(self, aggregated_content: str, memo_count: int) -> str:
        """
        Build prompt for all-memos summary generation.
        
        Creates a Japanese prompt that guides the AI to generate a comprehensive
        summary of all memos, including themes, patterns, and key information.
        
        Args:
            aggregated_content: Combined memo content from all memos
            memo_count: Number of memos included in the aggregated content
            
        Returns:
            Formatted prompt string in Japanese for AI processing
        """
        prompt = f"""以下は{memo_count}件のメモの内容です。これらのメモ全体を分析し、包括的な要約を生成してください。

要約には以下の内容を含めてください：
- 全体的なテーマやトピック
- 重要な情報やポイント
- メモ間の関連性やパターン
- 主要な結論や洞察

メモの内容：

{aggregated_content}

上記のメモ全体を分析し、日本語で包括的な要約を生成してください。"""
        
        return prompt

    def generate_all_memos_summary(
        self,
        aggregated_content: str,
        memo_count: int
    ) -> str:
        """
        Generate summary of all memos using Bedrock.
        
        Orchestrates the full AI summary generation flow by building the prompt,
        creating the request body with correct model parameters, invoking Bedrock
        with retry logic, and returning the summary text.
        
        Args:
            aggregated_content: Combined memo content from all memos
            memo_count: Number of memos included in the aggregated content
            
        Returns:
            AI-generated summary text in Japanese
            
        Raises:
            ServiceUnavailableError: If retries exhausted after 3 attempts
            ClientError: For non-retryable Bedrock errors
        """
        # Build the prompt for summary generation
        prompt = self.build_summary_prompt(aggregated_content, memo_count)
        
        # Build request body with correct model parameters
        request_body = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 4096,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }
        
        # Invoke Bedrock with retry logic and return summary text
        summary_text = self.invoke_with_retry(request_body)
        
        return summary_text

    def invoke_with_retry(self, request_body: Dict[str, Any]) -> str:
        """
        Invoke Bedrock with exponential backoff retry.
        
        Implements retry logic for ThrottlingException and ServiceUnavailableException.
        Exponential backoff: 1s, 2s, 4s between attempts.
        
        Args:
            request_body: Bedrock API request body with model parameters
            
        Returns:
            AI response text extracted from Bedrock response
            
        Raises:
            ServiceUnavailableError: If all retries fail after max_retries attempts
            ClientError: For non-retryable errors
        """
        retryable_errors = ['ThrottlingException', 'ServiceUnavailableException']
        
        for attempt in range(self.max_retries):
            try:
                # Invoke Bedrock API
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body)
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                
                # Extract text from response
                # Claude response format: {"content": [{"text": "..."}]}
                if 'content' in response_body and len(response_body['content']) > 0:
                    return response_body['content'][0]['text']
                else:
                    raise ValueError("Unexpected response format from Bedrock")
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Check if error is retryable
                if error_code in retryable_errors:
                    # If this is the last attempt, raise ServiceUnavailableError
                    if attempt == self.max_retries - 1:
                        raise ServiceUnavailableError(
                            "AI service temporarily unavailable. Please try again later."
                        )
                    
                    # Wait with exponential backoff before retrying
                    # Exponential backoff: 2^attempt seconds (1s, 2s, 4s, 8s, ...)
                    delay = 2 ** attempt
                    time.sleep(delay)
                    continue
                else:
                    # Non-retryable error, raise immediately
                    raise
        
        # Should not reach here, but raise error just in case
        raise ServiceUnavailableError(
            "AI service temporarily unavailable. Please try again later."
        )
