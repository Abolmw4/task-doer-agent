from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from nodes.task_doer_nodes import getting_task, human_decision, test_code, write_code, show_result
from states.task_doer_agent_state import TaskDoerAgent

workflow = StateGraph(TaskDoerAgent)


workflow.add_node("getting_task", getting_task)
workflow.add_node("write_code", write_code)
workflow.add_node("test_code", test_code)
workflow.add_node("human_decision", human_decision)
workflow.add_node("show_result", show_result)

workflow.add_edge(START, "getting_task")
workflow.add_edge("getting_task", "write_code")
workflow.add_edge("write_code", "test_code")
workflow.add_edge("test_code", "human_decision")
workflow.add_edge("human_decision", "show_result")
workflow.add_edge("human_decision", "write_code")
workflow.add_edge("test_code", "write_code")
workflow.add_edge("human_decision", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
