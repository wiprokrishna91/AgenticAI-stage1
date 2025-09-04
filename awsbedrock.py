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
    
    def analyze_project_and_create_dockerfile(self, project_path: str) -> tuple:
        project_info = self._analyze_project_structure(project_path)
        
        prompt = f"""
        We have the existing Dockerfile in the directory. Go through each directory not more than 3 deapths. scan each line to check which all languages are used and frontend and backend applications are used and which all pods needs to be create for the docker to be deployed.
        Compare the existing Dockerfile and build new Dockerfile. go through each settings,configuration see for the databases, important is the ports examine each. need specific ports used by frontend and backend and databse applications.
        Project Structure:
        Project: {project_path}
        
        Return only the Dockerfile content, do not include any line starting from special character and no comments.
        """
        dedicated_port = []
        response = self._call_bedrock(prompt)
        dockerfile_path = os.path.join(project_path, "Dockerfile1")
        with open(dockerfile_path, 'w') as f:
            f.write(response.strip())
    
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
        
        prompt = f"""
        Go through each directory not more than 3 deapths and except for modules/library directories. scan each line to check which all coding languages are used and frontend and backend applications are used.
        provided below is the repository name and details. go through each settings,configuration and yaml files to get maximum details from each. need specific ports used by frontend and backend and database applications.
        
        Project: {project_path}
        
        Return JSON:
        {{
            "port": "detected_port_number",
            "database: : "if any"
            "project_type": what is the project type,
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
    
    def analyze_project_for_docker2(self, analeses: str) -> dict:
       
        prompt = f"""
        Create a Dockerfile for on this analysis: {analeses}. read the above project type, modules used, check for the ports and then if asny databases are required. Write docker file for this requirement.
            Return only Dockerfile content without comments or special characters
        """
        
        try:
            ai_response = self._call_bedrock(prompt)
            return {"success": True, "ai_analysis": ai_response}
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
    
