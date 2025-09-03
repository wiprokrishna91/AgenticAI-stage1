import boto3
import json
from botocore.exceptions import ClientError

def query_amazon_q(prompt: str) -> dict:
    """
    Send prompt to Amazon Q and return JSON response
    """
    try:
        # Initialize Amazon Q client
        client = boto3.client('qbusiness')
        
        # Send message to Amazon Q
        response = client.chat_sync(
            applicationId='your-application-id',  # Replace with your Q application ID
            # userMessage=prompt,
            userMessage={
            'sourceAttributionFilter': {
                'exclude': [],
                'include': []
            },
            'text': prompt
        },
            conversationId=None  # New conversation
        )
        


        # Return structured JSON response
        return {
            "success": True,
            "response": response.get('systemMessage', ''),
            "conversation_id": response.get('conversationId', ''),
            "source_attributions": response.get('sourceAttributions', [])
        }
        
    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": e.response['Error']['Code']
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def chat_with_bedrock_nova(prompt: str) -> dict:
    """
    Send prompt to Amazon Bedrock Nova model and return JSON response
    """
    try:
        # Initialize Bedrock client
        client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Prepare request body for Nova model
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 100,
                "temperature": 0.7
            }
        }
        
        # Invoke Nova model
        response = client.converse(
            modelId='amazon.nova-micro-v1:0',
            messages=body['messages'],
            inferenceConfig=body['inferenceConfig']
        )
        
        # Extract response text
        response_text = response['output']['message']['content'][0]['text']
        
        return {
            "success": True,
            "response": response_text,
            "model": "amazon.nova-micro-v1:0",
            "usage": response.get('usage', {})
        }
        
    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": e.response['Error']['Code']
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }