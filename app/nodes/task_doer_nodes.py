from app.states.task_doer_agent_state import TaskDoerAgent, TesterResult, ResultCode
from app.tools.task_doer_tools import python_code_executer
from langgraph.types import Command, interrupt
from langgraph.graph import END
from langchain_ollama import ChatOllama
from typing import Literal, List

try:
    OLLAMA_RAW_MODEL = ChatOllama(model="qwen3:8b", base_url="http://localhost:11434")
except Exception as error:
    print("Can't load 'qwen3:8b' model")

def getting_task(state: TaskDoerAgent):

    prompt = f"""
    I have a task.

    Title:
    {state["task"]}

    Description:
    {state["description"]}

    Now please write Python code for this task
    and fill the code in the result_code field.
    """

    return Command(update={"prompt": prompt, "tester_result": None, "result_code": None}, goto="write_code")

def write_code(state: TaskDoerAgent):

    ollama_model_write_code = OLLAMA_RAW_MODEL.with_structured_output(ResultCode)

    if state.get("tester_result") is not None:

        previous_code = (state.get("result_code") or {}).get("code") or ""

        tester = state["tester_result"]

        issues = f"""
        This Python code has some problems:

        syntactic_issue: {tester.get("syntactic_issue")}

        logic_issue: {tester.get("logic_issue")}

        Please fix the code.
        """

        updated_prompt = [
            state["prompt"] or "",
            previous_code,
            issues
        ]

        result = ollama_model_write_code.invoke(updated_prompt)

    else:

        result = ollama_model_write_code.invoke(
            state["prompt"]
        )

    # Convert Pydantic model to a regular dictionary
    result_dict = ResultCode.model_validate(result).model_dump(
        mode="json"
    )

    return Command(update={"tester_result": None, "result_code": result_dict}, goto="test_code")
    
def test_code(state: TaskDoerAgent):

    code = (state.get("result_code") or {}).get("code")

    if not code:
        raise ValueError("No generated code found in result_code")

    ollama_model_for_tool_call = OLLAMA_RAW_MODEL.bind_tools([python_code_executer])

    ollama_model_for_getting_response = OLLAMA_RAW_MODEL.with_structured_output(TesterResult)

    messages = [state["prompt"] or "", code, "Execute Python code and check whether it is correct."]

    result = ollama_model_for_tool_call.invoke(messages)

    result_messages = [state["prompt"] or "", code,
        """
        Review the code for syntax and logic.
        Set result to true only if it is correct.
        Leave issue fields empty or null when there are no issues.
        """
    ]

    if result.tool_calls:
        for tool_call in result.tool_calls:
            if tool_call.get("name") == "python_code_executer":
                tool_result = python_code_executer.invoke(tool_call.get("args"))
                result_messages.append(str(tool_result))
                result_messages.append(
                    """
                    Review the execution results.
                    Check syntax, implementation and logic.
                    Run various unit tests.
                    Report issues when they exist.
                    """
                )

    response = ollama_model_for_getting_response.invoke(result_messages)

    # Convert Pydantic output to a regular dictionary
    response_dict = TesterResult.model_validate(response).model_dump(mode="json")

    has_issues = any((response_dict.get(issue) or "").strip() for issue in ["syntactic_issue", "logic_issue"])

    goto = ("write_code" if has_issues or not response_dict["result"] else "human_decision")

    return Command(update={"tester_result": response_dict}, goto=goto)

def human_decision(state: TaskDoerAgent):

    print("You are in human decision")

    code = (state.get("result_code") or {}).get("code")

    decision = interrupt({
        "code": code,
        "question": "Do you approve this code?",
        "options": ["yes", "no"],
        "description": "If you reject the code, please provide feedback."
    })

    if isinstance(decision, bool):
        approved = decision
        feedback = ""

    elif isinstance(decision, dict):

        answer = decision.get("approved", False)

        approved = (answer if isinstance(answer, bool) else str(answer).strip().lower() in {"yes", "y", "true"})

        feedback = decision.get("feedback", "")

    else:

        approved = str(decision).strip().lower() in {"yes", "y", "true", "approved"}

        feedback = ""

    if approved:

        return Command(update={}, goto="show_result")

    prompt = (state.get("prompt") or "") + f"\nFeedback:\n{feedback}"

    return Command(update={"prompt": prompt}, goto="write_code")



def show_result(state: TaskDoerAgent):

    print("You are in show_result node")

    result_code = state.get("result_code") or {}

    print(result_code.get("code"))

    return Command(update={}, goto=END)
