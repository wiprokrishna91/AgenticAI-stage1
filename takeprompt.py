import boto3
import json
import os

class BedrockAgent:
    def __init__(self, region_name: str = "us-east-1"):
            self.bedrock = boto3.client(
                'bedrock-runtime',
                region_name=region_name,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            self.model_id = "amazon.nova-lite-v1:0"

    def get_bedrock_response(self, prompt):
        """Takes a prompt and returns response from AWS Bedrock"""
        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"max_new_tokens": 1000, "temperature": 0.1}
        }
        
        response = self.bedrock.invoke_model(
            body=json.dumps(body),
            modelId=self.model_id
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['output']['message']['content'][0]['text']
    
    def _call_bedrock(self, prompt: str) -> str:
        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"max_new_tokens": 2000}
        }
        response = self.bedrock.invoke_model(modelId=self.model_id, body=json.dumps(body))
        response_body = json.loads(response['body'].read())
        return response_body['output']['message']['content'][0]['text']