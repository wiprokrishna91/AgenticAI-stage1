from awsbedrock import BedrockDockerAgent
from awsdocker import build_and_run_docker
import os

def test_ai_docker_analysis():
    """Test AI-powered Docker configuration and containerization"""
    
    # Test with cloned_repos if it exists
    test_dirs = ["cloned_repos", "test_project"]
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            print(f"\n=== Analyzing {test_dir} with AI ===")
            
            agent = BedrockDockerAgent()
            analysis = agent.analyze_project_for_docker(test_dir)
            
            if analysis.get("success"):
                ai_config = analysis.get("ai_analysis", {})
                print("✅ AI Analysis successful!")
                print(f"Project Type: {ai_config.get('project_type')}")
                print(f"Detected Port: {ai_config.get('port')}")
                print(f"Image Name: {ai_config.get('image_name')}")
                print(f"Container Name: {ai_config.get('container_name')}")
                print(f"Main File: {ai_config.get('main_file')}")
                print(f"Dockerfile Needed: {ai_config.get('dockerfile_needed')}")
                
                # Test Docker containerization
                print(f"\n=== Docker Containerization of {test_dir} ===")
                result = build_and_run_docker(
                    directory_path=test_dir,
                    image_name=ai_config.get('image_name'),
                    container_name=ai_config.get('container_name')
                )
                
                if result.get("success"):
                    print("✅ Containerization successful!")
                    print(f"Image: {result.get('image_name')}")
                    print(f"Container: {result.get('container_name')}")
                    print(f"Port: {result.get('port')}")
                    print(f"URL: {result.get('url')}")
                else:
                    print("❌ Containerization failed:")
                    print(f"Error: {result.get('error')}")
            else:
                print("❌ AI Analysis failed:")
                print(f"Error: {analysis.get('error')}")
        else:
            print(f"Directory {test_dir} not found, skipping...")

if __name__ == "__main__":
    test_ai_docker_analysis()