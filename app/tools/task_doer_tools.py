from langchain.tools import tool
import subprocess
import sys

EXECUTION_TIMEOUT = 15


@tool
def python_code_executer(code: str):
    """Execute non-interactive Python tests and return output.

    Mock input() when testing interactive programs. Execution times out after
    15 seconds; stdin is closed so interactive prompts cannot block the agent.

    Args:
        code (str): the code snipet

    Returns:
        _type_: return result of execute code.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"Python execution failed: timed out after {EXECUTION_TIMEOUT} seconds. Use non-interactive tests and mock input()."
    output = result.stdout + result.stderr
    if result.returncode:
        return f"Python execution failed (exit {result.returncode}): {output}"
    return output or "Execution successful. No output"
