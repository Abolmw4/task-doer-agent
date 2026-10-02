from app.states.task_doer_agent_state import TaskDoerAgent, TesterResult, ResultCode
from app.tools.task_doer_tools import python_code_executer
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
    return Command(update=TaskDoerAgent(code_id=state.code_id, task=state.task, description=state.description, prompt=prompt, tester_result=None, result_code=None), goto="write_code")

def write_code(state: TaskDoerAgent) -> Command[Literal["test_code"]]:
    ollama_model_write_code = OLLAMA_RAW_MODEL.with_structured_output(ResultCode)
    if state.tester_result is not None:
        issues = f"""
        this python code hase some promblem like:
        syntactic_issue: {state.tester_result.syntactic_issue}
        
        logic_issue: {state.tester_result.logic_issue}
        
        pleas fixed the code
        """
        updated_prompt: List[str] = [state.prompt, issues]
        result = ollama_model_write_code.invoke(updated_prompt)
        return Command(update=TaskDoerAgent(code_id=state.code_id, task=state.task, description=state.description, prompt=state.prompt, tester_result=None, result_code=result), goto="test_code")
    
    result = ollama_model_write_code.invoke(state.prompt)
    return Command(update=TaskDoerAgent(code_id=state.code_id, task=state.task, description=state.description, prompt=state.prompt, tester_result=None, result_code=result), goto="test_code")

def test_code(state: TaskDoerAgent) -> Command[Literal["human_decision", "write_code"]]:
    ollama_model_for_tool_call = OLLAMA_RAW_MODEL.bind_tools([python_code_executer])
    ollama_molde_for_getting_response = OLLAMA_RAW_MODEL.with_structured_output(TesterResult)
    messages: List[str] = [state.prompt, state.result_code.code, "Execut python code and check is corect or not(based on syntax and unittests). and tell is ok or not"]
    result = ollama_model_for_tool_call.invoke(messages)
    result_messages: List[str] = [state.prompt, state.result_code.code]
    if result.tool_calls:
        for tool_call in result.tool_calls:
            if tool_call.get("name") == "python_code_executer":
                tool_result = python_code_executer.invoke(tool_call.get("args"))        
                result_messages.append(tool_result)
                result_messages.append("Please check and review this code based on sysntax, implimentation and logic. Run various unittests on it; if you encounter any issues, fill in the fields related to the syntactic_issue or logic_issue if the code has not any issue nothing set into syntactic_issue or logic_issue. If there are no issues, leave those fields blank. You may also provide your general feedback regarding the code and the tests you performed in the description field.")
        response = ollama_molde_for_getting_response.invoke(result_messages)
        
        goto = "write_code" if response.syntactic_issue != '' or response.logic_issue != '' else "human_decision"
    
    return Command(update=TaskDoerAgent(code_id=state.code_id, task=state.task, description=state.description, prompt=state.prompt, tester_result=response, result_code=state.result_code), goto=goto)

           

def human_decision(state: TaskDoerAgent) -> Command[Literal["write_code", "show_result"]]:
    print("in human decision")

def show_result(state: TaskDoerAgent) -> Command[Literal[END]]:
    pass
    