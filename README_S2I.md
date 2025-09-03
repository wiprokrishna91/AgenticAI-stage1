set_aws_env.bat
python main.py

# S2I Containerization Guide

## What is S2I?

Source-to-Image (S2I) is a toolkit for building reproducible container images from source code without requiring a Dockerfile. It uses builder images that contain the runtime environment and build tools.

## Benefits over Traditional Docker

- **No Dockerfile needed** - S2I handles the containerization process
- **Standardized builds** - Consistent build process across projects
- **Security** - Builder images follow security best practices
- **Language optimization** - Optimized for specific languages/frameworks

## Quick Start

1. **Install S2I**:
   ```python
   from awsbedrock import setup_s2i_environment
   setup_s2i_environment()
   ```

2. **Containerize your project**:
   ```python
   from awsbedrock import containerize_project_with_s2i
   
   result = containerize_project_with_s2i(
       source_path="cloned_repos",
       builder_image="registry.redhat.io/ubi9/python-311",
       output_image="my-flask-app"
   )
   ```

3. **Run the demo**:
   ```bash
   python s2i_demo.py
   ```

## Builder Images

### Python
- `registry.redhat.io/ubi9/python-311` - Python 3.11 on UBI 9
- `registry.redhat.io/ubi8/python-39` - Python 3.9 on UBI 8

### Node.js
- `registry.redhat.io/ubi9/nodejs-18` - Node.js 18 on UBI 9
- `registry.redhat.io/ubi8/nodejs-16` - Node.js 16 on UBI 8

## S2I Configuration

The `.s2i/environment` file contains:
```
APP_MODULE=microblog:app
APP_CONFIG=config.py
```

## Manual S2I Commands

```bash
# Build image
s2i build cloned_repos registry.redhat.io/ubi9/python-311 flask-app-s2i

# Run container
docker run -p 8080:8080 flask-app-s2i
```

## Comparison: S2I vs Dockerfile

| Feature | S2I | Dockerfile |
|---------|-----|------------|
| Setup | No Dockerfile needed | Requires Dockerfile |
| Security | Built-in best practices | Manual configuration |
| Consistency | Standardized process | Varies by developer |
| Maintenance | Builder image updates | Manual updates |
| Learning curve | Minimal | Requires Docker knowledge |