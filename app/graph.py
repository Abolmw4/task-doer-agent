import atexit
import os
from contextlib import ExitStack
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.postgres import PostgresStore
from app.nodes.task_doer_nodes import getting_task, human_decision, test_code, write_code, show_result
from app.states.task_doer_agent_state import TaskDoerAgent, TaskDoerAgentContext


MODE: str = os.getenv("MODE", "production")

workflow = StateGraph(TaskDoerAgent, context_schema=TaskDoerAgentContext)

workflow.add_node("getting_task", getting_task)
workflow.add_node("write_code", write_code)
workflow.add_node("test_code", test_code)
workflow.add_node("human_decision", human_decision)
workflow.add_node("show_result", show_result)

workflow.add_edge(START, "getting_task")
# Nodes route through Command(goto=...). Static edges would also run.

if MODE == "production":
    SHORT_DB_URI = os.getenv("REDIS_URL", "redis://localhost:6380")
    LONG_DB_URI = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"
    resources = ExitStack()
    atexit.register(resources.close)
    
    # Short-term memery
    checkpointer = resources.enter_context(RedisSaver.from_conn_string(SHORT_DB_URI))
    checkpointer.setup()
    
    # Long-term memory
    store = resources.enter_context(PostgresStore.from_conn_string(LONG_DB_URI))
    store.setup()

else:
    # Short-term memory
    checkpointer = InMemorySaver()
    
    # Long-term memory
    store = InMemoryStore()
    
app = workflow.compile(checkpointer=checkpointer, store=store)
