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
from takeprompt import BedrockAgent
from awsdocker import build_and_run_docker, build_compose
from tindatabase import RepoDatabase
from awsbedrock import _analyze_project_structure

app = FastAPI(title="Git Repo Analyzer & Containerizer", version="1.0.0")

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

@app.post("/clone-repo")
async def clone_repository(repo_request: RepoRequest) -> Dict[str, Any]:
    """Clone git repository from URL to local cloned_repos directory"""
    try:
        repo_url = str(repo_request.repo_url)
        
        # Extract repo name from URL
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        clone_path = os.path.join(CLONED_REPOS_DIR, repo_name)
        
        # Remove existing directory if it exists
        if os.path.exists(clone_path):
            shutil.rmtree(clone_path)
        
        # Clone repository
        result = subprocess.run(
            ["git", "clone", repo_url, clone_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=400,
                detail=f"Git clone failed: {result.stderr}"
            )
        
        return {
            "success": True,
            "message": f"Repository cloned successfully to {clone_path}",
            "repo_name": repo_name,
            "clone_path": clone_path
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Clone operation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clone failed: {str(e)}")

@app.post("/analyze-repo")
async def analyze_repository(repo_request: RepoRequest) -> Dict[str, Any]:
    """Analyze repository using AWS Bedrock and return details"""
    try:
        repo_url = str(repo_request.repo_url)
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        print(repo_name)
        project_path = os.path.abspath(os.path.join(os.getcwd(),CLONED_REPOS_DIR, repo_name))
        print(project_path)
        if not os.path.exists(project_path):
            raise HTTPException(
                status_code=404,
                detail=f"Repository not found. Please clone it first."
            )
        # Initialize Bedrock agent
        agent = BedrockAgent()
        
        # Analyze project structure
        project_info = _analyze_project_structure(project_path)
        
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
            "multistaged": "is it a multi-staged application? just reply True or false
        }}
        """
    
        ai_response = agent._call_bedrock(prompt)
        restructured_response = agent._call_bedrock(f"Given this text, restructure it into a valid JSON object: {ai_response}. need spefic details with no additional texts")
    
        # Store analysis data in database
        db = RepoDatabase()
        analysis_data = {
            "success": True,
            "repo_name": repo_name,
            "project_path": project_path,
            "structure": project_info,
            "ai_analysis": restructured_response[7:-5],
            "bedrock_model": agent.model_id,
            "error_in":"",
            "errormsg":"",
            "imagename": ""
        }
        
        db.store_repo_analysis(repo_name, analysis_data)
        db.close()
        
        return analysis_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
@app.post("/containerize")
async def containerize_project(container_request: ContainerizeRequest) -> Dict[str, Any]:
    """Create containerized image using Docker"""
    try:
        project_name = container_request.project_name
        project_path = os.path.join(CLONED_REPOS_DIR, project_name)     
        if not os.path.exists(project_path) or len(os.listdir(project_path)) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Project '{project_path}' is either not found or empty. please check if the repo is cloned"
            )
        
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