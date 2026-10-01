from pydantic import BaseModel

class TesterResult(BaseModel):
    code_id: str
    code: str
    result: str | None

class TaskDoerAgent(BaseModel):
    code_id: str
    result_code: str | None
    task: str
    description: str
    prompt: str
    tester_result: TesterResult | None
