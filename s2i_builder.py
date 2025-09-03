import os
import subprocess
import json
from typing import Dict, Any

class S2IBuilder:
    def __init__(self):
        """Initialize S2I Builder"""
        self.s2i_available = self._check_s2i_availability()
    
    def _check_s2i_availability(self) -> bool:
        """Check if S2I is installed with enhanced detection"""
        from s2i_setup import check_s2i_installation
        result = check_s2i_installation()
        if result.get("installed"):
            self.s2i_command = result.get("path", "s2i")
            return True
        return False
    
    def build_with_s2i(self, source_dir: str, builder_image: str, output_image: str) -> Dict[str, Any]:
        """Build container image using S2I"""
        if not self.s2i_available:
            return {"error": "S2I is not installed. Install from: https://github.com/openshift/source-to-image"}
        
        try:
            # Use the detected S2I command path
            cmd = [getattr(self, 's2i_command', 's2i'), 'build', source_dir, builder_image, output_image]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "image": output_image,
                    "output": result.stdout
                }
            else:
                return {
                    "error": f"S2I build failed: {result.stderr}",
                    "output": result.stdout
                }
        except Exception as e:
            return {"error": f"S2I build error: {str(e)}"}
    
    def get_recommended_builder_images(self, project_type: str) -> Dict[str, str]:
        """Get recommended S2I builder images for different project types"""
        builders = {
            "python": {
                "python-39": "registry.redhat.io/ubi8/python-39",
                "python-311": "registry.redhat.io/ubi9/python-311",
                "centos-python": "centos/python-38-centos7"
            },
            "nodejs": {
                "nodejs-16": "registry.redhat.io/ubi8/nodejs-16",
                "nodejs-18": "registry.redhat.io/ubi9/nodejs-18"
            },
            "java": {
                "openjdk-11": "registry.redhat.io/ubi8/openjdk-11",
                "openjdk-17": "registry.redhat.io/ubi9/openjdk-17"
            }
        }
        return builders.get(project_type, {})

def containerize_with_s2i(source_path: str = "cloned_repos", builder_image: str = None, output_image: str = "my-app") -> Dict[str, Any]:
    """Containerize repository using S2I with enhanced detection"""
    from s2i_setup import check_s2i_installation
    
    # Check Docker daemon first
    try:
        docker_check = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
        if docker_check.returncode != 0:
            return {
                "error": "Docker daemon not running",
                "suggestion": "Start Docker Desktop before using S2I"
            }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {
            "error": "Docker not available",
            "suggestion": "Install and start Docker Desktop"
        }
    
    # Check S2I availability
    s2i_check = check_s2i_installation()
    if not s2i_check.get("installed"):
        return {
            "error": "S2I not found",
            "details": s2i_check.get("error", "Unknown error"),
            "suggestion": "Install S2I from https://github.com/openshift/source-to-image/releases"
        }
    
    # Use absolute path
    abs_source_path = os.path.abspath(source_path)
    
    if not os.path.exists(abs_source_path):
        return {"error": f"Source directory '{source_path}' not found"}
    
    # Initialize S2I builder
    s2i = S2IBuilder()
    
    # Auto-detect project type and suggest builder
    if not builder_image:
        if os.path.exists(os.path.join(abs_source_path, "requirements.txt")):
            builder_image = "registry.redhat.io/ubi9/python-311"
        elif os.path.exists(os.path.join(abs_source_path, "package.json")):
            builder_image = "registry.redhat.io/ubi9/nodejs-18"
        else:
            return {"error": "Could not auto-detect project type. Please specify builder_image"}
    
    # Build with S2I
    result = s2i.build_with_s2i(abs_source_path, builder_image, output_image)
    
    if result.get("success"):
        # Run the container
        try:
            run_cmd = ["docker", "run", "-d", "-p", "8080:8080", output_image]
            run_result = subprocess.run(run_cmd, capture_output=True, text=True)
            
            if run_result.returncode == 0:
                result["container_id"] = run_result.stdout.strip()
                result["message"] = f"S2I build successful. Container running on port 8080"
            else:
                result["run_error"] = run_result.stderr
        except Exception as e:
            result["run_error"] = str(e)
    
    return result