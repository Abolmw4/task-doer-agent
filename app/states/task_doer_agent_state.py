from typing import TypedDict, List
from pydantic import BaseModel
from dataclasses import dataclass

# Pydantic models: Used for LLM structured output

class ResultCode(BaseModel):
    code: str | None = None


class TesterResult(BaseModel):
    code: str
    result: bool
    description: str | None = None
    syntactic_issue: str | None = None
    logic_issue: str | None = None


# TypedDict: Used for LangGraph state

class TaskDoerAgent(TypedDict):
    code_id: str
    task: str
    description: str
    prompt: str | None
    result_code: dict | None
    tester_result: dict | None
    
@dataclass
class TaskDoerAgentContext:
    user_id: str

class PlanStep(BaseModel):
    id: str
    description: str
    expected_output: str
    
class TaskPlan(BaseModel):
    goal: str
    steps: List[PlanStep]
