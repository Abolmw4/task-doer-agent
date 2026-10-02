from app.graph import app
from app.states.task_doer_agent_state import TaskDoerAgent
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
    print(result)

if __name__ == "__main__":
    main()