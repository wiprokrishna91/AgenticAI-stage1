import os
import subprocess
from typing import Dict, Any
from awsbedrock import BedrockDockerAgent

def check_docker_daemon() -> Dict[str, Any]:
    """Check if Docker daemon is running"""
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return {"running": True, "message": "Docker daemon is running"}
        else:
            return {"running": False, "error": result.stderr}
    except subprocess.TimeoutExpired:
        return {"running": False, "error": "Docker daemon timeout"}
    except FileNotFoundError:
        return {"running": False, "error": "Docker not installed"}
    except Exception as e:
        return {"running": False, "error": str(e)}

def start_docker_daemon() -> Dict[str, Any]:
    """Attempt to start Docker daemon on Windows"""
    try:
        # Try starting Docker Desktop
        subprocess.run(["powershell", "-Command", "Start-Process 'Docker Desktop'"], 
                      capture_output=True, timeout=30)
        
        # Wait and check if daemon started
        import time
        time.sleep(10)
        
        daemon_check = check_docker_daemon()
        if daemon_check.get("running"):
            return {"success": True, "message": "Docker daemon started successfully"}
        else:
            return {"error": "Failed to start Docker daemon", "details": daemon_check}
    except Exception as e:
        return {"error": f"Failed to start Docker: {str(e)}"}

def build_docker_image(directory_path: str, image_name: str) -> Dict[str, Any]:
    """Build Docker image from directory"""
    try:
        if not os.path.exists(directory_path):
            return {"error": f"Directory '{directory_path}' not found"}
        
        dockerfile_path = os.path.join(directory_path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            return {"error": f"Dockerfile not found in '{directory_path}'"}
        
        # Build Docker image
        build_cmd = ["docker", "build", "-t", image_name, directory_path]
        build_result = subprocess.run(build_cmd, capture_output=True, text=True)
        
        if build_result.returncode != 0:
            return {
                "error": f"Docker build failed: {build_result.stderr}",
                "build_output": build_result.stdout
            }
        
        return {
            "success": True,
            "image_name": image_name,
            "build_output": build_result.stdout
        }
        
    except Exception as e:
        return {"error": f"Failed to build Docker image: {str(e)}"}

def run_docker_container(image_name: str, container_name: str, port: str = '') -> Dict[str, Any]:
    """Run Docker container from image"""
    try:
        # Run Docker container
        run_cmd = ["docker", "run", "-d", "--name", container_name]
        
        if port:
            run_cmd.extend(["-p", f"{port}:{port}"])
        
        run_cmd.append(image_name)
        run_result = subprocess.run(run_cmd, capture_output=True, text=True)
        
        if run_result.returncode != 0:
            return {
                "error": f"Docker run failed: {run_result.stderr}",
                "run_output": run_result.stdout
            }
        
        return {
            "success": True,
            "container_name": container_name,
            "container_id": run_result.stdout.strip(),
            "port": port,
            "url": f"http://localhost:{port}" if port else None
        }
        
    except Exception as e:
        return {"error": f"Failed to run Docker container: {str(e)}"}

def build_and_run_docker(directory_path: str, image_name: str = '', container_name: str = '') -> Dict[str, Any]:
    """Build and run Docker image with AI-powered configuration detection"""
    
    # Use AI to analyze project first
    agent = BedrockDockerAgent()
    analysis = agent.analyze_project_for_docker(directory_path)
    key_parameters = ['ports','databases']
    if not analysis.get("success"):
        return {"error": f"Project analysis failed: {analysis.get('error')}"}
    
    ai_config = analysis.get("ai_analysis", {})
    
    # Use AI recommendations or fallback to provided values
    final_image_name = image_name or ai_config.get("image_name", f"app-{os.path.basename(directory_path)}").lower()
    final_container_name = container_name or ai_config.get("container_name", f"container-{os.path.basename(directory_path)}").lower()
    detected_port = ai_config.get("port")
    
    # Check Docker daemon
    daemon_check = check_docker_daemon()
    if not daemon_check.get("running"):
        start_result = start_docker_daemon()
        if "error" in start_result:
            return {
                "error": "Docker daemon not running",
                "suggestion": "Start Docker Desktop manually"
            }
    
    # Generate Dockerfile if needed using AI
    dockerfile_path = os.path.join(directory_path, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        dockerfile_result = agent.analyze_project_and_create_dockerfile(directory_path)
        if not dockerfile_result:
            return {"error": "Failed to generate Dockerfile"}
    
    # Build Docker image
    build_result = build_docker_image(directory_path, final_image_name)
    if not build_result.get("success"):
        return build_result
    
    # Run Docker container
    run_result = run_docker_container(final_image_name, final_container_name, detected_port)
    if not run_result.get("success"):
        return run_result
    
    return {
        "success": True,
        "image_name": final_image_name,
        "container_name": final_container_name,
        "container_id": run_result.get("container_id"),
        "port": detected_port,
        "url": f"http://localhost:{detected_port}" if detected_port else None,
        "ai_analysis": ai_config,
        "build_output": build_result.get("build_output")
    }

def stop_docker_container(container_name: str) -> Dict[str, Any]:
    """Stop Docker container"""
    try:
        result = subprocess.run(["docker", "stop", container_name], capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "message": f"Container '{container_name}' stopped"}
        else:
            return {"error": f"Failed to stop container: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to stop container: {str(e)}"}

def remove_docker_container(container_name: str) -> Dict[str, Any]:
    """Remove Docker container"""
    try:
        result = subprocess.run(["docker", "rm", container_name], capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "message": f"Container '{container_name}' removed"}
        else:
            return {"error": f"Failed to remove container: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to remove container: {str(e)}"}

def list_docker_containers() -> Dict[str, Any]:
    """List all Docker containers"""
    try:
        result = subprocess.run(["docker", "ps", "-a"], capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "containers": result.stdout}
        else:
            return {"error": f"Failed to list containers: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to list containers: {str(e)}"}

def list_docker_images() -> Dict[str, Any]:
    """List all Docker images"""
    try:
        result = subprocess.run(["docker", "images"], capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "images": result.stdout}
        else:
            return {"error": f"Failed to list images: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to list images: {str(e)}"}