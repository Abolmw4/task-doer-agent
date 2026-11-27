from app.hitl import parse_approval
from app.states.task_doer_agent_state import TaskDoerAgent, TesterResult, ResultCode, TaskDoerAgentContext, TaskPlan
from app.tools.task_doer_tools import python_code_executer
from app.planning.decomposer import TaskDecomposer
from app.planning.react import ReAct
from langgraph.types import Command, interrupt
from langgraph.graph import END
from langgraph.runtime import Runtime
from langchain_ollama import ChatOllama
from typing import Literal, List, Callable
from uuid import uuid4

OLLAMA_RAW_MODEL = ChatOllama(model="qwen3:8b", base_url="http://localhost:11434")

decomposer = TaskDecomposer(model = OLLAMA_RAW_MODEL)
ReActFramwork = ReAct(model=OLLAMA_RAW_MODEL, tools=[python_code_executer], max_iteration=3)
CODE_WRITER = OLLAMA_RAW_MODEL.with_structured_output(ResultCode)

def getting_task(state: TaskDoerAgent, runtime: Runtime[TaskDoerAgentContext]):
    print("In the 'getting_task' node")
    user_id = runtime.context.user_id
    
    print("user_id", user_id)
    namespace = (user_id, "memories")
    
    memories = runtime.store.search(namespace, limit=20)
    previus_memories = [memroy.value["data"] for memroy in memories]
    print("memories", previus_memories, '\n', 10*"=", '\n')
        
    plan: TaskPlan = decomposer.task_decomposer(title=state["task"], description=state["description"], previus_memoris=previus_memories) if len(previus_memories) > 0 else decomposer.task_decomposer(title=state["task"], description=state["description"], previus_memoris=None)
    
    print(10*'=', "Plan" ,'\n', plan)
    prompt = f"""
    I have a task.

    Title:
    {state["task"]}

    Description:
    {state["description"]}
        
    step by step plan for ding this task:
    {TaskPlan.model_validate(plan).model_dump(mode="json")}
    """
    
    return Command(update={"prompt": prompt, "tester_result": None, "result_code": None, "plan": TaskPlan.model_validate(plan).model_dump(mode="json")}, goto="write_code")

def write_code(state: TaskDoerAgent):
    print("In the 'write_code' node")
    
    observation = None
    step_result: List[dict] = []
    for idx, item in enumerate(state.get("plan")["steps"]):
        result = ReActFramwork(item, observation)
        observation = result
        state["current_step"] = idx + 1
        step_result.append(result)
        
    state["step_results"] = step_result
    state["latest_observation"] = observation
    wirte_code_prompt: str = state.get("prompt") + f"""
    plan or ReAct reuslt:
    {step_result}
    
    please attention to code / statment field
    """
        
    final_code = CODE_WRITER.invoke(wirte_code_prompt)
    
    return Command(update={"current_step": state["current_step"], "step_results": step_result, "latest_observation": observation, "result_code": ResultCode.model_validate(final_code).model_dump(mode="json")}, goto="test_code")
    

def test_code(state: TaskDoerAgent):
    print("In the 'test_code' node")
    
    code = state.get("result_code")["code"]
    print(f"output code: ", code, '\n')
    
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

        approved = (answer if isinstance(answer, bool) else parse_approval(answer))

        feedback = str(decision.get("feedback") or "").strip()

    else:

        approved = parse_approval(decision)

        feedback = ""

    if approved:

        return Command(update={}, goto="show_result")

    prompt = state.get("prompt") or ""

    if feedback:

        prompt = f"{prompt}\nFeedback:\n{feedback}"

    return Command(update={"prompt": prompt}, goto="write_code")


def show_result(state: TaskDoerAgent, runtime: Runtime[TaskDoerAgentContext]):
    user_id = runtime.context.user_id
    namespace = (user_id, "memories")
    memory_id = str(uuid4())
    memory_data = {"data": state.get('result_code')}
    runtime.store.put(namespace, memory_id, memory_data)
    
    print("You are in show_result node")

    result_code = state.get("result_code") or {}

    print(result_code)

    return Command(update={}, goto=END)
