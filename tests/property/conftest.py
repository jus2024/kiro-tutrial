"""
Shared fixtures for property tests.
"""

import pytest
from moto import mock_aws
import boto3
from unittest.mock import patch, MagicMock


@pytest.fixture(scope='function', autouse=True)
def aws_credentials():
    """Mock AWS credentials for moto."""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'


@pytest.fixture(scope='function')
def mock_bedrock_and_dynamodb():
    """Create mock DynamoDB table and Bedrock client for AI property testing."""
    with mock_aws():
        # Create DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
        table = dynamodb.create_table(
            TableName='test-memo-table',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'entity_type', 'AttributeType': 'S'},
                {'AttributeName': 'updated_at', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UpdatedAtIndex',
                    'KeySchema': [
                        {'AttributeName': 'entity_type', 'KeyType': 'HASH'},
                        {'AttributeName': 'updated_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Mock Bedrock client
        mock_bedrock_response = {
            'body': MagicMock()
        }
        mock_bedrock_response['body'].read.return_value = b'{"completion": "This is a mock AI answer based on the memo content."}'
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = MagicMock()
            mock_bedrock.invoke_model.return_value = mock_bedrock_response
            
            # Store original client function
            original_client = boto3.client
            
            def client_factory(service_name, **kwargs):
                if service_name == 'bedrock-runtime':
                    return mock_bedrock
                # For DynamoDB, return the real client (within moto context)
                return original_client(service_name, **kwargs)
            
            mock_boto_client.side_effect = client_factory
            
            yield table
