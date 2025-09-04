import os
import subprocess
from typing import Dict, Any
from tindatabase import RepoDatabase
import json
from tindatabase import RepoDatabase
from takeprompt import BedrockAgent
from awsbedrock import edit_the_file
from submodule import run_command
import time
from Dockerpush import push_to_ecr


def build_and_run_docker(project_name: str, image_name: str = '', container_name: str = '') -> Dict[str, Any]:
    """Build and run Docker image for the containerize route"""
    try:
        cloned_repo_path = f"cloned_repos/{project_name}"
        image_name = image_name+str(time.monotonic()).split('.')[-1]
        # Analyze all files in cloned_repo directory
        file_analysis = []
        for root, dirs, files in os.walk(cloned_repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()[:500]  # First 500 chars
                        file_analysis.append(f"{file}: {content}")
                except:
                    continue
        
        # Create prompt for Bedrock
        prompt = f"""
        Analyze the following project files and create a Dockerfile:
        Project: {project_name}
        Files analysis: {' '.join(file_analysis[:10])}
        
        Create a complete Dockerfile that can build and run this project.
        Return only the Dockerfile content without any explanations.
        """
        
        # Get Dockerfile content from Bedrock
        agent = BedrockAgent()
        dockerfile_content = agent.get_bedrock_response(prompt)
        
        # Write Dockerfile to cloned_repos
        dockerfile_path = os.path.join(cloned_repo_path, "Dockerfile")
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        edit_the_file(dockerfile_path)
        
        # Build Docker image
        build_result = run_command(f"docker build -t {image_name} {cloned_repo_path}".split(' '))
        
        if not build_result.get("success"):
            return {"error": f"Docker build failed: {build_result.get('stderr')}"}
        
        # Push to ECR if build successful
        push_result = push_to_ecr(image_name)
        if not push_result.get("success"):
            return {"error": f"ECR push failed: {push_result.get('error')}"}
#----------------------------------------------------------------------------
        # Create docker-compose.yml
        def create_docker_compose():
            compose_prompt = f"""
            Analyze the following project files and create a docker-compose.yml:
            Project: {project_name}
            Files analysis: {' '.join(file_analysis[:10])}
            
            Create a complete docker-compose.yml that can orchestrate this project.
            Return only the docker-compose.yml content without any explanations.
            """
            
            compose_content = agent.get_bedrock_response(compose_prompt)
            compose_path = os.path.join(cloned_repo_path, "docker-compose.yml")
            with open(compose_path, 'w', encoding='utf-8') as f:
                f.write(compose_content)
            edit_the_file(compose_path)
            return compose_path
        
        compose_path = create_docker_compose()
        return {
            "success": True,
            "dockerfile_path": dockerfile_path,
            "compose_path": compose_path
        }
        
    except Exception as e:
        try:
            db = RepoDatabase()
            existing_data = db.get_repo_analysis(project_name) or {}
            existing_data["latest_error"] = str(e)
            db.store_repo_analysis(project_name, existing_data)
            db.close()
        except:
            pass
        return {"error": f"Build and run failed: {str(e)}"}

def build_compose(project_name: str, project_path: str) -> Dict[str, Any]:
    """Build docker-compose.yml file"""
    try:
        # Analyze all files in project directory
        file_analysis = []
        for root, dirs, files in os.walk(project_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()[:500]
                        file_analysis.append(f"{file}: {content}")
                except:
                    continue
        
        # Create prompt for Bedrock
        compose_prompt = f"""
        Analyze the following project files and create a docker-compose.yml:
        Project: {project_name}
        path: {project_path}
        Files analysis: {' '.join(file_analysis[:10])}
        
        Create a complete docker-compose.yml that can orchestrate this project.
        Return only the docker-compose.yml content without any explanations.
        """
        
        # Get compose content from Bedrock
        agent = BedrockAgent()
        compose_content = agent.get_bedrock_response(compose_prompt)
        
        # Write docker-compose.yml
        compose_path = os.path.join(project_path, "docker-compose.yml")
        with open(compose_path, 'w', encoding='utf-8') as f:
            f.write(compose_content)
        edit_the_file(compose_path)
        return {
            "success": True,
            "compose_path": compose_path
        }
        
    except Exception as e:
        try:
            db = RepoDatabase()
            existing_data = db.get_repo_analysis(project_name) or {}
            existing_data["latest_error"] = str(e)
            db.store_repo_analysis(project_name, existing_data)
            db.close()
        except:
            pass
        return {"error": f"Build compose failed: {str(e)}"}