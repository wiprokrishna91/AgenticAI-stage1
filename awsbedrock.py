import boto3
import json
import os
import subprocess
from typing import Dict, Any
from s2i_builder import containerize_with_s2i, S2IBuilder
from s2i_setup import install_s2i, check_s2i_installation

class BedrockDockerAgent:
    def __init__(self, region_name: str = "ap-south-1"):
        """Initialize AWS Bedrock client"""
        self.bedrock = boto3.client(
            'bedrock-runtime', 
            region_name="us-east-1",
            aws_access_key_id="ASIAYSE4OFR63CSNP6JP",
            aws_secret_access_key="+WhdoEZn0aHjyXRAaF5KulIUD2B0AygAoT6xoRfx",
            aws_session_token="IQoJb3JpZ2luX2VjENn//////////wEaCmFwLXNvdXRoLTEiSDBGAiEAj7uLZKWf+kA8vJit6aLLwHQHyJwgFptd3W/mk+gMlwMCIQC+eFAF9oictZmlVmwMS5ZLvU2R0bs8ESQexmxyaj+IdiqIAwhCEAAaDDU4ODczODYwNDE1NyIMDrgGQdAwINWOMcZSKuUClmZndCjws5qQgaItYuBsIgbNRXlU4e4yGyWvDA99KFMTeXLBrlIq9xXw4YvBxug7kF2YwgGaiduYs3ZOOs9JOtPWrRn8ZZU2jR+JrLvc2AtXKMAs0IGI2A1r4Ob1MUri3A3NVhMscWPNSgrayDxPhgqEfS07BrGOhfO7QIs6/0H29YUB3czdLJOZE76eNIZ4HSsqkWFfLuFY3tdqRQg0ARgIUV2bfipnkvow6JdKUsdWqD+9b+Qq0jzLxTIW+VkWstbKsfxBDkx6rgQlA0MQcB9riQqIqtmBWV9T1+7g2hGxwPqZmeeAw67VCK2sLWwl44bTXbxzGG47wkq7IRrQCZ9DLSJt3wW1RooNSU0aSUql1uonBTBpdi8GSOmdV2aORjOQUr56y/n2kj26SRzQhDFdIAaJ8CiIQ7AK5jRvgQ6MR9n7A2sQsof0rOLPJjWcNEHGXbDwsJcZPfWojnVl2sHSKlfsMKOK4MUGOqUBToHi/f7AsdaLtqUJPOSAXrapGS1P4MlPut6m1uz9jUPaUiGEose34FbyBFpb1bRwNm6qValxeCHLan16s3bvuimexjXICUCHUau4m/xt/UVDRRyCTGuS5PKE52DqOekT2YB3BmwK07lHtYzrETiy9x8TU4ocnfKxzg7onnOfnkHTNeCVJrisyHFW8XuOtXUI/sF0gNrx5MGAusIhM2Uc+RFvbzLq"
        )
        self.model_id = "amazon.nova-lite-v1:0"
    
    def analyze_project_and_create_dockerfile(self, project_path: str) -> str:
        """Use Bedrock to analyze project and generate Dockerfile"""
        
        # Analyze project structure
        project_info = self._analyze_project_structure(project_path)
        
        # Create prompt for Bedrock
        prompt = f"""
        Analyze this project structure and create an optimized Dockerfile:
        
        Project Path: {project_path}
        Files and Structure: {project_info}
        
        Generate a production-ready Dockerfile that:
        1. Uses appropriate base image
        2. Installs dependencies
        3. Sets up the application
        4. Exposes necessary ports
        5. Includes security best practices
        
        Return only the Dockerfile content without explanations.
        """
        
        # Call Bedrock
        try:
            response = self._call_bedrock(prompt)
            dockerfile_content = response.strip()
            
            # Save Dockerfile to project directory
            dockerfile_path = os.path.join(project_path, "Dockerfile")
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
        except Exception as e:
            raise Exception(f"Failed to generate or save Dockerfile: {str(e)}")
        
        return dockerfile_path
    
    def _analyze_project_structure(self, project_path: str) -> str:
        """Analyze project structure and return summary"""
        structure = []
        
        for root, dirs, files in os.walk(project_path):
            # Skip hidden directories and common build directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            level = root.replace(project_path, '').count(os.sep)
            indent = ' ' * 2 * level
            structure.append(f"{indent}{os.path.basename(root)}/")
            
            subindent = ' ' * 2 * (level + 1)
            for file in files[:10]:  # Limit to first 10 files per directory
                structure.append(f"{subindent}{file}")
        
        return '\n'.join(structure[:50])  # Limit output
    
    def _call_bedrock(self, prompt: str) -> str:
        """Call AWS Bedrock with the given prompt"""
        try:
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": 2000
                }
            }
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['output']['message']['content'][0]['text']
        except Exception as e:
            raise Exception(f"Bedrock API call failed: {str(e)}")
    
    def test_prompt(self) -> Dict[str, Any]:
        """Test method that sends hello bedrock prompt and returns JSON response"""
        try:
            response_text = self._call_bedrock("hello bedrock")
            return {
                "success": True,
                "response": response_text,
                "model": self.model_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_and_containerize_with_s2i(self, project_path: str = "cloned_repos") -> Dict[str, Any]:
        """Use Bedrock AI to analyze project and generate S2I containerized image"""
        
        if not os.path.exists(project_path):
            return {"error": f"Directory '{project_path}' not found"}
        
        project_info = self._analyze_project_structure(project_path)
        
        prompt = f"""
        Analyze this project and recommend S2I configuration:
        
        Project: {project_path}
        Structure: {project_info}
        
        Return JSON with:
        {{
            "builder_image": "registry.redhat.io/ubi9/python-311",
            "output_image": "suggested_name",
            "environment_vars": {{}}
        }}
        """
        
        try:
            ai_response = self._call_bedrock(prompt)
            
            try:
                ai_config = json.loads(ai_response.strip())
            except:
                ai_config = {
                    "builder_image": "registry.redhat.io/ubi9/python-311",
                    "output_image": "ai-generated-app",
                    "environment_vars": {}
                }
            
            s2i_check = check_s2i_installation()
            if not s2i_check.get("installed"):
                return {
                    "error": "S2I not installed",
                    "ai_recommendation": ai_config
                }
            
            # Check Docker daemon before S2I build
            daemon_check = check_docker_daemon()
            if not daemon_check.get("running"):
                return {
                    "error": "Docker daemon not running",
                    "daemon_error": daemon_check.get("error"),
                    "suggestion": "Start Docker Desktop before containerizing",
                    "ai_recommendation": ai_config
                }
            
            s2i_result = containerize_with_s2i(
                project_path,
                ai_config["builder_image"],
                ai_config["output_image"]
            )
            
            return {
                "success": s2i_result.get("success", False),
                "ai_recommendation": ai_config,
                "s2i_result": s2i_result
            }
            
        except Exception as e:
            return {"error": f"Bedrock S2I analysis failed: {str(e)}"}
    
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

def build_and_run_docker(directory_path: str, image_name: str = None, container_name: str = None) -> Dict[str, Any]:
    """Build and run Docker image with daemon check"""
    # Check Docker daemon first
    daemon_check = check_docker_daemon()
    if not daemon_check.get("running"):
        # Try to start daemon
        start_result = start_docker_daemon()
        if "error" in start_result:
            return {
                "error": "Docker daemon not running",
                "daemon_error": daemon_check.get("error"),
                "start_attempt": start_result,
                "suggestion": "Start Docker Desktop manually"
            }
    
    try:
        # Validate directory and Dockerfile
        if not os.path.exists(directory_path):
            return {"error": f"Directory '{directory_path}' not found"}
        
        dockerfile_path = os.path.join(directory_path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            return {"error": f"Dockerfile not found in '{directory_path}'"}
        
        # Generate names if not provided
        if not image_name:
            image_name = f"app-{os.path.basename(directory_path)}".lower()
        if not container_name:
            container_name = f"container-{os.path.basename(directory_path)}".lower()
        
        # Build Docker image
        build_cmd = ["docker", "build", "-t", image_name, directory_path]
        build_result = subprocess.run(build_cmd, capture_output=True, text=True)
        
        if build_result.returncode != 0:
            return {
                "error": f"Docker build failed: {build_result.stderr}",
                "build_output": build_result.stdout
            }
        
        # Run Docker container
        run_cmd = ["docker", "run", "-d", "--name", container_name, "-p", "8080:8080", image_name]
        run_result = subprocess.run(run_cmd, capture_output=True, text=True)
        
        if run_result.returncode != 0:
            return {
                "error": f"Docker run failed: {run_result.stderr}",
                "run_output": run_result.stdout
            }
        
        return {
            "success": True,
            "image_name": image_name,
            "container_name": container_name,
            "container_id": run_result.stdout.strip(),
            "build_output": build_result.stdout
        }
        
    except Exception as e:
        return {"error": f"Failed to build/run Docker: {str(e)}"}

def build_and_run_existing_dockerfile(directory_path: str, image_name: str = None, container_name: str = None) -> Dict[str, Any]:
    """Build and run Docker image from existing Dockerfile in directory"""
    agent = BedrockDockerAgent()
    return agent.build_and_run_docker(directory_path, image_name, container_name)

def create_docker_image_for_project(cloned_repos_dir: str = "cloned_repos") -> Dict[str, Any]:
    """Main function to create Docker image for a project using Bedrock"""
    
    # Sanitize input to prevent path traversal
    safe_dir = os.path.basename(os.path.normpath(cloned_repos_dir))
    project_path = os.path.abspath(safe_dir)
    
    if not os.path.exists(project_path):
        return {"error": f"Project '{safe_dir}' not found"}
    
    try:
        # Initialize Bedrock agent
        agent = BedrockDockerAgent()
        
        # Generate Dockerfile using Bedrock
        dockerfile_path = agent.analyze_project_and_create_dockerfile(project_path)
        
        return {
            "success": True,
            "message": f"Dockerfile created successfully for {cloned_repos_dir}",
            "dockerfile_path": dockerfile_path,
            "project_path": project_path
        }
        #https://github.com/mmumshad/simple-webapp-flask.git
    except Exception as e:
        return {"error": f"Failed to create Dockerfile: {str(e)}"}

def containerize_project_with_s2i(source_path: str = "cloned_repos", builder_image: str = None, output_image: str = "my-flask-app") -> Dict[str, Any]:
    """Containerize project using S2I instead of Dockerfile"""
    
    # Check S2I installation
    s2i_check = check_s2i_installation()
    if not s2i_check.get("installed"):
        return {
            "error": "S2I not installed",
            "install_info": s2i_check,
            "suggestion": "Run install_s2i() to install S2I"
        }
    
    # Use S2I to containerize
    return containerize_with_s2i(source_path, builder_image, output_image)

def setup_s2i_environment() -> Dict[str, Any]:
    """Setup S2I environment and check prerequisites"""
    
    # Check current installation
    s2i_status = check_s2i_installation()
    
    if s2i_status.get("installed"):
        return {
            "status": "ready",
            "message": "S2I is already installed and ready to use",
            "version": s2i_status.get("version")
        }
    else:
        # Attempt installation
        install_result = install_s2i()
        return {
            "status": "setup_required",
            "install_result": install_result
        }

def bedrock_s2i_containerize(project_path: str = "cloned_repos") -> Dict[str, Any]:
    """Use Bedrock AI to analyze directory and generate S2I containerized image"""
    agent = BedrockDockerAgent()
    return agent.analyze_and_containerize_with_s2i(project_path)

