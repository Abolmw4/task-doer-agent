from typing import List, Callable
from langchain_ollama import ChatOllama
from langchain.messages import ToolMessage

class ReAct:
    def __init__(self, model: ChatOllama, tools: List[Callable], max_iteration: int=5) -> None:
        self.ract_model = model.bind_tools(tools)
        self.max_iteration = max_iteration
        self.tools = {tool.name: tool for tool in tools}
        
    def __call__(self, *args):
        step, previous_observations = args
        
        messages = [{"role": "system",
                     "content":"""
                     You are a ReAct(Reason, Action, Observation) agent.
                     
                     your job is to execute the given task step.
                     
                     you do this based on this cycle:
                     
                     1. Reason about the current step.
                     2. Select the appropirate tool if necessary.
                     3. Observe the tool result.
                     4. Decide whether the expected output was achived.
                     5. Continue or finish
                     
                     Do not expose private chain-of-thought.
                     Provide concise progress summaries.

                     If the task is complete, provide the final result.
                     If you cannot complete it, explain the problem
                     """}, {"role": "user", 
                            "content":f"""
                            Current step:
                            id:{step.get('id')}
                            description:{step.get('description')}
                            expected_value:{step.get('expected_output')}
                            Previous observations:
                            {previous_observations}
                            
                            """}]
        observations = []
        for iteration in range(self.max_iteration):
            response = self.ract_model.invoke(messages)
            messages.append(response)
            if not response.tool_calls:
                return {"status": "True",
                        "result": response.content,
                        "observation": observations,
                        "iteration": iteration + 1}
                
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args")
                tool_id = tool_call.get("id")
                if tool_name not in self.tools:
                    raise ValueError(f"Unknown tool: {tool_name}")
                else:
                    observation = self.tools[tool_name].invoke(tool_args)
                    observation = f"""code / statment: {tool_args}
                                      observation: {observation}"""
                    
                    observations.append(observation)
                    
                    messages.append(ToolMessage(content=str(observation), tool_call_id=tool_id))
                
        return {"status": "True",
                "result": "Maximum ReAct iteration reached.",
                "observation": observations,
                "iteration": self.max_iteration}
