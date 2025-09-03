import boto3
import json
import os
from typing import Dict, Any

class BedrockDockerAgent:
    def __init__(self, region_name: str = "us-east-1"):
        self.bedrock = boto3.client(
            'bedrock-runtime',
            region_name=region_name,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        self.model_id = "amazon.nova-lite-v1:0"
    
    def analyze_project_and_create_dockerfile(self, project_path: str) -> str:
        project_info = self._analyze_project_structure(project_path)
        
        prompt = f"""
        Analyze this project and create a Dockerfile:
        
        Project: {project_path}
        Structure: {project_info}
        
        Return only the Dockerfile content.
        """
        
        response = self._call_bedrock(prompt)
        dockerfile_path = os.path.join(project_path, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write(response.strip())
        return dockerfile_path
    
    def _analyze_project_structure(self, project_path: str) -> str:
        structure = []
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            level = root.replace(project_path, '').count(os.sep)
            indent = ' ' * 2 * level
            structure.append(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files[:10]:
                structure.append(f"{subindent}{file}")
        return '\n'.join(structure[:50])
    
    def _call_bedrock(self, prompt: str) -> str:
        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"max_new_tokens": 2000}
        }
        response = self.bedrock.invoke_model(modelId=self.model_id, body=json.dumps(body))
        response_body = json.loads(response['body'].read())
        return response_body['output']['message']['content'][0]['text']
    
    def analyze_project_for_docker(self, project_path: str) -> Dict[str, Any]:
        if not os.path.exists(project_path):
            return {"error": f"Directory '{project_path}' not found"}
        
        project_info = self._analyze_project_structure(project_path)
        key_files_content = self._read_key_files(project_path)
        
        prompt = f"""
        Go through each directory not more than 3 deapths and except for modules/library directories. scan each line to check which all languages are used and frontend and backend applications are used.
        provided below is the repository name and details. go through each settings,configuration and yaml files to get maximum details from each. need specific ports used by frontend and backend and databse applications.
        
        Project: {project_path}
        Structure: {project_info}
        Key Files: {key_files_content}
        
        Return JSON:
        {{
            "port": "detected_port_number",
            "database: : "if any"
            "image_name": "suggested_image_name",
            "container_name": "suggested_container_name",
            "project_type": "python/nodejs/java/other",
            "build_instructions": "how to build this project",
        }}
        """
        
        try:
            ai_response = self._call_bedrock(prompt)
            try:
                ai_config = json.loads(ai_response.strip())
            except:
                ai_config = {
                    "port": None,
                    "image_name": f"app-{os.path.basename(project_path)}".lower(),
                    "container_name": f"container-{os.path.basename(project_path)}".lower(),
                    "project_type": "python"
                }
            return {"success": True, "ai_analysis": ai_config}
        except Exception as e:
            return {"error": f"Bedrock analysis failed: {str(e)}"}
    
    def _read_key_files(self, project_path: str) -> str:
        key_files = ["app.py", "main.py", "server.js", "package.json", "requirements.txt"]
        content = []
        for file in key_files:
            file_path = os.path.join(project_path, file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()[:500]
                        content.append(f"{file}: {file_content}")
                except:
                    continue
        return "\n".join(content)
    
