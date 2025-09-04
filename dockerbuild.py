import subprocess
from typing import Dict, Any

def docker_build(directory_path: str, image_name: str) -> Dict[str, Any]:
    """Execute docker build command"""
    try:
        cmd = ["docker", "build", "-t", image_name, directory_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {"error": result.stderr, "output": result.stdout}
            
    except Exception as e:
        return {"error": f"Docker build failed: {str(e)}"}

def docker_compose_build(directory_path: str) -> Dict[str, Any]:
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