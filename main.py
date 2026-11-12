from app.observability import setup_phoenix
from openinference.instrumentation import using_attributes

# Initialize monitoring BEFORE importing graph
tracer_provider = setup_phoenix()

from app.graph import app
from uuid import uuid4
from app.states.task_doer_agent_state import TaskDoerAgent
from langgraph.types import Command
from typing import Dict, Any

def main():
    inital_state: TaskDoerAgent = {"code_id": "code-101",
                                 "result_code":None,
                                 "task": "Tic Toc Toe game",
                                 "description": "I have to play Tic Toc Toe with computer(I mean me vs computer play tic toc toe)",
                                 "prompt": None,
                                 "tester_result": None}


    # Use a new ID for each new task execution.
    config = {"configurable": {"thread_id": "task-doer-101"}, "run_name": "TaskDoerAgent", "tags": ["task-doer-agent", "ollama"], "metadata":{"agent": "TaskDoerAgent", "thread_id": "task-doer-101"}}

    while using_attributes(session_id="task-doer-101", metadata={"agent": "TaskDoerAgent", "model": "qwen3:8b"}, tags=["task-doer"]):    
        result: Dict[str, Any] = app.invoke(inital_state, config=config)
        while "__interrupt__" in result:
            inter = result["__interrupt__"][0].value
            print("code", inter["code"])
            approved = bool(input(inter["question"] + 'yes/no: '))
            # feedback = "" if approved.strip().lower() in {"yes", "y", "true"} else input("Feedback: ")
            feedback = "" if approved else input("Feedback: ")
            result = app.invoke(Command(resume={"approved": approved, "feedback":feedback}), config=config)

        print("\n" + "=" * 60)
        print("Graph Execution Completed")
        print("=" * 60)
        print(result)
        tracer_provider.force_flush()

if __name__ == "__main__":
    main()
