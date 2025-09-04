import subprocess
from typing import List, Dict, Any

def run_command(command_list: List[str]) -> Dict[str, Any]:
    """Run subprocess command from list"""
    try:
        result = subprocess.run(command_list, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }