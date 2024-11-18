import json
import os
import time
import uuid
import boto3
from typing import Dict, List
import tiktoken

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime')

# Get table names from environment variables
CHAT_SESSIONS_TABLE = os.environ['CHAT_SESSIONS_TABLE']
CHAT_MESSAGES_TABLE = os.environ['CHAT_MESSAGES_TABLE']

# Constants
MAX_TOKENS = 200000  # Claude 3's context window
DAYS_TO_KEEP = 30    # Number of days to keep chat history
TOKEN_BUFFER = 1000  # Buffer for new messages

def count_tokens(text: str) -> int:
    """Count the number of tokens in a text using tiktoken."""
    encoding = tiktoken.get_encoding("cl100k_base")  # Claude uses cl100k_base
    return len(encoding.encode(text))

def get_or_create_session(user_id: str, session_id: str = None) -> str:
    """Get existing session or create a new one."""
    sessions_table = dynamodb.Table(CHAT_SESSIONS_TABLE)
    
    if not session_id:
        session_id = str(uuid.uuid4())
        sessions_table.put_item(
            Item={
                'sessionId': session_id,
                'userId': user_id,
                'createdAt': int(time.time()),
                'ttl': int(time.time()) + (DAYS_TO_KEEP * 24 * 60 * 60),  # 30 days TTL
                'totalTokens': 0
            }
        )
    return session_id

def update_session_tokens(session_id: str, new_tokens: int):
    """Update the total token count for a session."""
    sessions_table = dynamodb.Table(CHAT_SESSIONS_TABLE)
    sessions_table.update_item(
        Key={'sessionId': session_id},
        UpdateExpression='SET totalTokens = totalTokens + :val',
        ExpressionAttributeValues={':val': new_tokens}
    )

def get_chat_history(session_id: str) -> List[Dict]:
    """Retrieve chat history for a session."""
    messages_table = dynamodb.Table(CHAT_MESSAGES_TABLE)
    
    # Get all messages for the session
    messages = []
    last_evaluated_key = None
    
    while True:
        if last_evaluated_key:
            response = messages_table.query(
                KeyConditionExpression='sessionId = :sid',
                ExpressionAttributeValues={':sid': session_id},
                ExclusiveStartKey=last_evaluated_key,
                ScanIndexForward=True  # Get oldest messages first
            )
        else:
            response = messages_table.query(
                KeyConditionExpression='sessionId = :sid',
                ExpressionAttributeValues={':sid': session_id},
                ScanIndexForward=True
            )
        
        messages.extend(response.get('Items', []))
        last_evaluated_key = response.get('LastEvaluatedKey')
        
        if not last_evaluated_key:
            break
    
    return messages

def trim_history_to_token_limit(messages: List[Dict], max_tokens: int = MAX_TOKENS - TOKEN_BUFFER) -> List[Dict]:
    """Trim message history to fit within token limit."""
    total_tokens = 0
    trimmed_messages = []
    
    # Count tokens from newest to oldest
    for message in reversed(messages):
        message_tokens = count_tokens(message['content'])
        if total_tokens + message_tokens > max_tokens:
            break
        total_tokens += message_tokens
        trimmed_messages.insert(0, message)
    
    return trimmed_messages

def save_message(session_id: str, role: str, content: str):
    """Save a message to the chat history."""
    messages_table = dynamodb.Table(CHAT_MESSAGES_TABLE)
    token_count = count_tokens(content)
    
    # Save the message
    messages_table.put_item(
        Item={
            'sessionId': session_id,
            'timestamp': int(time.time() * 1000),
            'role': role,
            'content': content,
            'tokens': token_count
        }
    )
    
    # Update session token count
    update_session_tokens(session_id, token_count)

def create_claude_messages(history: List[Dict], new_message: str) -> List[Dict]:
    """Create message format for Claude."""
    messages = []
    for msg in history:
        messages.append({
            'role': msg['role'],
            'content': msg['content']
        })
    messages.append({
        'role': 'user',
        'content': new_message
    })
    return messages

def invoke_claude(messages: List[Dict]) -> str:
    """Invoke Claude model via Bedrock."""
    body = {
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': 1000,
        'messages': messages,
        'temperature': 0.7,
    }
    
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        contentType='application/json',
        accept='application/json',
        body=json.dumps(body)
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['content'][0]['text']

def handler(event, context):
    """Lambda handler for chat functionality."""
    try:
        # Parse request body
        body = json.loads(event['body'])
        message = body['message']
        session_id = body.get('sessionId')
        
        # Get user ID from Cognito authorizer
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # Get or create session
        session_id = get_or_create_session(user_id, session_id)
        
        # Get chat history
        history = get_chat_history(session_id)
        
        # Trim history to fit within token limit
        trimmed_history = trim_history_to_token_limit(history)
        
        # Create messages for Claude
        claude_messages = create_claude_messages(trimmed_history, message)
        
        # Get response from Claude
        response = invoke_claude(claude_messages)
        
        # Save both user message and Claude's response
        save_message(session_id, 'user', message)
        save_message(session_id, 'assistant', response)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'sessionId': session_id,
                'response': response
            }),
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True,
            }
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True,
            }
        }
