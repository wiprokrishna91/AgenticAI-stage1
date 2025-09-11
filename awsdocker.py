import os
import subprocess
from typing import Dict, Any
from tindatabase import RepoDatabase
import json
import sqlite3

from clone_database import CloneDatabase
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
        build_result = run_command(f"docker build -q -t {image_name} {cloned_repo_path}".split(' '))
        
        if not build_result.get("success"):
            return {"error": f"Docker build failed: {build_result.get('stderr')}"}
        image_ID = build_result.get("stdout",'')
        # Push to ECR if build successful
        print("pushing to ECR")
        push_result = push_to_ecr(image_name, image_ID)
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
            "compose_path": 'compose_path'
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

def build_compose(repo_id: str, project_path: str) -> Dict[str, Any]:
    """Build docker-compose.yml and Dockerfile with error correction"""
    try:
        print("build_compose")
        # Get error from database
        clone_db = CloneDatabase()
        conn = sqlite3.connect(clone_db.db_path)
        cursor = conn.execute('SELECT error FROM docker_status WHERE repoID = ?', (repo_id,))
        existing_status = cursor.fetchone()
        error_var = existing_status[0] if existing_status and existing_status[0] else None
        conn.close()
        print(f"Retrieved error from DB: {error_var}")
        if error_var is None:
            print("error is None")
        # No error, run docker compose build directly
            original_cwd = os.getcwd()
            os.chdir(project_path)
            print("building docker!")
            build_result = run_command(["docker", "compose", "build"])
            os.chdir(original_cwd)
            print(build_result)
            if build_result.get("success"):
                return {
                    "success": True,
                    "dockerfile_path": os.path.join(project_path, "Dockerfile"),
                    "compose_path": os.path.join(project_path, "docker-compose.yml")
                }
            else:
                docker_data = {
                "project_path": project_path,
                "status": "failed",
                "imageID": "",
                "image_name": 'image_name',
                "error": build_result.get('stderr')
                        }
                clone_db.store_docker_status(repo_id, docker_data)
        ai_analysis_content = ""
        ai_report_path = os.path.join(project_path, "AIanalysis_report.txt")
        if os.path.exists(ai_report_path):
            try:
                with open(ai_report_path, 'r', encoding='utf-8') as f:
                    ai_analysis_content = f.read()
                print(f"Found AI analysis report: {ai_report_path}")
            except Exception as e:
                print(f"Error reading AI analysis report: {e}")
                ai_analysis_content = ""
        # Error exists, retry 5 times
        for attempt in range(1):
            print(f"Retry attempt {attempt + 1}/5")
            print(f"Error: {error_var}")
           
            # Read existing Dockerfile and docker-compose.yml
            existing_dockerfile = ""
            existing_compose = ""
            
            dockerfile_path = os.path.join(project_path, "Dockerfile")
            if os.path.exists(dockerfile_path):
                try:
                    with open(dockerfile_path, 'r', encoding='utf-8') as f:
                        existing_dockerfile = f.read()
                except Exception as e:
                    print(f"Error reading Dockerfile: {e}")
            
            compose_path = os.path.join(project_path, "docker-compose.yml")
            if os.path.exists(compose_path):
                try:
                    with open(compose_path, 'r', encoding='utf-8') as f:
                        existing_compose = f.read()
                except Exception as e:
                    print(f"Error reading docker-compose.yml: {e}")
            # Create prompt for Bedrock
            prompt = f"""

            Analyze the following Error Message recieved while running docker-compose.yml or dockerfile. read the error message and identify if the error is in Dockerfile or docker-compose.yml.
            note the error message and make the changes to dockerfile or docker compose and create a new Dockerfile and Docker-compose file. 
            read the 'repo Analysis Report' for reference. adding the existing Dockerfile and docker-compose.yml.
            Fix the Docker configuration based on the error, if no error return the same dockerfile and cocker-compose.yml files. analyze the rror and rectify either Dockerfile or docker-compose file. analyze which file needs to be altered as per requirements:
            Error Message: {error_var}
            existing Dockerfile: {existing_dockerfile}
            existing docker-compose.yml: {existing_compose}
            "repo Analysis Report: " + {ai_analysis_content if ai_analysis_content else ""}
            
            Return ONLY valid JSON with both files:
            {{
                "dockerfile": "complete Dockerfile content",
                "docker_compose": "complete docker-compose.yml content"
            }}
            """
            
            # Get response from Bedrock
            agent = BedrockAgent()
            bedrock_response = agent.get_bedrock_response(prompt)
            
            if not bedrock_response or bedrock_response.strip() == "":
                continue
            try:
                dd = json.loads(bedrock_response[7:-3])
                print(dd)
                # Extract Dockerfile content
                print("editing dockerfile")

                # dockerfile_path = os.path.join(project_path, "Dockerfile")
                # dockerfile_start = bedrock_response.find('```dockerfile')
                # if dockerfile_start != -1:
                #     print("one if")
                #     dockerfile_start += len('```dockerfile')
                #     dockerfile_end = bedrock_response.find('```', dockerfile_start)
                #     if dockerfile_end != -1:
                #         print("two if")
                #         dockerfile_content = bedrock_response[dockerfile_start:dockerfile_end].strip()
                #         with open(dockerfile_path, 'w', encoding='utf-8') as f:
                #             f.write(dockerfile_content)
                #         edit_the_file(dockerfile_path)
                #         print("Dockerfile created successfully!")
                # print("editing docker-compose")
                # # Extract docker-compose.yml content
                # compose_start = bedrock_response.find('```yaml')
                # if compose_start != -1:
                #     print("one if")
                #     compose_start += len('```yaml')
                #     compose_end = bedrock_response.find('```', compose_start)
                #     if compose_end != -1:
                #         print("two if")
                #         compose_content = bedrock_response[compose_start:compose_end].strip()
                #         compose_path = os.path.join(project_path, "docker-compose.yml")
                #         with open(compose_path, 'w', encoding='utf-8') as f:
                #             f.write(compose_content)
                #         print(compose_content)
                #         edit_the_file(compose_path)
                #         print("docker-compose.yml created successfully!")
                
                # Try build
                original_cwd = os.getcwd()
                os.chdir(project_path)
                build_result = run_command(["docker", "compose", "build"])
                os.chdir(original_cwd)
                
                if build_result.get("success"):
                    return {
                        "success": True,
                        "dockerfile_path": dockerfile_path,
                        "compose_path": compose_path
                    }
                else:
                    error_var = build_result.get('stderr', '')
                    print(error_var)
                    docker_data = {
                "project_path": project_path,
                "status": "failed",
                "imageID": "",
                "image_name": 'image_name',
                "error": error_var
                        }
                    clone_db.store_docker_status(repo_id, docker_data)
                    continue
                    
            except Exception as e:
                continue
        
            return {"error": "Failed after 5 retry attempts"}
        
    except Exception as e:
        return {"error": f"Build compose failed: {str(e)}"}
