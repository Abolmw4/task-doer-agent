from langchain_ollama import ChatOllama
from app.states.task_doer_agent_state import PlanStep, TaskPlan

class TaskDecomposer:
    def __init__(self, model: ChatOllama) -> None:
        self.decomposer_model = model.with_structured_output(TaskPlan)
        
    def task_decomposer(self, title: str, description: str) -> TaskPlan:
        prompt: str = f"""
        you are a task decomposer agent.
        
        our responsibility is to decompose the given task based on chain of thougt.
        Let's do it step-by-step
        
        Task:
        {title}
        
        Description:
        {description}
        
        Return the result using the provided structured schema.
        """
        result = self.decomposer_model.invoke(prompt)
        return result

    def __repr__(self):
        pass
        