from awsdocker import build_and_run_docker
import os

def test_containerization():
    """Test containerization with Docker"""
    
    # Create a simple test project
    test_dir = "test_project"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create requirements.txt
    with open(os.path.join(test_dir, "requirements.txt"), "w") as f:
        f.write("flask==2.3.3\n")
    
    # Create simple app.py
    with open(os.path.join(test_dir, "app.py"), "w") as f:
        f.write("""from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from containerized app!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
""")
    
    print("=== Testing Docker Containerization ===")
    result = build_and_run_docker(
        directory_path=test_dir,
        image_name="test-app"
    )
    
    if result.get("success"):
        print("✅ Containerization successful!")
        print(f"Image: {result.get('image_name')}")
        print(f"Container: {result.get('container_name')}")
        if result.get("container_id"):
            print(f"Container ID: {result.get('container_id')}")
            print(f"App running at: {result.get('url')}")
    else:
        print("❌ Containerization failed:")
        print(f"Error: {result.get('error')}")
    
    return result

if __name__ == "__main__":
    test_containerization()