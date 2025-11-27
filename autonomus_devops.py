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
load_dotenv()
# ---------------------------------------------------------

# -------------------------
#        TOOLS
# -------------------------

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
    """Builds the docker image."""
    try:
        client = docker.from_env()
        client.images.build(path=".", tag=tag)
        return "SUCCESS"
    except Exception as e:
        return f"Docker Build Failed: {e}"

@tool
def run_container(tag: str, port: int) -> str:
    """Runs docker container."""
    try:
        client = docker.from_env()
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
        return f"RUNNING at http://localhost:{port}"
    except Exception as e:
        return f"Run Error: {e}"

@tool
def write_github_actions_workflow(name: str, content: str) -> str:
    """
    Writes GitHub Actions workflow YAML file into .github/workflows/
    """
    try:
        path = f".github/workflows/{name}.yml"
        os.makedirs(".github/workflows", exist_ok=True)
        with open(path, "w") as wf:
            wf.write(content)
        return f"Workflow created: {path}"
    except Exception as e:
        return f"Error writing workflow: {e}"

@tool
def git_commit_and_push(message: str = "Automated commit by AI agent") -> str:
    """Adds, commits, and pushes the repository."""
    try:
        os.system("git add .")
        os.system(f'git commit -m "{message}"')
        os.system("git push")
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

tools = [list_files, write_file, build_docker_image, run_container,
         write_github_actions_workflow, git_commit_and_push]

llm_with_tools = llm.bind_tools(tools)

# -------------------------
#       AGENT BRAIN
# -------------------------

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def reasoner_node(state: AgentState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

def tool_executor_node(state: AgentState):
    from langgraph.prebuilt import ToolNode
    tool_node = ToolNode(tools)
    return tool_node.invoke(state)

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return END
    return "tools"

workflow = StateGraph(AgentState)
workflow.add_node("agent", reasoner_node)
workflow.add_node("tools", tool_executor_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

app = workflow.compile()

# -------------------------
#       MAIN EXECUTION
# -------------------------

if __name__ == "__main__":
    print("🚀 DevOps Agent starting...")

    prompt = (
        "You are a DevOps Agent.\n"
        "1. Analyze codebase and detect backend type.\n"
        "2. Write Dockerfile.\n"
        "3. Build docker image: ai-devops-app.\n"
        "4. Run docker container on port 5000.\n"
        "5. Create GitHub Actions CI/CD workflow including:\n"
        "   - Install dependencies\n"
        "   - Run tests\n"
        "   - Linting\n"
        "   - Build Docker image\n"
        "   - Push image to GHCR\n"
        "6. Save workflow file as 'ci-cd'\n"
        "7. Commit & push everything to GitHub.\n"
        "8. Stop after push.\n"
    )

    final_state = app.invoke({"messages": [HumanMessage(content=prompt)]})

    print("\n🎉 Pipeline Automation Complete!")
