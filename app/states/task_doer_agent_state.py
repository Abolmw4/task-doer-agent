from pydantic import BaseModel

class ResultCode(BaseModel):
    code: str | None

class TesterResult(BaseModel):
    code: str
    result: bool
    description: str | None
    syntactic_issue: str | None
    logic_issue: str | None
    
class TaskDoerAgent(BaseModel):
    code_id: str
    result_code: ResultCode | None
    task: str
    description: str
    prompt: str | None
    tester_result: TesterResult | None
