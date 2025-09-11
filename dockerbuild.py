import subprocess
from typing import Dict, Any
import os
import sqlite3
from clone_database import CloneDatabase
from takeprompt import BedrockAgent
from awsbedrock import edit_the_file

def docker_build(repo_name: str, image_name: str, repo_id: str) -> Dict[str, Any]:
    """Execute docker build command"""
    try:
        cloned_repo_path = f"cloned_repos/{repo_name}"
        
        # Check docker_status table first
        clone_db = CloneDatabase()
        conn = sqlite3.connect(clone_db.db_path)
        cursor = conn.execute('SELECT status FROM docker_status WHERE repoID = ?', (repo_id,))
        existing_status = cursor.fetchone()
        conn.close()
        
        # If status is already success, return early
        # if existing_status and existing_status[0] == 'success':
        #     print("Docker already built successfully")
        #     return {"success": True, "message": "Docker already built successfully"}
        
        # Read AIanalysis_report.txt if exists
        ai_analysis_content = ""
        ai_report_path = os.path.join(cloned_repo_path, "AIanalysis_report.txt")
        if os.path.exists(ai_report_path):
            try:
                with open(ai_report_path, 'r', encoding='utf-8') as f:
                    ai_analysis_content = f.read()
                print(f"Found AI analysis report: {ai_report_path}")
            except Exception as e:
                print(f"Error reading AI analysis report: {e}")
                ai_analysis_content = ""
        
        # Check if Dockerfile exists, if not create it
        dockerfile_path = os.path.join(cloned_repo_path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            # Analyze files and create Dockerfile using Bedrock
            file_analysis = []
            for root, dirs, files in os.walk(cloned_repo_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()[:500]
                            file_analysis.append(f"{file}: {content}")
                    except:
                        continue
            
            # Create prompt for Bedrock
            prompt = f"""
            Analyze the following project files and create a Dockerfile and Docker-compose file. read the 'repo Analysis Report'
            note each major points from coding languages to config files, settings, database each and every major point points.
            create a dockerfile and docker-compose file which is a production level precesion and images should be a known and perfect :
            Project: {repo_name}
            Files analysis: {' '.join(file_analysis[:10])}
            "repo Analysis Report: " + {ai_analysis_content if ai_analysis_content else ""}
            
            Create a complete Dockerfile that can build and run this project and Docker-compose that can create a containarized image.
            Return only the Dockerfile and docker-compose.yml content without any explanations.
            """
            print("prompt given")
            # Get Dockerfile content from Bedrock
            agent = BedrockAgent()
            bedrock_response = agent.get_bedrock_response(prompt)
            if not bedrock_response:
                return {"error": "Failed to get content from Bedrock"}
            
            # Extract Dockerfile content
            print("editing dockerfile")
            dockerfile_start = bedrock_response.find('```dockerfile')
            if dockerfile_start != -1:
                dockerfile_start += len('```dockerfile')
                dockerfile_end = bedrock_response.find('```', dockerfile_start)
                if dockerfile_end != -1:
                    dockerfile_content = bedrock_response[dockerfile_start:dockerfile_end].strip()
                    with open(dockerfile_path, 'w', encoding='utf-8') as f:
                        f.write(dockerfile_content)
                    edit_the_file(dockerfile_path)
                    print("Dockerfile created successfully!")
            print("editing docker-compose")
            # Extract docker-compose.yml content
            compose_start = bedrock_response.find('```yaml')
            if compose_start != -1:
                compose_start += len('```yaml')
                compose_end = bedrock_response.find('```', compose_start)
                if compose_end != -1:
                    compose_content = bedrock_response[compose_start:compose_end].strip()
                    compose_path = os.path.join(cloned_repo_path, "docker-compose.yml")
                    with open(compose_path, 'w', encoding='utf-8') as f:
                        f.write(compose_content)
                    edit_the_file(compose_path)
                    print("docker-compose.yml created successfully!")
        
        # # Build Docker image
        # cmd = ["docker", "build", "-t", image_name, cloned_repo_path]
        # result = subprocess.run(cmd, capture_output=True, text=True)
        
        # if result.returncode == 0:
            # Update docker_status table with success
        docker_data = {
                "project_path": cloned_repo_path,
                "status": "success",
                "imageID":"nil",
                "image_name": image_name,
                "error": ''
            }
        clone_db.store_docker_status(repo_id, docker_data)
            
        return {"success": True, "output": "Dcoker files craeted successfully", "dockerfile_path": dockerfile_path}
            
    except Exception as e:
        docker_data = {
                "project_path": cloned_repo_path,
                "status": "failed",
                "imageID": "",
                "image_name": image_name,
                "error": str(e)
            }
        clone_db.store_docker_status(repo_id, docker_data)
        return {"error": f"Docker build failed: {str(e)}"}
    finally:
        if 'clone_db' in locals():
            clone_db.close()

def docker_compose_build(repo_name: str) -> Dict[str, Any]:
    """Execute docker-compose build command"""
    try:
        cmd = ["docker-compose", "build"]
        result = subprocess.run(cmd, cwd=directory_path, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {"error": result.stderr, "output": result.stdout}
            
    except Exception as e:
        return {"error": f"Docker compose build failed: {str(e)}"}