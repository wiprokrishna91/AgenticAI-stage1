import os
import subprocess
from typing import Dict, Any
from awsbedrock import BedrockDockerAgent
from tindatabase import RepoDatabase
import json
from tindatabase import RepoDatabase
import numpy

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

def run_docker_container(image_name: str, container_name: str, port, cmd) -> Dict[str, Any]:
    """Run Docker container from image"""
    try:
        if cmd:
            cmd[-1] = image_name
            print(cmd)
            run_result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            # Run Docker container
            run_cmd = ["docker", "run", "-d", "-p", f"{port}:{port}", "--name", container_name]
            print(run_cmd)
            # if port:
            #     run_cmd.extend(["-p", f"{port}:{port}"])
            
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

def validate_the_dockerfile() -> Dict[str, Any]:
    """Read Dockerfile from cloned_repos and remove lines starting with special characters"""
    try:
        dockerfile_path = os.path.join("cloned_repos", "Dockerfile")
        
        if not os.path.exists(dockerfile_path):
            return {"error": "Dockerfile not found in cloned_repos directory"}
        
        # Read original Dockerfile
        with open(dockerfile_path, 'r', encoding='utf-8') as f:
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
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        return {
            "success": True,
            "message": "Dockerfile cleaned successfully",
            "removed_lines_count": len(removed_lines),
            "removed_lines": removed_lines,
            "cleaned_dockerfile_path": dockerfile_path,
            "content": cleaned_content
        }
        
    except Exception as e:
        return {"error": f"Failed to clean Dockerfile: {str(e)}"}

def create_dockerfile_from_prompt(prompt: str) -> Dict[str, Any]:
    """Create Dockerfile in cloned_repos directory from given prompt"""
    try:
        cloned_repos_path = "cloned_repos"
        if not os.path.exists(cloned_repos_path):
            os.makedirs(cloned_repos_path)
        
        dockerfile_path = os.path.join(cloned_repos_path, "Dockerfile")
        
        # Use BedrockDockerAgent to generate Dockerfile from prompt
        agent = BedrockDockerAgent()
        dockerfile_content = agent.analyze_project_for_docker2(prompt[7:-3])
        if not dockerfile_content:
            return {"error": "Failed to generate Dockerfile content from prompt"}
        # Write Dockerfile to cloned_repos directory
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content['ai_analysis'])

        run_comand = get_docker_run_command_from_prompt(dockerfile_content['ai_analysis'])
        if run_comand.get("error"):
            raise Exception("Unable to build docker through command")
        return {
            "success": True,
            "message": "Dockerfile created successfully from prompt",
            "dockerfile_path": dockerfile_path,
            "run": run_comand 
        }
        
    except Exception as e:
        return {"error": f"Failed to create Dockerfile from prompt: {str(e)}"}

def docker_commands_from_prompt(prompt: str) -> Dict[str, Any]:
    """Extract docker build command from prompt containing Dockerfile"""
    try:
        agent = BedrockDockerAgent()
        build_command = agent._call_bedrock(prompt)
        if not build_command:
            return {"error": "Failed to get docker details"}
        
        return {
            "success": True,
            "build_command": build_command.strip()
        }
        
    except Exception as e:
        return {"error": f"Failed to get docker build command: {str(e)}"}

def get_docker_run_command_from_prompt(prompt: str) -> Dict[str, Any]:
    """Extract docker build command from prompt containing Dockerfile"""
    try:
        agent = BedrockDockerAgent()
        build_command = agent._call_bedrock(
            f"From this Dockerfile content: {prompt}, generate only the docker run command. Return just the command without any explanation."
        )
        
        if not build_command:
            return {"error": "Failed to generate docker build command"}
        
        return {
            "success": True,
            "build_command": build_command.strip()
        }
        
    except Exception as e:
        return {"error": f"Failed to get docker build command: {str(e)}"}

