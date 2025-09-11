import json
import os
from typing import Dict, Any, List


def analyse_repo_completely(folder_path: str, unique_id: str) -> Dict[str, Any]:
    """Analyze repository folder and create JSON file with analysis"""
    try:
        analysis_data = {
            "unique_id": unique_id,
            "folder_path": folder_path,
            "files": [],
            "subfolders": [],
            "file_types": {},
            "total_files": 0,
            "total_folders": 0
        }
        
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git', 'library','modules', 'packages','static','images']]
            
            rel_path = os.path.relpath(root, folder_path)
            if rel_path != '.':
                analysis_data["subfolders"].append(rel_path)
                analysis_data["total_folders"] += 1
            
            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.join(rel_path, file) if rel_path != '.' else file
                    analysis_data["files"].append(file_path)
                    analysis_data["total_files"] += 1
                    
                    ext = os.path.splitext(file)[1].lower()
                    if ext:
                        analysis_data["file_types"][ext] = analysis_data["file_types"].get(ext, 0) + 1
        
        json_file_path = os.path.join(folder_path, f"{unique_id}.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2)
        
        return {
            "success": True,
            "json_file": json_file_path,
            "analysis": analysis_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def list_packages(folder_path: str) -> Dict[str, List[str]]:
    """Extract packages from requirements.txt, package.json, and Pipfile"""
    packages = {
        "requirements.txt": [],
        "package.json": [],
        "Pipfile": []
    }
    
    # Check requirements.txt
    req_file = os.path.join(folder_path, "requirements.txt")
    if os.path.exists(req_file):
        with open(req_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    packages["requirements.txt"].append(line.split('==')[0].split('>=')[0].split('<=')[0])
    
    # Check package.json
    pkg_file = os.path.join(folder_path, "package.json")
    if os.path.exists(pkg_file):
        try:
            with open(pkg_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                packages["package.json"] = list(deps.keys()) + list(dev_deps.keys())
        except json.JSONDecodeError:
            pass
    
    # Check Pipfile
    pip_file = os.path.join(folder_path, "Pipfile")
    if os.path.exists(pip_file):
        with open(pip_file, 'r', encoding='utf-8') as f:
            in_packages = False
            for line in f:
                line = line.strip()
                if line == "[packages]" or line == "[dev-packages]":
                    in_packages = True
                elif line.startswith('[') and line.endswith(']'):
                    in_packages = False
                elif in_packages and '=' in line:
                    pkg_name = line.split('=')[0].strip().strip('"')
                    if pkg_name:
                        packages["Pipfile"].append(pkg_name)
    
    return packages


def find_config_files(folder_path: str) -> List[str]:
    """Find settings, config, and .env files in the project"""
    config_files = []
    config_patterns = [
        '.env', '.env.local', '.env.production', '.env.development',
        'config.yml', 'config.yaml', 'application.properties', 'application.yml',
        'settings.py', 'appsettings.json', 'config.json', 'database.yml',
        'web.config', 'nginx.conf', 'httpd.conf', 'database.json',
        'knexfile.js', 'sequelize.config.js', 'hibernate.cfg.xml'
    ]
    
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]
        
        for file in files:
            if file in config_patterns or file.startswith('config') or file.startswith('settings'):
                config_files.append(os.path.join(root, file))
    
    return config_files