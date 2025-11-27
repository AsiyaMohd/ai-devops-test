# import os
# import docker
# import textwrap # Added to fix indentation issues automatically

# # Initialize Docker Client
# try:
#     client = docker.from_env()
# except Exception:
#     print("❌ Error: Docker is not running. Please open Docker Desktop first.")
#     exit()


# def ask_ai_for_config(file_list):
#     print(f"🤖 AI is analyzing your files: {file_list}...")
    
#     if "app.py" in file_list or "requirements.txt" in file_list:
#         print("💡 AI detected: Python Flask Application")
#         # textwrap.dedent removes the common leading whitespace
#         return textwrap.dedent("""\
#             FROM python:3.9-slim
#             WORKDIR /app
#             COPY . .
#             RUN pip install -r requirements.txt
#             CMD ["python", "app.py"]
#         """)
#     elif "package.json" in file_list:
#         print("💡 AI detected: Node.js Application")
#         return textwrap.dedent("""\
#             FROM node:14
#             WORKDIR /app
#             COPY . .
#             RUN npm install
#             CMD ["npm", "start"]
#         """)
#     else:
#         return "ERROR"

# def run_devops_pipeline():
#     # Step 1: Analyze Code
#     files = [f for f in os.listdir('.') if os.path.isfile(f)]
    
#     # Step 2: Generate Dockerfile
#     dockerfile_content = ask_ai_for_config(files)
    
#     if "ERROR" == dockerfile_content:
#         print("❌ AI couldn't figure out your project type.")
#         return

#     with open("Dockerfile", "w") as f:
#         f.write(dockerfile_content)
#     print("✅ Created Dockerfile successfully.")

#     # Step 3: Build Docker Image
#     print("🐳 Building Docker Image...")
#     try:
#         # We assume dependencies are satisfied by the Dockerfile we just wrote
#         image, logs = client.images.build(path=".", tag="my-ai-app:latest")
#         print("✅ Docker Image 'my-ai-app:latest' built successfully!")
#     except Exception as e:
#         print(f"❌ Build failed: {e}")
#         return

#     # Step 4: Generate GitHub Actions
#     print("🚀 Generating GitHub Actions Workflow...")
#     os.makedirs(".github/workflows", exist_ok=True)
    
#     workflow_content = textwrap.dedent("""\
#         name: CI Pipeline
#         on: [push]
#         jobs:
#           build-and-test:
#             runs-on: ubuntu-latest
#             steps:
#               - uses: actions/checkout@v2
#               - name: Build Docker Image
#                 run: docker build -t my-app .
#               - name: Run Tests
#                 run: echo "Simulating automated tests..."
#     """)
#     with open(".github/workflows/main.yml", "w") as f:
#         f.write(workflow_content)
#     print("✅ GitHub Actions workflow created.")
#     print("\n🎉 Success! Run this command to start your app:")
#     print("docker run -p 5000:5000 my-ai-app:latest")

# if __name__ == "__main__":
#     run_devops_pipeline()






