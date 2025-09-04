import boto3
import os
import base64
from typing import Dict, Any
from submodule import run_command

def push_to_ecr(image_name: str) -> Dict[str, Any]:
    """Push Docker image to AWS ECR with all necessary steps"""
    try:
        # Get environment variables
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        aws_account_id = os.getenv('AWS_ACCOUNT_ID')
        
        if not all([aws_access_key, aws_secret_key, aws_account_id]):
            return {"error": "Missing AWS credentials or account ID in environment variables"}
        
        # Create ECR client
        ecr_client = boto3.client(
            'ecr',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Extract repository name from image name.MAKE SURE  YOPU GIVE YOUR REPONAME IN ECR
        repo_name = image_name.split(':')[0].lower()
        
        # Create ECR repository if it doesn't exist
        try:
            ecr_client.create_repository(repositoryName=repo_name)
        except ecr_client.exceptions.RepositoryAlreadyExistsException:
            pass
        
        # Get ECR login token
        token_response = ecr_client.get_authorization_token()
        token = token_response['authorizationData'][0]['authorizationToken']
        username, password = base64.b64decode(token).decode().split(':')
        ecr_endpoint = f"{aws_account_id}.dkr.ecr.{aws_region}.amazonaws.com"
        
        # Docker login to ECR
        login_cmd = ["docker", "login", "--username", username, "--password", password, ecr_endpoint]
        login_result = run_command(login_cmd)
        
        if not login_result.get("success"):
            return {"error": f"ECR login failed: {login_result.get('stderr')}"}
        
        # Tag image for ECR
        ecr_uri = f"{ecr_endpoint}/{repo_name}:latest"
        tag_cmd = ["docker", "tag", image_name, ecr_uri]
        tag_result = run_command(tag_cmd)
        
        if not tag_result.get("success"):
            return {"error": f"Image tagging failed: {tag_result.get('stderr')}"}
        
        # Push image to ECR
        push_cmd = ["docker", "push", ecr_uri]
        push_result = run_command(push_cmd)
        
        if not push_result.get("success"):
            return {"error": f"Image push failed: {push_result.get('stderr')}"}
        
        return {
            "success": True,
            "ecr_uri": ecr_uri,
            "repository_name": repo_name,
            "message": f"Image pushed successfully to {ecr_uri}"
        }
        
    except Exception as e:
        return {"error": f"ECR push failed: {str(e)}"}