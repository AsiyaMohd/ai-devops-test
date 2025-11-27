import os
import docker
import time
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
# TOOLS
# ---------------------------------------------------------

@tool
def list_files(path: str = ".") -> str:
    """Lists files in the directory."""
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Error listing files: {e}"


@tool
def write_file(filename: str, content: str) -> str:
    """Writes content to a file."""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(content)
        return f"Successfully wrote {filename}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def build_docker_image(tag: str) -> str:
    """Builds docker image."""
    try:
        client = docker.from_env()
        client.images.build(path=".", tag=tag)
        return f"Docker image built: {tag}"
    except Exception as e:
        return f"Docker Build Failed: {e}"


@tool
def run_container(tag: str, port: int) -> str:
    """Runs docker container."""
    try:
        client = docker.from_env()
        # stop old container
        try:
            old = client.containers.get("agent_runner")
            old.stop()
            old.remove()
        except:
            pass

        container = client.containers.run(
            tag,
            name="agent_runner",
            ports={f"{port}/tcp": port},
            detach=True
        )
        return f"Container running at http://localhost:{port}"
    except Exception as e:
        return f"Run Error: {e}"


@tool
def write_github_actions_workflow(name: str, content: str) -> str:
    """Writes GitHub Actions workflow YML file."""
    try:
        os.makedirs(".github/workflows", exist_ok=True)
        path = f".github/workflows/{name}.yml"

        # FIX: ensure YAML is written EXACTLY without breaking indentation
        with open(path, "w", encoding="utf-8") as wf:
            wf.write(content)

        return f"Workflow created at {path}"
    except Exception as e:
        return f"Error writing workflow: {e}"


@tool
def git_commit_and_push(message: str = "Automated commit by AI agent") -> str:
    """Adds, commits, and pushes."""
    try:
        os.system("git add .")
        os.system(f'git commit -m "{message}"')
        os.system("git branch")  # debug
        os.system("git push --force")
        return "Pushed to GitHub"
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
    write_github_actions_workflow,
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
    print("🚀 DevOps Agent Starting...\n")

    prompt = """
You are a DevOps Agent.
1. Analyze backend code type.
2. Write a Dockerfile.
3. Build Docker image: ai-devops-app.
4. Run container on port 5000.
5. Create GitHub Actions workflow named 'ci-cd':
   - Checkout code
   - Set up Python
   - Install dependencies
   - Lint
   - Run Tests
   - Build & Push Docker image to GHCR
6. Save workflow file as .github/workflows/ci-cd.yml
7. Git commit and push.
8. Stop after push.
"""

    final_state = app.invoke({"messages": [HumanMessage(content=prompt)]})
    print("\n🎉 Pipeline Automation Complete!")
