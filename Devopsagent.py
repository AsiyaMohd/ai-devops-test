import os
import docker
import sys
import socket
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
def find_free_port(start_port=8000, max_retries=100):
        for port in range(start_port, start_port + max_retries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # Try to bind to the port. If successful, it's free.
                try:
                    s.bind(('0.0.0.0', port))
                    return port
                except OSError:
                    continue # Port is busy, try next one
        raise Exception("No free ports found available!")
class DevOpsAgent:
    def __init__(self, repo_path):
        # FIX: Convert to Absolute Path immediately to prevent Docker "Ghost Builds"
        self.repo_path = os.path.abspath(repo_path)
        print(f"[DEBUG] Initializing Agent for Absolute Path: {self.repo_path}")
        
        self.project_name = os.path.basename(os.path.normpath(repo_path))
        
        try:
            self.llm = AzureChatOpenAI(
                azure_deployment=os.getenv("AZURE_DEPLOYMENT"),
                api_version=os.getenv("AZURE_VERSION"),
                azure_endpoint=os.getenv("AZURE_END_POINT"),
                api_key=os.getenv("AZURE_API_KEY"),
                temperature=0.2 
            )
        except Exception as e:
            raise ValueError(f"❌ Failed to initialize Azure OpenAI. Check your ENV variables. Error: {e}")

    def _get_project_context(self):
        """Reads key config files with robust encoding."""
        print("[DEBUG] Scanning for project files...")
        context = ""
        critical_files = ['requirements.txt', 'package.json', 'app.py', 'main.py']
        
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file in critical_files:
                    path = os.path.join(root, file)
                    try:
                        # Try UTF-8 first, fallback to Latin-1
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                file_content = "".join([next(f) for _ in range(50)])
                        except UnicodeDecodeError:
                            with open(path, 'r', encoding='latin-1') as f:
                                file_content = "".join([next(f) for _ in range(50)])
                                
                        context += f"\n--- FILE: {file} ---\n{file_content}\n"
                    except Exception as e:
                        print(f"[WARN] Could not read {file}: {e}")
        return context

    def ensure_entrypoint(self):
        """Creates a dedicated entrypoint script to force binding to 0.0.0.0."""
        print("🔧 Creating Docker Entrypoint...")
        
        entrypoint_content = """import sys
import os

try:
    from app import app
    print("Successfully imported 'app' from app.py")
except ImportError as e:
    print(f"Could not import 'app': {e}")
    print("Creating fallback app...")
    from flask import Flask
    app = Flask(__name__)
    @app.route('/')
    def home():
        return "<h1>Fallback App</h1><p>The container is running, but app.py failed to load.</p>"

if __name__ == "__main__":
    print("Starting Server on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
"""
        target_file = os.path.join(self.repo_path, 'docker_entrypoint.py')
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(entrypoint_content)
                f.flush()
                os.fsync(f.fileno())
            
            if os.path.getsize(target_file) > 0:
                print(f"[DEBUG] ✅ Entrypoint created successfully ({os.path.getsize(target_file)} bytes)")
            else:
                print("[CRITICAL ERROR] ❌ Entrypoint file is empty after write!")
        except Exception as e:
            print(f"[CRITICAL ERROR] ❌ Error writing entrypoint: {str(e)}")

    def generate_dockerfile(self, context):
        print(f"[DEBUG] Generating Dockerfile for {self.project_name}...")
        
        prompt = f"""
        You are a DevOps Expert. Write a SIMPLE, WORKING Dockerfile.
        
        Project Context:
        {context}
        
        STRICT RULES:
        Do not mention Dockerfile in first line
        1. Base Image: python:3.9-slim
        2. Workdir: /app
        3. Install: COPY requirements.txt . && pip install --no-cache-dir -r requirements.txt
           (If requirements.txt has numpy/pandas, install 'build-essential' first)
        4. Copy Code: COPY . .
        5. Network: EXPOSE 5000
        6. Command: CMD ["python", "docker_entrypoint.py"]
        
        OUTPUT ONLY THE RAW DOCKERFILE CONTENT.
        """

        messages = [HumanMessage(content=prompt)]
        response = self.llm.invoke(messages)
        content = response.content.replace("```dockerfile", "").replace("```", "").strip()
        
        with open(os.path.join(self.repo_path, 'Dockerfile'), 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("[DEBUG] Dockerfile Written.")
        return "Dockerfile (Using docker_entrypoint.py)"

    def generate_docker_compose(self, context):
        return "docker-compose.yml (Skipped)"

    def generate_github_workflow(self):
        return ".github/workflows/main.yml (Skipped)"
    
    def deploy_container(self):
        print(f"[DEBUG] Starting Deployment for {self.project_name}...")
        #host_port=find_free_port(8000)
        try:
            client = docker.from_env()
            # Convert tag to lowercase to comply with Docker rules
            image_tag = self.project_name.lower()
            
            # 1. Build with STREAMING LOGS
            print("   Step 1: Building Image (Streaming Logs)...")
            
            try:
                # Use ABSOLUTE PATH here
                build_generator = client.api.build(
                    path=self.repo_path, # Now guaranteed to be absolute
                    tag=image_tag,
                    rm=True,
                    decode=True
                )
                
                build_success = False
                for chunk in build_generator:
                    # Print any message from Docker to debug "Ghost Builds"
                    if 'stream' in chunk:
                        print(chunk['stream'], end='')
                        build_success = True # We saw at least one log line
                    elif 'error' in chunk:
                        raise Exception(f"Build Error: {chunk['error']}")
                    else:
                        # Print raw chunk for debugging unknown responses
                        print(f"[RAW DOCKER]: {chunk}")
                
                if not build_success:
                    print("\n[WARNING] Docker returned no stream logs. Context might be empty.")

                print("\n   ✅ Build Stream Finished.")
                
                # SAFETY CHECK: Verify image exists
                client.images.get(image_tag)

            except Exception as build_err:
                raise Exception(f"Docker Build Failed: {str(build_err)}")

            # 2. Cleanup Old Container
            print("[DEBUG] Cleaning up old containers...")
            try:
                old = client.containers.get(image_tag)
                old.stop()
                old.remove()
            except: 
                pass
            
            # 3. Run with Environment Variables
            print("   Step 2: Starting Container (Mapping 8000->5000)...")
            
            env_vars = {
                "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY"),
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
                "AZURE_API_KEY": os.getenv("AZURE_API_KEY"),
                "AZURE_ENDPOINT": os.getenv("AZURE_ENDPOINT"),
                "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION"),
                "AZURE_DEPLOYMENT": os.getenv("AZURE_DEPLOYMENT")
            }
            env_vars = {k: v for k, v in env_vars.items() if v is not None}

            container = client.containers.run(
                image_tag,
                detach=True,
                name=image_tag,
                ports={'5000/tcp': 0},
                environment=env_vars
            )
            print(f"[DEBUG] Container Started! ID: {container.id}")
            
            return "✅ Deployed! Access at: http://localhost:${host_port}"

        except Exception as e:
            print(f"[CRITICAL ERROR] Deployment Failed: {str(e)}")
            return f"❌ Deployment Failed: {str(e)}"

    def run(self):
        try:
            self.ensure_entrypoint()
            context = self._get_project_context()
            f1 = self.generate_dockerfile(context)
            status = self.deploy_container()
            return [f1, status]
        except Exception as e:
            return [f"Error: {str(e)}"]