import pytest
import time
from unittest.mock import Mock, patch
import json
import os
import sys
from datetime import datetime, timedelta

# Add the lambda directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat

@pytest.fixture
def mock_dynamodb():
    with patch('boto3.resource') as mock_resource:
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        yield mock_table

@pytest.fixture
def mock_bedrock():
    with patch('boto3.client') as mock_client:
        mock_bedrock = Mock()
        mock_client.return_value = mock_bedrock
        yield mock_bedrock

def test_count_tokens():
    """Test token counting functionality"""
    test_texts = [
        "Hello, world!",  # Short text
        "A" * 1000,      # Long text
        "🌟 emoji test", # Text with emoji
        "",              # Empty text
    ]
    
    for text in test_texts:
        token_count = chat.count_tokens(text)
        assert isinstance(token_count, int)
        assert token_count >= 0
        
        # Specific assertions
        if text == "":
            assert token_count == 0
        if text == "Hello, world!":
            assert token_count < 10  # Should be around 4-5 tokens

def test_get_or_create_session(mock_dynamodb):
    """Test session creation and retrieval"""
    user_id = "test_user"
    
    # Test session creation
    session_id = chat.get_or_create_session(user_id)
    
    # Verify DynamoDB put_item was called with correct arguments
    mock_dynamodb.put_item.assert_called_once()
    put_item_args = mock_dynamodb.put_item.call_args[1]['Item']
    
    assert 'sessionId' in put_item_args
    assert put_item_args['userId'] == user_id
    assert 'createdAt' in put_item_args
    assert 'ttl' in put_item_args
    assert put_item_args['totalTokens'] == 0
    
    # Verify TTL is set correctly (30 days from now)
    current_time = int(time.time())
    ttl_time = put_item_args['ttl']
    assert ttl_time > current_time
    assert ttl_time <= current_time + (31 * 24 * 60 * 60)  # Within 31 days

def test_trim_history_to_token_limit():
    """Test history trimming based on token limit"""
    # Create test messages
    messages = [
        {'content': 'Short message 1', 'timestamp': 1},
        {'content': 'A' * 1000, 'timestamp': 2},  # Long message
        {'content': 'Short message 2', 'timestamp': 3},
    ]
    
    # Test with very low token limit
    trimmed = chat.trim_history_to_token_limit(messages, max_tokens=20)
    assert len(trimmed) < len(messages)
    
    # Test with high token limit
    trimmed = chat.trim_history_to_token_limit(messages, max_tokens=10000)
    assert len(trimmed) == len(messages)

def test_save_message(mock_dynamodb):
    """Test message saving with token counting"""
    session_id = "test_session"
    role = "user"
    content = "Test message"
    
    chat.save_message(session_id, role, content)
    
    # Verify message was saved
    mock_dynamodb.put_item.assert_called_once()
    put_item_args = mock_dynamodb.put_item.call_args[1]['Item']
    
    assert put_item_args['sessionId'] == session_id
    assert put_item_args['role'] == role
    assert put_item_args['content'] == content
    assert 'tokens' in put_item_args
    assert put_item_args['tokens'] > 0

@pytest.mark.asyncio
async def test_handler_integration(mock_dynamodb, mock_bedrock):
    """Test the complete Lambda handler flow"""
    # Mock Bedrock response
    mock_response = {
        'body': Mock(
            read=Mock(return_value=json.dumps({
                'content': [{'text': 'Test response'}]
            }).encode())
        )
    }
    mock_bedrock.invoke_model.return_value = mock_response
    
    # Create test event
    event = {
        'body': json.dumps({
            'message': 'Test message',
            'sessionId': None
        }),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'test_user'
                }
            }
        }
    }
    
    # Mock chat history query response
    mock_dynamodb.query.return_value = {'Items': []}
    
    # Test handler
    response = chat.handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'sessionId' in body
    assert 'response' in body
    assert body['response'] == 'Test response'

def test_update_session_tokens(mock_dynamodb):
    """Test updating session token count"""
    session_id = "test_session"
    new_tokens = 100
    
    chat.update_session_tokens(session_id, new_tokens)
    
    mock_dynamodb.update_item.assert_called_once()
    update_args = mock_dynamodb.update_item.call_args[1]
    
    assert update_args['Key']['sessionId'] == session_id
    assert ':val' in update_args['ExpressionAttributeValues']
    assert update_args['ExpressionAttributeValues'][':val'] == new_tokens

def test_get_chat_history(mock_dynamodb):
    """Test chat history retrieval and pagination"""
    session_id = "test_session"
    
    # Mock first query response with LastEvaluatedKey
    mock_dynamodb.query.side_effect = [
        {
            'Items': [{'message': 'First batch'}],
            'LastEvaluatedKey': {'key': 'value'}
        },
        {
            'Items': [{'message': 'Second batch'}]
        }
    ]
    
    history = chat.get_chat_history(session_id)
    
    assert len(history) == 2
    assert mock_dynamodb.query.call_count == 2

if __name__ == '__main__':
    pytest.main([__file__])
