import boto3
import json
import os
from typing import Dict, Any


def _analyze_project_structure(project_path: str) -> str:
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
        
        from takeprompt import BedrockAgent
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
    
