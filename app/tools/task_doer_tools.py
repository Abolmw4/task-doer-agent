from langchain.tools import tool
import contextlib
import io
import traceback


@tool
def python_code_executer(code: str):
    """Execut python code and retrun output of executed code

    Args:
        code (str): the code snipet

    Returns:
        _type_: return result of execute code.
    """
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, {})
        output = stdout.getvalue()
        if not output:
            return "Execution sucessful. No output"
        return output
    except Exception:
        return f"python execution failed: {traceback.format_exc()}"