def build_and_run_docker(repo_name: str, image_name: str = '', container_name: str = '') -> Dict[str, Any]:
    """Build and run Docker image with AI-powered configuration detection"""
    
    # Use AI to analyze project first
    db = RepoDatabase()
    agent = BedrockDockerAgent()
    print(f"Looking for repo: {repo_name}")
    
    # Debug: Show all available repos
    all_repos = db.get_all_repos()
    print(f"Available repos: {list(all_repos.keys())}")
    
    repo_data = db.get_repo_analysis(repo_name)
    if repo_data is None:
        return {"error": f"Repository '{repo_name}' not found in database. Available repos: {list(all_repos.keys())}"}
    
    analysis_repo = repo_data.get("ai_analysis",'')
    directory_path = os.path.abspath(repo_data.get("project_path",''))
    # now use Bedrock to analyse the analysis again    
    # Check Docker daemon
    daemon_check = check_docker_daemon()
    if not daemon_check.get("running"):
        start_result = start_docker_daemon()
        if "error" in start_result:
            return {
                "error": "Docker daemon not running",
                "suggestion": "Start Docker Desktop manually"
            }
# Create Dockerfile from prompt if provided
    create_dockerfile_result = create_dockerfile_from_prompt(str(analysis_repo))
    print("-------------------457664--------------------")
    print(create_dockerfile_result)
    cmd = create_dockerfile_result['run']['build_command'].split('\n')[1].split(' ')
    if not create_dockerfile_result.get("success"):
        return {"error": f"Failed to create Dockerfile from prompt: {create_dockerfile_result.get('error')}"}
    print("created Dockerfile!")
    # Set default names if not provided
    g_image_name = image_name or f"{repo_name}-image"
    g_container_name = container_name or f"{repo_name}-container"
    final_image_name = f"{g_image_name}{numpy.random.randint(500, 970)}"
    final_container_name = f"{g_container_name}{numpy.random.randint(100, 570)}"
    dockerfile_path = os.path.join(directory_path, "Dockerfile")
    dedicated_port = 3000
    # with open(directory_path, 'r+') as file:
    #     line = file.readline()
    #     if 'expose' in line.lower():  # Handle cases where the file has fewer lines than requested
    #         dedicated_port=(line.lstrip()).split()[-1]
    ai_config = analysis_repo

    # Generate Dockerfile if needed using AI
    dockerfile_path = os.path.join(directory_path, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        dockerfile_result, dedicated_port = agent.analyze_project_and_create_dockerfile(directory_path)
        if not dockerfile_result:
            return {"error": "Failed to generate Dockerfile, path is incorrect!"}
    print("lets validate")
    # Validate Dockerfile before building
    validation_result = validate_the_dockerfile()
    if not validation_result.get("success"):
        return {"error": f"Dockerfile validation failed: {validation_result.get('error')}"}
    cmd_oyt = docker_commands_from_prompt(f"""
                              providing you the path of the dockerfile{validation_result['content']}. validate the base images for any wrong or deprecated images chosen. Return only the Dockerfile content, do not include any line starting from special character and no comments.  
                                """)
    # print(cmd_oyt['build_command'])
    with open(dockerfile_path, 'w', encoding='utf-8') as f:
        f.write(cmd_oyt['build_command'])
    validation_result = validate_the_dockerfile()
    # Build Docker image
    build_result = build_docker_image(directory_path, final_image_name)
    if not build_result.get("success"):
        return build_result
    print("build sucessful!")
    print(f"Using port: {dedicated_port}")
    # Run Docker container
    run_result = run_docker_container(final_image_name, final_container_name, dedicated_port, cmd)
    if not run_result.get("success"):
        return run_result
    
    return {
        "success": True,
        "image_name": final_image_name,
        "container_name": final_container_name,
        "container_id": run_result.get("container_id"),
        "port": dedicated_port,
        "url": f"http://localhost:{dedicated_port}" if dedicated_port else None,
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