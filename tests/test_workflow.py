import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph import workflow
from app.nodes import task_doer_nodes as nodes
from app.tools import task_doer_tools as tools
from app.states.task_doer_agent_state import ResultCode, TaskDoerAgent, TesterResult


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.state = TaskDoerAgent(
            code_id="test", task="Print hello", description="Print hello",
            prompt="Print hello", result_code=ResultCode(code="print('hello')"),
            tester_result=None,
        )
        self.review = TesterResult(
            code="print('hello')", result=True, description="Correct",
            syntactic_issue=None, logic_issue=None,
        )
        self.model = MagicMock()
        self.writer = MagicMock()
        self.writer.invoke.return_value = self.state.result_code
        self.reviewer = MagicMock()
        self.reviewer.invoke.return_value = self.review
        self.model.with_structured_output.side_effect = lambda schema: (
            self.writer if schema is ResultCode else self.reviewer
        )
        self.model.bind_tools.return_value.invoke.return_value = SimpleNamespace(tool_calls=[])

    def test_no_tool_call_and_null_issues_reach_approval(self):
        with patch.object(nodes, "OLLAMA_RAW_MODEL", self.model):
            result = nodes.test_code(self.state)
        self.assertEqual(result.goto, "human_decision")
        self.assertIs(result.update["tester_result"], self.review)

    def test_failed_review_retries_even_without_issue_text(self):
        self.review.result = False
        with patch.object(nodes, "OLLAMA_RAW_MODEL", self.model):
            self.assertEqual(nodes.test_code(self.state).goto, "write_code")

    def test_boolean_rejection_does_not_require_dictionary(self):
        with patch.object(nodes, "interrupt", return_value=False):
            self.assertEqual(nodes.human_decision(self.state).goto, "write_code")

    def test_generated_input_cannot_block(self):
        result = tools.python_code_executer.invoke({"code": "input('Move: ')"})
        self.assertIn("EOFError", result)

    def test_generated_infinite_loop_times_out(self):
        with patch.object(tools, "EXECUTION_TIMEOUT", 0.1):
            result = tools.python_code_executer.invoke({"code": "while True: pass"})
        self.assertIn("timed out", result)

    def test_generated_main_guard_and_output(self):
        result = tools.python_code_executer.invoke({"code": "if __name__ == '__main__': print('hello')"})
        self.assertEqual(result, "hello\n")

    def test_reject_revise_then_approve_finishes_without_parallel_writes(self):
        graph = workflow.compile(checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "test"}}
        with patch.object(nodes, "OLLAMA_RAW_MODEL", self.model):
            result = graph.invoke(self.state, config=config)
            self.assertIn("__interrupt__", result)
            result = graph.invoke(Command(resume={"approved": "no", "feedback": "Try again"}), config=config)
            self.assertIn("__interrupt__", result)
            result = graph.invoke(Command(resume={"approved": "yes"}), config=config)
        self.assertNotIn("__interrupt__", result)
        self.assertEqual(self.writer.invoke.call_count, 2)
        self.assertIn("Try again", result["prompt"])


if __name__ == "__main__":
    unittest.main()
