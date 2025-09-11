import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
import uvicorn
import json
from takeprompt import BedrockAgent
from awsdocker import build_and_run_docker, build_compose
from tindatabase import RepoDatabase
from clone_database import CloneDatabase
from awsbedrock import _analyze_project_structure, analyze_repo_details
from dockerbuild import docker_build
from utils import format_dict_string

app = FastAPI(title="Containerizer", version="1.0.0")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Ensure cloned_repos directory exists
CLONED_REPOS_DIR = "cloned_repos"
Path(CLONED_REPOS_DIR).mkdir(exist_ok=True)

class RepoRequest(BaseModel):
    repo_url: HttpUrl

class ContainerizeRequest(BaseModel):
    project_name: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/list-repos")
async def list_repositories() -> Dict[str, Any]:
    """Get list of all cloned repositories"""
    try:
        clone_db = CloneDatabase()
        repos = clone_db.get_all_cloned_repos()
        clone_db.close()
        return {"success": True, "repos": repos}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/repo/{repo_id}")
async def get_repository_details(repo_id: str) -> Dict[str, Any]:
    """Get repository details by repoID"""
    try:
        clone_db = CloneDatabase()
        repo = clone_db.get_cloned_repo(repo_id)
        clone_db.close()
        if repo:
            return {"success": True, "repo": repo}
        else:
            return {"success": False, "error": "Repository not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/clone-repo")
