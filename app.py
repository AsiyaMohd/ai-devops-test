import os
import shutil
import uuid
import git
from flask import Flask, render_template, request
# Import our new Agent class
from Devopsagent import DevOpsAgent

app = Flask(__name__)

# Helper to clean up URLs
def clean_url(url):
    return url.strip().rstrip('/')

@app.route('/', methods=['GET', 'POST'])
def home():
    agent_report = []
    submitted_url = None
    
    if request.method == 'POST':
        submitted_url = request.form.get('repoUrl')
        token = request.form.get('githubToken')
        
        # 1. Prepare Paths
        session_id = str(uuid.uuid4())
        download_path = os.path.join("./temp_project_files", session_id)
        
        # Clean up previous runs to avoid conflicts
        if os.path.exists(download_path):
            shutil.rmtree(download_path)
            
        # 2. Construct Auth URL (if token provided)
        clean_repo_url = clean_url(submitted_url)
        auth_url = clean_repo_url
        if token and token.strip() and clean_repo_url.startswith("https://"):
            auth_url = clean_repo_url.replace("https://", f"https://{token}@")

        try:
            # 3. Clone Repository
            print(f"Cloning {clean_repo_url}...")
            git.Repo.clone_from(auth_url, download_path)
            
            # 4. Trigger Autonomous Agent
            print("Initializing DevOps Agent...")
            agent = DevOpsAgent(download_path)
            
            # Agent analyzes code and writes Dockerfile/Workflow to the temp folder
            agent_report = agent.run()
            print(agent_report)
            
            # (Optional) Here you could push the changes back to GitHub 
            # using repo.index.add and repo.remotes.origin.push()
            
        except Exception as e:
            agent_report = [f"Critical Error: {str(e)}"]

    return render_template('index.html', submitted_url=submitted_url, files=agent_report)

if __name__ == '__main__':
    # Ensure you have 'flask' and 'GitPython' installed
    app.run(debug=True, port=5000,use_reloader=False)