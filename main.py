from app.graph import app
from app.states.task_doer_agent_state import TaskDoerAgent
from langgraph.types import Command
from typing import Dict, Any

def main():
    inital_state = TaskDoerAgent(code_id="code-101", 
                                 result_code=None, 
                                 task="Tic Toc Toe game", 
                                 description="I have to play Tic Toc Toe with computer(I mean me vs computer play tic toc toe)", 
                                 prompt = None,
                                 tester_result = None)
    
    config = {"configurable": {"thread_id": "task-doer-101"}}
    result: Dict[str, Any] = app.invoke(inital_state, config=config)
    if "__interrupt__" in result:
        inter = result["__interrupt__"][0].value
        print("code", inter["code"])
        approved = input(inter["question"] + 'yes/no: ')       
        result = app.invoke(Command(resume={"approved": approved, "feedback":""}), config=config)
    
    print("\n" + "=" * 60)
    print("Graph Execution Completed")
    print("=" * 60)
    print(result)

if __name__ == "__main__":
    main()
