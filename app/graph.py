import atexit
import os
from contextlib import ExitStack
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.redis import RedisSaver
from app.nodes.task_doer_nodes import getting_task, human_decision, test_code, write_code, show_result
from app.states.task_doer_agent_state import TaskDoerAgent


MODE: str = os.getenv("MODE", "production")

workflow = StateGraph(TaskDoerAgent)
workflow.add_node("getting_task", getting_task)
workflow.add_node("write_code", write_code)
workflow.add_node("test_code", test_code)
workflow.add_node("human_decision", human_decision)
workflow.add_node("show_result", show_result)

workflow.add_edge(START, "getting_task")
# Nodes route through Command(goto=...). Static edges would also run.

if MODE == "production":
    DB_URI = os.getenv("REDIS_URL", "redis://localhost:6380")
    resources = ExitStack()
    atexit.register(resources.close)
    checkpointer = resources.enter_context(RedisSaver.from_conn_string(DB_URI))
    checkpointer.setup()
else:
    checkpointer = InMemorySaver()
app = workflow.compile(checkpointer=checkpointer)
