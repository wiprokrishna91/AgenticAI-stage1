#!/usr/bin/env python3
"""
S2I Demo Script - Containerize your repository using Source-to-Image
"""

from awsbedrock import setup_s2i_environment, containerize_project_with_s2i
from s2i_builder import S2IBuilder

def main():
    print("🚀 S2I Containerization Demo")
    print("=" * 40)
    
    # Step 1: Setup S2I environment
    print("\n1. Checking S2I environment...")
    setup_result = setup_s2i_environment()
    
    if setup_result["status"] == "ready":
        print(f"✅ S2I is ready: {setup_result['version']}")
    else:
        print("⚠️  S2I setup required:")
        print(setup_result["install_result"])
        return
    
    # Step 2: Show available builder images
    print("\n2. Available S2I Builder Images:")
    s2i = S2IBuilder()
    
    python_builders = s2i.get_recommended_builder_images("python")
    print("Python builders:")
    for name, image in python_builders.items():
        print(f"  - {name}: {image}")
    
    # Step 3: Containerize the Flask app
    print("\n3. Containerizing Flask application...")
    
    # Use Python 3.11 builder for the Flask app
    result = containerize_project_with_s2i(
        source_path="cloned_repos",
        builder_image="registry.redhat.io/ubi9/python-311",
        output_image="flask-app-s2i"
    )
    
    if result.get("success"):
        print("✅ S2I build successful!")
        print(f"Image: {result['image']}")
        if result.get("container_id"):
            print(f"Container ID: {result['container_id']}")
            print("🌐 Application running on http://localhost:8080")
    else:
        print("❌ S2I build failed:")
        print(result.get("error", "Unknown error"))
    
    # Step 4: Show comparison with traditional Docker
    print("\n4. S2I vs Traditional Docker:")
    print("S2I Benefits:")
    print("  ✅ No Dockerfile needed")
    print("  ✅ Standardized build process")
    print("  ✅ Security best practices built-in")
    print("  ✅ Reproducible builds")
    print("  ✅ Language-specific optimizations")

if __name__ == "__main__":
    main()