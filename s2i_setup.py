import os
import subprocess
import platform
import shutil
from typing import Dict, Any

def install_s2i() -> Dict[str, Any]:
    """Install S2I based on the operating system"""
    system = platform.system().lower()
    
    try:
        if system == "windows":
            return install_s2i_windows()
        elif system == "linux":
            return install_s2i_linux()
        elif system == "darwin":  # macOS
            return install_s2i_macos()
        else:
            return {"error": f"Unsupported operating system: {system}"}
    except Exception as e:
        return {"error": f"Installation failed: {str(e)}"}

def install_s2i_windows() -> Dict[str, Any]:
    """Install S2I on Windows"""
    # Check if chocolatey is available
    try:
        subprocess.run(['choco', '--version'], capture_output=True, check=True)
        
        # Install using chocolatey
        result = subprocess.run(['choco', 'install', 'source-to-image', '-y'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return {"success": True, "method": "chocolatey", "output": result.stdout}
        else:
            return manual_install_windows()
    except:
        return manual_install_windows()

def manual_install_windows() -> Dict[str, Any]:
    """Manual installation instructions for Windows"""
    instructions = """
    Manual S2I Installation for Windows:
    
    1. Download S2I from: https://github.com/openshift/source-to-image/releases
    2. Extract the binary to a directory (e.g., C:\\s2i)
    3. Add the directory to your PATH environment variable
    4. Restart your terminal/IDE
    5. Verify installation: s2i version
    
    Alternative: Use WSL2 with Linux installation
    """
    return {"manual_install": True, "instructions": instructions}

def install_s2i_linux() -> Dict[str, Any]:
    """Install S2I on Linux"""
    try:
        # Try using package manager first
        distro_commands = [
            ['sudo', 'dnf', 'install', 'source-to-image', '-y'],  # Fedora/RHEL
            ['sudo', 'apt-get', 'install', 'source-to-image', '-y'],  # Ubuntu/Debian
        ]
        
        for cmd in distro_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    return {"success": True, "method": "package_manager", "output": result.stdout}
            except:
                continue
        
        # Manual installation
        return manual_install_linux()
    except Exception as e:
        return {"error": str(e)}

def manual_install_linux() -> Dict[str, Any]:
    """Manual installation for Linux"""
    instructions = """
    Manual S2I Installation for Linux:
    
    1. Download latest release:
       wget https://github.com/openshift/source-to-image/releases/download/v1.3.1/source-to-image-v1.3.1-a5a77147-linux-amd64.tar.gz
    
    2. Extract and install:
       tar -xzf source-to-image-v1.3.1-a5a77147-linux-amd64.tar.gz
       sudo mv s2i /usr/local/bin/
    
    3. Verify: s2i version
    """
    return {"manual_install": True, "instructions": instructions}

def install_s2i_macos() -> Dict[str, Any]:
    """Install S2I on macOS"""
    try:
        # Try homebrew first
        result = subprocess.run(['brew', 'install', 'source-to-image'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return {"success": True, "method": "homebrew", "output": result.stdout}
        else:
            return manual_install_macos()
    except:
        return manual_install_macos()

def manual_install_macos() -> Dict[str, Any]:
    """Manual installation for macOS"""
    instructions = """
    Manual S2I Installation for macOS:
    
    1. Install Homebrew if not available:
       /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    2. Install S2I:
       brew install source-to-image
    
    3. Verify: s2i version
    """
    return {"manual_install": True, "instructions": instructions}

def check_s2i_installation() -> Dict[str, Any]:
    """Check if S2I is properly installed with enhanced Windows detection"""
    import shutil
    
    # Try standard PATH lookup first
    s2i_path = shutil.which('s2i')
    if s2i_path:
        try:
            result = subprocess.run([s2i_path, 'version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {"installed": True, "version": result.stdout.strip(), "path": s2i_path}
        except subprocess.TimeoutExpired:
            pass
    
    # Windows-specific paths to check
    if platform.system().lower() == "windows":
        windows_paths = [
            r'C:\s2i\s2i.exe',
            r'C:\Program Files\s2i\s2i.exe', 
            r'C:\tools\s2i\s2i.exe',
            os.path.expanduser(r'~\s2i\s2i.exe'),
            os.path.expanduser(r'~\AppData\Local\s2i\s2i.exe'),
            r'C:\ProgramData\chocolatey\bin\s2i.exe'
        ]
        
        for path in windows_paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run([path, 'version'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        return {
                            "installed": True, 
                            "version": result.stdout.strip(),
                            "path": path,
                            "note": "Found S2I but not in PATH. Consider adding to PATH."
                        }
                except subprocess.TimeoutExpired:
                    continue
    
    return {"installed": False, "error": "S2I not found in PATH or common locations"}

def get_s2i_command() -> str:
    """Get S2I command path"""
    check_result = check_s2i_installation()
    if check_result.get("installed"):
        return check_result.get("path", "s2i")
    return None