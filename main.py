from app.observability import setup_phoenix
from openinference.instrumentation import using_attributes

# Initialize monitoring BEFORE importing graph
tracer_provider = setup_phoenix()

from app.graph import app
from uuid import uuid4
from app.states.task_doer_agent_state import TaskDoerAgent
from langgraph.types import Command
from typing import Dict, Any

def run_agent(task_title: str, description: str):
    code_id = f"code-{uuid4().hex[:8]}"
    inital_state: TaskDoerAgent = {"code_id": code_id,
                                 "result_code":None,
                                 "task": task_title,
                                 "description": description,
                                 "prompt": None,
                                 "tester_result": None}

    thread_id: str = f"task-doer-{uuid4().hex}"
    # Use a new ID for each new task execution.
    config = {"configurable": {"thread_id": thread_id}, "run_name": "TaskDoerAgent", "tags": ["task-doer-agent", "ollama"], "metadata":{"agent": "TaskDoerAgent", "thread_id": thread_id}}

    while using_attributes(session_id=thread_id, metadata={"agent": "TaskDoerAgent", "model": "qwen3:8b", "task_title": task_title, "code_id": code_id}, tags=["task-doer"]):    
        result: Dict[str, Any] = app.invoke(inital_state, config=config)
        while "__interrupt__" in result:
            inter = result["__interrupt__"][0].value
            print("code", inter["code"])
            approved = bool(input(inter["question"] + 'yes/no: '))
            # feedback = "" if approved.strip().lower() in {"yes", "y", "true"} else input("Feedback: ")
            feedback = "" if approved else input("Feedback: ")
            result = app.invoke(Command(resume={"approved": approved, "feedback":feedback}), config=config)

        print("\n" + "=" * 60)
        print("Task Complited")
        print("=" * 60)
        print(result)
        tracer_provider.force_flush()
        return result

def main():
    print("=" * 60)
    print("       TaskDoerAgent - Interactive Mode")
    print("=" * 60)
    while True:
        print("\nEnter a new task (or type 'exit' to quit)")
        task_title: str = input("Enter your task title: ").strip()
        if task_title.lower == "exit":
            print("agent stoped!")
            break
        task_description: str = input("Enter your task description: ").strip()
        try:
            run_agent(task_title=task_title, description=task_description)
        except KeyboardInterrupt:
            print("\nTask intrupted by user")
        except Exception as error:
            print(f"Error during task execution '{error}'")
            
        

if __name__ == "__main__":
    try:
        main()
    finally:
        tracer_provider.shutdown()
