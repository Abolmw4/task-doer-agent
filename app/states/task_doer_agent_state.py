from pydantic import BaseModel

class TaskDoerAgent(BaseModel):
    code_id: str
    result_code: str | None
    task: str
    description: str
    