async def clone_repository(repo_request: RepoRequest) -> Dict[str, Any]:
    """Clone git repository from URL to local cloned_repos directory"""
    try:
        repo_url = str(repo_request.repo_url)
        
        # Extract repo name from URL
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        clone_path = os.path.join(CLONED_REPOS_DIR, repo_name)
        
        # Always remove existing directory if it exists
        if os.path.exists(clone_path):
            try:
                shutil.rmtree(clone_path)
            except Exception as e:
                print(f"Warning: Could not remove existing directory: {e}")
        
        # Clone repository with authentication handling
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, clone_path],
            capture_output=True,
            text=True,
            timeout=300,
            env=dict(os.environ, GIT_TERMINAL_PROMPT="0")
        )
        
        # Store clone result in database (update if exists, create if new)
        clone_db = CloneDatabase()
        
        if result.returncode != 0:
            repo_id = clone_db.store_cloned_repo(repo_name, repo_url, clone_path, "failed")
            clone_db.close()
            raise HTTPException(
                status_code=400,
                detail=f"Git clone failed: {result.stderr}"
            )
        
        repo_id = clone_db.store_cloned_repo(repo_name, repo_url, clone_path, "success")
        clone_db.close()
        
        return {
            "success": True,
            "message": f"Repository cloned successfully to {clone_path}",
            "repo_name": repo_name,
            "clone_path": clone_path,
            "repoID": repo_id
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Clone operation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clone failed: {str(e)}")

@app.post("/analyze-repo-complete")
async def analyze_repository_complete(repo_request: RepoRequest) -> Dict[str, Any]:
    """Analyze repository completely using analyse_repo_completely function"""
    try:
        repo_url = str(repo_request.repo_url)
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        project_path = os.path.abspath(os.path.join(os.getcwd(), CLONED_REPOS_DIR, repo_name))
        
        if not os.path.exists(project_path):
            raise Exception(f"Repository not found. Please clone it first.")
        
        # Get repo ID from database
        clone_db = CloneDatabase()
        repos = clone_db.get_all_cloned_repos()
        repo_id = None
        for repo in repos:
            if repo['repo_name'] == repo_name:
                repo_id = repo['repoID']
                break
        clone_db.close()
        
        if not repo_id:
            raise Exception(f"Repository ID not found for {repo_name}")
        
        # Import and use the analyse_repo_completely function
        from fileanalysis import analyse_repo_completely
        result = analyse_repo_completely(project_path, repo_id)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Complete analysis failed: {str(e)}")

@app.post("/analyze-repo")
async def analyze_repository(repo_request: RepoRequest) -> Dict[str, Any]:
    """Analyze repository using AWS Bedrock and return details"""
    try:
        repo_url = str(repo_request.repo_url)
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        project_path = os.path.abspath(os.path.join(os.getcwd(),CLONED_REPOS_DIR, repo_name))
        if not os.path.exists(project_path):
            raise Exception(f"Repository not found. Please clone it first.")
        # Initialize Bedrock agent
        agent = BedrockAgent()
        
        # Analyze project structure
        project_info = _analyze_project_structure(project_path)
        print("analyzed structure")
        # Get AI analysis
        prompt = f"""
        Go through each directory not more than 3 deapths and except for modules/library directories. scan each line to check which all languages are used and frontend and backend applications are used.
        provided below is the repository name and details. go through each settings,configuration and yaml files to get maximum details from each. need specific ports used by frontend and backend and databse applications.
        Repository: {repo_name}
        Project Structure:
        {project_info}
        
        Please provide analysis in JSON format with:
        {{
            "project_type": "detected framework/language",
            "madules": ["major modules"]
            "ports": ["list of all ports used] 
            "database": ["databse used"]
            "build_instructions": "how to build this project",
            "multistaged": "is it a multi-staged application to build the doker files? if database is used then multistaged should be true. analyze the project info and decide is it multistaged. just reply True or false
        }}
        """
    
        ai_response = agent._call_bedrock(prompt)
        restructured_response = agent._call_bedrock(f"Given this text, restructure it into a valid JSON object: {ai_response}. need spefic details with no additional texts")
        formated_Well = format_dict_string(restructured_response)
        # Store analysis data in database
        db = RepoDatabase()
        analysis_data = {
            "status": "success",
            "repo_name": repo_name,
            "project_path": project_path,
            "structure": f"{project_info}",
            "ai_analysis": f"{json.loads(formated_Well)}",
            "bedrock_model": agent.model_id,
            "errormsg": 'NA',
            "imageID": 'NA'
        }
        
        db.store_repo_analysis(repo_name, analysis_data)
        db.close()
        
        return analysis_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
@app.post("/analyze-repo-details")
async def analyze_repository_details(container_request: ContainerizeRequest) -> Dict[str, Any]:
    """Analyze repository details including packages and config files"""
    try:
        project_name = container_request.project_name
        
        # Call analyze_repo_details function
        result = analyze_repo_details(project_name)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))
        
        return {
            "success": True,
            "message": f"Repository details analyzed for {project_name}",
            "analysis": result["analysis"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repository details analysis failed: {str(e)}")

@app.post("/build-docker")
async def build_docker_image(container_request: ContainerizeRequest) -> Dict[str, Any]:
    """Build Docker image for the project"""
    try:
        project_name = container_request.project_name
        
        # Get repo_id from database
        clone_db = CloneDatabase()
        repos = clone_db.get_all_cloned_repos()
        repo_id = None
        for repo in repos:
            if repo['repo_name'] == project_name:
                repo_id = repo['repoID']
                break
        clone_db.close()
        
        if not repo_id:
            raise HTTPException(status_code=404, detail=f"Repository ID not found for {project_name}")
        
        # Call docker_build function
        result = docker_build(project_name, f"{project_name}-image", repo_id)
        
        if result.get("success"):
            return {
                "success": True,
                "message": f"Docker image built successfully for {project_name}",
                "result": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Docker build failed"))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Docker build failed: {str(e)}")

@app.post("/containerize")
async def containerize_project(container_request: ContainerizeRequest) -> Dict[str, Any]:
    """Create containerized image using Docker"""
    try:
        project_name = container_request.project_name
        project_path = os.path.abspath(os.path.join(os.getcwd(),CLONED_REPOS_DIR, project_name))
        if not os.path.exists(project_path) or len(os.listdir(project_path)) == 0:
            raise Exception(f"Repository not found. Please clone it first.")
        
        if not project_path or not os.path.exists(project_path):
            raise HTTPException(
                status_code=404,
                detail=f"Project path not found or invalid for '{project_name}'"
            )
        
        # Use Docker containerization
        result = build_and_run_docker(project_name, image_name='tesmyapp:latest', container_name='tesmyapp')
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "message": f"Containerization completed for {project_name}",
            "repo_name": project_name,
            "containerization_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Containerization failed: {str(e)}")

@app.post("/rebuild-compose")
async def rebuild_compose(container_request: ContainerizeRequest) -> Dict[str, Any]:
    """Rebuild docker-compose.yml file"""
    try:
        project_name = container_request.project_name
        project_path = os.path.join(CLONED_REPOS_DIR, project_name)
        
        if not os.path.exists(project_path):
            raise HTTPException(status_code=404, detail=f"Project path not found: {project_path}")
        
        result = build_compose(project_name, project_path)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "message": f"Compose rebuilt for {project_name}",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebuild compose failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Git Repo Analyzer & Containerizer"}

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "detail": str(exc.detail)}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc.detail)}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1
    )