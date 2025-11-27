import os
import docker
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages

# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------
# Fixed workflow template (guaranteed valid YAML)
# You can edit this template later if you need to add steps.
# ---------------------------------------------------------
# ---------------------------------------------------------
# Fixed workflow template (Strict YAML compliance)
# ---------------------------------------------------------
WORKFLOW_TEMPLATE = """---
name: CI/CD Pipeline

"on":
  push:
    branches:
      - master
  pull_request:
    branches:
      - master
  workflow_dispatch:
permissions:
  contents: read
  packages: write
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      IMAGE_NAME: ghcr.io/${{ github.repository_owner }}/ai-devops-app
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Lint with flake8
        run: |
          pip install flake8
          # Stop the build if there are Python syntax errors or undefined names
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
          # exit-zero treats all errors as warnings.
          flake8 . --count --exit-zero --max-complexity=10 \\
            --max-line-length=127 --statistics

      - name: Run tests
        run: |
          pip install pytest
          pytest

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Lowercase Image Name
        run: |
          echo "IMAGE_NAME=${IMAGE_NAME,,}" >>${GITHUB_ENV}
      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: >-
            ghcr.io/${{ github.repository_owner }}/ai-devops-app:latest
"""

# ---------------------------------------------------------
# TOOLS (these are still available for the agent)
# ---------------------------------------------------------

@tool
def list_files(path: str = ".") -> str:
    """List files in a directory."""
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Error listing files: {e}"

@tool
def write_file(filename: str, content: str) -> str:
    """Write files in a directory."""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        # write using LF endings
        with open(filename, "w", encoding="utf-8", newline="\n") as f:
            f.write(content.replace("\r\n", "\n").replace("\r", "\n"))
        return f"Successfully wrote {filename}"
    except Exception as e:
        return f"Error writing file: {e}"

@tool
def build_docker_image(tag: str) -> str:
    """Building docker image in directory."""
    try:
        client = docker.from_env()
        client.images.build(path=".", tag=tag)
        return f"Docker image built: {tag}"
    except Exception as e:
        return f"Docker Build Failed: {e}"

@tool
def run_container(tag: str, port: int) -> str:
    """Run Container"""
    try:
        client = docker.from_env()
        try:
            old = client.containers.get("agent_runner")
            old.stop()
            old.remove()
        except:
            pass
        client.containers.run(tag, name="agent_runner", ports={f"{port}/tcp": port}, detach=True)
        return f"Container running at http://localhost:{port}"
    except Exception as e:
        return f"Run Error: {e}"

# write workflow tool still present but agent will NOT be asked to generate YAML
@tool 
def write_github_actions_workflow(name: str, content: str) -> str:
    """Writing github actions"""
    try:
        os.makedirs(".github/workflows", exist_ok=True)
        path = f".github/workflows/{name}.yml"
        
        # Enforce LF endings and strip purely leading/trailing whitespace
        # This fixes 'missing document start' if an empty line crept in
        content_clean = content.strip()
        
        # Ensure it actually starts with ---
        if not content_clean.startswith("---"):
            content_clean = "---\n" + content_clean
            
        # Normalize line endings to \n (Linux style)
        content_lf = content_clean.replace("\r\n", "\n").replace("\r", "\n")
        
        # Ensure a single newline at the end of the file (POSIX standard)
        if not content_lf.endswith("\n"):
            content_lf += "\n"

        with open(path, "w", encoding="utf-8", newline="\n") as wf:
            wf.write(content_lf)
            
        return f"Workflow created at {path}"
    except Exception as e:
        return f"Error writing workflow: {e}"

@tool
def git_commit_and_push(message: str = "Automated CI/CD commit") -> str:
    """Git commit and push"""
    try:
        # make sure git has user configured (if running in fresh environment)
        os.system('git config --global user.email "you@example.com"')
        os.system('git config --global user.name "AI Agent"')
        os.system("git add .")
        # commit only when there are staged changes
        status = os.popen("git status --porcelain").read().strip()
        if status == "":
            return "No changes to commit"
        os.system(f'git commit -m "{message}"')
        push_result = os.system("git push")
        return "Pushed to GitHub" if push_result == 0 else f"Git push exit code: {push_result}"
    except Exception as e:
        return f"Git push failed: {e}"

# ---------------------------------------------------------
# LLM SETUP
# ---------------------------------------------------------
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_DEPLOYMENT"),
    api_version=os.getenv("AZURE_VERSION"),
    azure_endpoint=os.getenv("AZURE_END_POINT"),
    api_key=os.getenv("AZURE_API_KEY"),
    temperature=0,
)

tools = [
    list_files,
    write_file,
    build_docker_image,
    run_container,
    write_github_actions_workflow,  # kept for completeness
    git_commit_and_push,
]

llm_with_tools = llm.bind_tools(tools)

# ---------------------------------------------------------
# AGENT BRAIN
# ---------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def reasoner_node(state: AgentState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

def tool_executor_node(state: AgentState):
    from langgraph.prebuilt import ToolNode
    node = ToolNode(tools)
    return node.invoke(state)

def should_continue(state: AgentState):
    last = state["messages"][-1]
    if not last.tool_calls:
        return END
    return "tools"

workflow = StateGraph(AgentState)
workflow.add_node("agent", reasoner_node)
workflow.add_node("tools", tool_executor_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

app = workflow.compile()

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    print("🚀 DevOps Agent starting...")

    # keep prompt focused: agent will analyze and write Dockerfile; DO NOT generate workflow in LLM output.
    prompt = """
You are a DevOps agent. You MUST NOT generate or output the full GitHub Actions YAML.
Tasks to perform (only these):
1) Analyze repository files and determine backend type (python/node/java) and entrypoint.
2) Generate an appropriate Dockerfile and write it to the workspace as 'Dockerfile' using the write_file tool.
3) Build the docker image named 'ai-devops-app' using build_docker_image.
4) If build is successful, run the container on port 5000 using run_container.
5) Return a short JSON-like summary of actions you performed (language, entrypoint, image_tag, container_url).
Important rules:
- DO NOT attempt to create the GitHub Actions YAML. The host program will write a validated workflow template after you finish.
- Use the available tools only: list_files, write_file, build_docker_image, run_container.
"""

    # run the agent reasoning + tools for analysis and Dockerfile creation
    final_state = app.invoke({"messages": [HumanMessage(content=prompt)]})

    # AFTER AGENT FINISHES: write guaranteed-valid workflow (we do this in code to avoid YAML errors)
    print("Writing guaranteed-valid GitHub Actions workflow from template...")
    res = write_github_actions_workflow.invoke({"name": "ci-cd", "content": WORKFLOW_TEMPLATE})
    print(res)

    # commit & push if there are changes
    git_res = git_commit_and_push.invoke({"message": "Add CI workflow and any agent changes"})
    print(git_res)

    print("\n🎉 Done - the workflow file has been written and pushed (if git credentials present).")
    print("Now check .github/workflows/ci-cd.yml and GitHub Actions tab.")
