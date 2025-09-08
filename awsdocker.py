import os
import subprocess
from typing import Dict, Any
from tindatabase import RepoDatabase
import json
from tindatabase import RepoDatabase
from takeprompt import BedrockAgent
from awsbedrock import edit_the_file, is_multi_staged
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
        print("docker file created sucessfully!")
        # Build Docker image
        build_result = run_command(f"docker build -t {image_name} {cloned_repo_path}".split(' '))
        
        if not build_result.get("success"):
            return {"error": f"Docker build failed: {build_result.get('stderr')}"}
        print("docker build is sucess")
        # Push to ECR if build successful
        print("pushing to ECR")
        push_result = push_to_ecr(image_name)
        if not push_result.get("success"):
            return {"error": f"ECR push failed: {push_result.get('error')}"}
        compose_path = ''
#----------------------------------------------------------------------------
        # Create docker-compose.yml
        if is_multi_staged(project_name):
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
        print("Completed!)")
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
    """Build docker-compose.yml and Dockerfile with error correction"""
    try:
        print("rebuilding!!")
        # Get error message from database
        db = RepoDatabase()
        repo_data = db.get_repo_analysis(project_name) or {}
        error_msg = repo_data.get("errormsg", "")
        db.close()
        
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
        
        # Create comprehensive prompt for Bedrock
        prompt = f"""
        Fix the Docker configuration based on the error, if no error return the same dockerfile and cocker-compose.yml files. analyze the rror and rectify either Dockerfile or docker-compose file. analyze which file needs to be altered as per requirements:
        
        Project: {project_name}
        Path: {project_path}
        Error Message: {error_msg}
        Files Analysis: {' '.join(file_analysis[:10])}
        
        Return ONLY valid JSON with both files (no explanations or markdown):
        {{
            "dockerfile": "complete Dockerfile content",
            "docker_compose": "complete docker-compose.yml content"
        }}
        """
        
        # Get response from Bedrock
        agent = BedrockAgent()
        response = agent.get_bedrock_response(prompt)
        
        if not response or response.strip() == "":
            return {"error": "Empty response from Bedrock"}
        
        try:
            # Try to extract JSON from response if it contains extra text
            response = response.strip()
            if response.startswith('```json'):
                response = response.replace('```json', '').replace('```', '').strip()
            elif response.startswith('```'):
                response = response.replace('```', '').strip()
            
            files_content = json.loads(response)
            print(files_content)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON from Bedrock: {response[:200]}..."}
        except Exception as e:
            return {"error": f"Bedrock response error: {str(e)}"}
        
        # Write Dockerfile
        dockerfile_path = os.path.join(project_path, "Dockerfile")
        print(f"re-writing: {dockerfile_path}")
        with open(os.path.abspath(dockerfile_path), 'w', encoding='utf-8') as f:
            f.write(files_content.get("dockerfile", ""))
        # edit_the_file(dockerfile_path)
        
        # Write docker-compose.yml
        compose_path = os.path.join(project_path, "docker-compose.yml")
        print(f"re-writing: {compose_path}")
        print("**********************")
        print(files_content.get("docker_compose", ""))
        print("**********************")
        with open(os.path.abspath(compose_path), 'w', encoding='utf-8') as f:
            f.write(files_content.get("docker_compose", ""))
        # edit_the_file(compose_path)
        
        # Build using docker-compose
        original_cwd = os.getcwd()
        os.chdir(project_path)
        build_result = run_command(["docker", "compose", "build"])
        os.chdir(original_cwd)
        
        if not build_result.get("success"):
            # Store stderr in database
            try:
                db = RepoDatabase()
                existing_data = db.get_repo_analysis(project_name) or {}
                existing_data["errormsg"] = build_result.get('stderr', '')
                db.store_repo_analysis(project_name, existing_data)
                db.close()
            except:
                pass
            return {"error": f"Docker compose build failed: {build_result.get('stderr')}"}
        
        return {
            "success": True,
            "dockerfile_path": dockerfile_path,
            "compose_path": compose_path
        }
        
    except Exception as e:
        try:
            db = RepoDatabase()
            existing_data = db.get_repo_analysis(project_name) or {}
            existing_data["errormsg"] = str(e)
            db.store_repo_analysis(project_name, existing_data)
            db.close()
        except:
            pass
        return {"error": f"Build compose failed: {str(e)}"}