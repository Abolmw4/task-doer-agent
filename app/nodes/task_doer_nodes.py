from states.task_doer_agent_state import TaskDoerAgent, TesterResult
from tools.task_doer_tools import python_code_executer
from langgraph.types import Command
from langgraph.graph import END
from langchain_ollama import ChatOllama
from typing import Literal, List

try:
    OLLAMA_RAW_MODEL = ChatOllama(model="qwen3:8b", base_url="http://localhost:11434")
except Exception as error:
    print("Can't load 'qwen3:8b' model")

def getting_task(state: TaskDoerAgent) -> Command[Literal["write_code"]]:
    prompt: str = f""" I have a task.
    --------------- The title of my task -------------------
    Title: 
    {state.task}
    
    --------------- Description about task -------------------
    description: 
    {state.description}
    
    ----------------------------------
    Now please write a python code for this task and filled the code in result_code field.
    """
    return Command(update=TaskDoerAgent(code_id=state.code_id, task=state.task, description=state.description, prompt= prompt), goto="write_code")

def write_code(state: TaskDoerAgent) -> Command[Literal["test_code"]]:
    ollama_model_write_code = OLLAMA_RAW_MODEL.with_structured_output(TaskDoerAgent)
    result = ollama_model_write_code.invoke(state.prompt)
    return Command(update=TaskDoerAgent(**result), goto="test_code")

def test_code(state: TaskDoerAgent) -> Command[Literal["human_decision", "write_code"]]:
    ollama_model_for_tool_call = OLLAMA_RAW_MODEL.bind_tools([python_code_executer])
    result = ollama_model_for_tool_call.invoke(state.prompt)
    messages: List[str] = []
    messages.append(state.prompt)
    if result.tool_calls:
        for tool_call in result.tool_calls:
            if tool_call.get("name") == "python_code_executer":
                tool_result = python_code_executer.invoke(tool_call.get("args"))
    
        
    messages.append()            
    

def human_decision(state: TaskDoerAgent) -> Command[Literal["write_code", "show_result"]]:
    pass

def show_result(state: TaskDoerAgent) -> Command[Literal[END]]:
    pass
    