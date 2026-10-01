from states.task_doer_agent_state import TaskDoerAgent, TesterResult
from langgraph.types import Command
from langgraph.graph import END
from typing import Literal

def getting_task(state: TaskDoerAgent) -> Command[Literal["write_code"]]:
    

def write_code(state: TaskDoerAgent) -> Command[Literal["test_code"]]:
    pass

def test_code(state: TaskDoerAgent) -> Command[Literal["human_decision", "write_code"]]:
    pass

def human_decision(state: TaskDoerAgent) -> Command[Literal["write_code", "show_result"]]:
    pass

def show_result(state: TaskDoerAgent) -> Command[Literal[END]]:
    pass
    