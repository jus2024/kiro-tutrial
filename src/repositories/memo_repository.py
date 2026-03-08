"""
DynamoDB repository for memo operations.

This module provides the data access layer for memo CRUD operations using DynamoDB.
"""

import os
import base64
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

from models.memo import Memo


class MemoNotFoundError(Exception):
    """Raised when a memo is not found in the database."""
    
    def __init__(self, memo_id: str):
        self.memo_id = memo_id
        super().__init__(f"Memo not found: {memo_id}")


class MemoRepository:
    """
    Repository class for DynamoDB memo operations.
    
    Handles all database interactions for memo CRUD operations using
    single-table design with GSI for efficient querying.
    """
    
    def __init__(self, table_name: Optional[str] = None):
        """
        Initialize the repository with DynamoDB table.
        
        Args:
            table_name: DynamoDB table name (defaults to MEMO_TABLE_NAME env var)
        """
        self.table_name = table_name or os.environ.get('MEMO_TABLE_NAME')
        if not self.table_name:
            raise ValueError("MEMO_TABLE_NAME environment variable not set")
        
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(self.table_name)
    
    def create_memo(self, memo: Memo) -> Memo:
        """
        Create a new memo in DynamoDB.
        
        Args:
            memo: Memo object to create
            
        Returns:
            The created Memo object
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        item = memo.to_dynamodb_item()
        
        self.table.put_item(Item=item)
        
        return memo
    
    def get_memo(self, memo_id: str) -> Memo:
        """
        Retrieve a memo by ID from DynamoDB.
        
        Args:
            memo_id: UUID of the memo to retrieve
            
        Returns:
            Memo object
            
        Raises:
            MemoNotFoundError: If memo does not exist
            ClientError: If DynamoDB operation fails
        """
        response = self.table.get_item(
            Key={'PK': f'MEMO#{memo_id}'}
        )
        
        if 'Item' not in response:
            raise MemoNotFoundError(memo_id)
        
        item = response['Item']
        return self._item_to_memo(item)
    
    def list_memos(
        self,
        page_size: int = 20,
        next_token: Optional[str] = None
    ) -> Tuple[List[Memo], Optional[str]]:
        """
        List memos sorted by update timestamp in descending order.
        
        Uses the UpdatedAtIndex GSI to query memos by entity_type and sort by updated_at.
        
        Args:
            page_size: Number of memos to return (default 20, max 100)
            next_token: Pagination token from previous request
            
        Returns:
            Tuple of (list of Memo objects, next_token for pagination or None)
            
        Raises:
            ClientError: If DynamoDB operation fails
        """
        # Cap page size at 100
        page_size = min(page_size, 100)
        
        query_params = {
            'IndexName': 'UpdatedAtIndex',
            'KeyConditionExpression': 'entity_type = :entity_type',
            'ExpressionAttributeValues': {
                ':entity_type': 'MEMO'
            },
            'ScanIndexForward': False,  # Descending order (most recent first)
            'Limit': page_size
        }
        
        # Add pagination token if provided
        if next_token:
            try:
                exclusive_start_key = json.loads(base64.b64decode(next_token).decode('utf-8'))
                query_params['ExclusiveStartKey'] = exclusive_start_key
            except (ValueError, json.JSONDecodeError):
                # Invalid token, ignore and start from beginning
                pass
        
        response = self.table.query(**query_params)
        
        # Convert items to Memo objects
        memos = [self._item_to_memo(item) for item in response.get('Items', [])]
        
        # Generate next token if there are more results
        new_next_token = None
        if 'LastEvaluatedKey' in response:
            last_key = response['LastEvaluatedKey']
            new_next_token = base64.b64encode(
                json.dumps(last_key).encode('utf-8')
            ).decode('utf-8')
        
        return memos, new_next_token
    
    def update_memo(
        self,
        memo_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        updated_at: Optional[datetime] = None
    ) -> Memo:
        """
        Update an existing memo in DynamoDB.
        
        Uses conditional update to ensure memo exists before updating.
        
        Args:
            memo_id: UUID of the memo to update
            title: New title (optional)
            content: New content (optional)
            updated_at: New update timestamp (defaults to current time)
            
        Returns:
            Updated Memo object
            
        Raises:
            MemoNotFoundError: If memo does not exist
            ClientError: If DynamoDB operation fails
        """
        if updated_at is None:
            updated_at = datetime.utcnow()
        
        # Build update expression dynamically based on provided fields
        update_parts = []
        expression_values = {}
        
        if title is not None:
            update_parts.append('title = :title')
            expression_values[':title'] = title
        
        if content is not None:
            update_parts.append('content = :content')
            expression_values[':content'] = content
        
        # Always update the timestamp
        update_parts.append('updated_at = :updated_at')
        expression_values[':updated_at'] = updated_at.isoformat()
        
        if not update_parts:
            # No fields to update, just retrieve and return
            return self.get_memo(memo_id)
        
        update_expression = 'SET ' + ', '.join(update_parts)
        
        try:
            response = self.table.update_item(
                Key={'PK': f'MEMO#{memo_id}'},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ConditionExpression='attribute_exists(PK)',  # Ensure memo exists
                ReturnValues='ALL_NEW'
            )
            
            item = response['Attributes']
            return self._item_to_memo(item)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise MemoNotFoundError(memo_id)
            raise
    
    def delete_memo(self, memo_id: str) -> None:
        """
        Delete a memo from DynamoDB.
        
        Uses conditional delete to ensure memo exists before deletion.
        
        Args:
            memo_id: UUID of the memo to delete
            
        Raises:
            MemoNotFoundError: If memo does not exist
            ClientError: If DynamoDB operation fails
        """
        try:
            self.table.delete_item(
                Key={'PK': f'MEMO#{memo_id}'},
                ConditionExpression='attribute_exists(PK)'  # Ensure memo exists
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise MemoNotFoundError(memo_id)
            raise
    
    def _item_to_memo(self, item: Dict) -> Memo:
        """
        Convert DynamoDB item to Memo object.
        
        Args:
            item: DynamoDB item dictionary
            
        Returns:
            Memo object
        """
        return Memo(
            id=item['id'],
            title=item['title'],
            content=item['content'],
            created_at=datetime.fromisoformat(item['created_at']),
            updated_at=datetime.fromisoformat(item['updated_at'])
        )
