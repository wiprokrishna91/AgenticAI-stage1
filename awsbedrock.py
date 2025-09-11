import boto3
import json
import os
from typing import Dict, Any
from tindatabase import RepoDatabase
from takeprompt import BedrockAgent
from fileanalysis import analyse_repo_completely, list_packages, find_config_files
from clone_database import CloneDatabase
import time

def _analyze_project_structure(project_path: str) -> str:
    structure = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
        level = root.replace(project_path, '').count(os.sep)
        indent = ' ' * 2 * level
        structure.append(f"{indent}{os.path.basename(root)}")
        subindent = ' ' * 2 * (level + 1)
        for file in files[:10]:
            structure.append(f"{subindent}{file}")
    return '\n'.join(structure[:50])

def edit_the_file(file_path: str):
    """Read Dockerfile from given path and remove lines starting with special characters"""
    try:
        
        if not os.path.exists(file_path):
            return {"error": "Dockerfile not found in cloned_repos directory"}
        
        # Read original Dockerfile
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        lines = original_content.split('\n')
        cleaned_lines = []
        removed_lines = []
        
        special_chars = ['`', '#', '*', '-', '+', '>', '<', '!', '@', '$', '%', '^', '&', '(', ')', '[', ']', '{', '}', '|', '\\', '/', '?', '~']
        
        for i, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line and any(stripped_line.startswith(char) for char in special_chars):
                removed_lines.append(f"Line {i}: {line}")
            else:
                cleaned_lines.append(line)
        
        # Write cleaned content back to Dockerfile
        cleaned_content = '\n'.join(cleaned_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
    except Exception as e:
        return {"error": f"Failed to edit the files: {str(e)}"}

def get_docker_build_command(project_path: str) -> str:
    """Get exact docker build command from Dockerfile"""
    try:
        dockerfile_path = os.path.join(project_path, "Dockerfile")
        
        if not os.path.exists(dockerfile_path):
            return "docker build -t myapp ."
        
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
            dockerfile_content = f.read()
        
        
        agent = BedrockAgent()
        
        prompt = f"""
        Based on this Dockerfile content, provide the exact docker build command:
        
        {dockerfile_content}
        
        Return only the docker build command, nothing else.
        """
        
        build_command = agent.get_bedrock_response(prompt)
        return build_command.strip()
        
    except Exception as e:
        return f"docker build -t myapp {project_path}"
    
def is_multi_staged(repo_name):
    db = RepoDatabase()
    repo_data = db.get_repo_analysis(repo_name)
    analysis_repo = repo_data.get("ai_analysis",'')
    agent = BedrockAgent()
    is_multi_staged = agent.get_bedrock_response(f"""
                              providing the string{analysis_repo}scan this string and the provided just return the value for multistaged key paramater, the return data should only be true or false depending on what is it saved in the provided string.
                              Return only true or false no other details required
                                """)
    return is_multi_staged


def analyze_repo_details(repo_name: str) -> Dict[str, Any]:
    """Analyze repository details including packages and config files"""
    try:
        # Get project path and repo_id from cloned_repo table
        clone_db = CloneDatabase()
        repos = clone_db.get_all_cloned_repos()
        project_path = None
        repo_id = None
        
        for repo in repos:
            if repo['repo_name'] == repo_name:
                project_path = repo['clone_path']
                repo_id = repo['repoID']
                repo_url = repo['repo_url']
                break
        
        if not project_path or not os.path.exists(project_path) or not repo_id:
            clone_db.close()
            return {"success": False, "error": "Repository not found or path invalid"}
        print("recived repo")
        # Get packages and config files
        packages = list_packages(project_path)
        config_files = find_config_files(project_path)
        print(f"packages: {packages}")
        print(f"config_files: {config_files}")
        
        # Check if file with repoID exists and read its content
        repo_file_path = os.path.join(project_path, f"{repo_id}.json")
        repo_file_content = ""
        if os.path.exists(repo_file_path):
            try:
                with open(repo_file_path, 'r', encoding='utf-8') as f:
                    repo_file_content = f.read()
                print(f"Found repo file: {repo_file_path}")
            except Exception as e:
                print(f"Error reading repo file: {e}")
                repo_file_content = ""
        # Send to Bedrock for analysis
        agent = BedrockAgent()
        prompt = f"""
        Analyze this repository data and provide insights, analyze ib brif and get the coding languages used. analyze the repository with latest all possible coding languages.
        Analyze the repository, config files, amd packages. gvie the all possible details to generate the containerized image. coding language, databses, ports, frontend backend network structures, environtment variaables everything:
        Repository: {repo_url}
        Packages: {json.dumps(packages, indent=2)}
        Config Files: {json.dumps(config_files, indent=2)}
        {"Repository Analysis File: " + repo_file_content if repo_file_content else ""}
        """
        print("Bedrockagent called")
        ai_response = agent.get_bedrock_response(prompt)
        print(ai_response)
        
        # Validate Bedrock response
        if ai_response.startswith("Error:"):
            raise Exception(f"Bedrock API error: {ai_response}")
        
        if not ai_response or len(ai_response.strip()) < 10:
            raise Exception("Bedrock returned empty or invalid response")
        # Store analysis in AnalyzeRepo table
        analysis_data = {
            "repoID": repo_id,
            "projectPath": project_path,
            "codelang": packages,
            "aiAnalysis": ai_response,
            "modified_at": time.time(),
            "bedrockModel": agent.model_id,
            "database": "",
            "databaseport": 0
        }
        
        clone_db.store_analyze_repo(repo_id, analysis_data)
        clone_db.close()
        
        # Create AIanalysis_report.txt file in project path
        report_file_path = os.path.join(project_path, "AIanalysis_report.txt")
        with open(report_file_path, 'w', encoding='utf-8') as f:
            f.write(analysis_data['aiAnalysis'])
        
        return {"success": True, "analysis": analysis_data['aiAnalysis']}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

