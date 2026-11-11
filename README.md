# Task Doer Agent

An autonomous, human-in-the-loop AI coding agent built with **LangGraph**. Give it a task in plain English and it will write the Python code, execute it, review it for syntax and logic issues, repair it iteratively — and pause for your approval before delivering the final result.

All inference runs **locally** through [Ollama](https://ollama.com/). No cloud API keys required.

> **Status:** Work in progress — the core agent loop is functional and actively being extended.

---

## How It Works

The agent is a LangGraph `StateGraph` with five nodes. Routing is dynamic — each node returns a `Command` that decides where the graph goes next:

```
 START
   │
   ▼
┌──────────────┐
│ getting_task │  Builds the prompt from the task + description
└──────┬───────┘
       ▼
┌────────────┐     ┌──────────────────────────────────────┐
│ write_code │ ◄── │  Retry loop (feedback from failures) │
└─────┬──────┘     └──────────────────────────────────────┘
      ▼
┌───────────┐   The model runs the code via a tool call,
│ test_code │   reviews it, and returns a structured verdict
└─────┬─────┘
      │
      ├─ syntax/logic issues? ──► back to write_code
      ▼
┌────────────────┐
│ human_decision │  ⏸ Graph interrupts — shows you the code
└─────┬──────────┘  and waits for approval
      │
      ├─ rejected (+ feedback) ──► back to write_code
      ▼
┌─────────────┐
│ show_result │  Prints the approved code
└─────┬───────┘
      ▼
     END
```

### The agent loop in detail

1. **`getting_task`** — Composes the generation prompt from the task name and description in the graph state.
2. **`write_code`** — Calls the LLM with structured output (`ResultCode`) so the model always returns valid JSON containing the code. On retries, the previous test failures (`syntactic_issue`, `logic_issue`) are appended to the prompt so the model can fix its own mistakes.
3. **`test_code`** — The LLM is given the `python_code_executer` tool. It calls the tool to actually execute the generated code, then reviews the output and returns a structured `TesterResult` verdict (pass/fail, syntax issues, logic issues). Failures route back to `write_code` automatically.
4. **`human_decision`** — Uses LangGraph's `interrupt()` to pause the graph and surface the generated code to you in the terminal. Approve it, or reject it with feedback — the agent loops back and revises.
5. **`show_result`** — Prints the final, human-approved code.

---

## Features

- 🤖 **Fully local LLM** — runs on Ollama (`qwen3:8b`), no API keys or cloud costs
- 🔄 **Self-healing code loop** — test failures are fed back to the model as structured feedback until the code works
- 🛠️ **Real tool calling** — the agent executes the code it writes via `python_code_executer` and reviews the actual runtime output
- 🧑‍⚖️ **Human-in-the-loop approval** — the graph interrupts and waits for your `yes/no` (plus optional feedback) before finishing
- 💾 **Checkpointed state** — `MemorySaver` + thread IDs make interrupt/resume reliable
- 📐 **Structured output** — Pydantic schemas (`ResultCode`, `TesterResult`) keep model responses machine-readable

---

## Project Structure

```
task-doer-agent/
├── main.py                          # Entry point — runs the demo task
├── app/
│   ├── graph.py                     # LangGraph workflow definition + compilation
│   ├── nodes/
│   │   └── task_doer_nodes.py       # All 5 node implementations
│   ├── states/
│   │   └── task_doer_agent_state.py # Pydantic state models
│   └── tools/
│       └── task_doer_tools.py       # python_code_executer tool
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.com/)** installed and running locally

### 1. Install Ollama and pull the model

```bash
# Start the Ollama server (if not already running)
ollama serve

# Pull the model the agent uses
ollama pull qwen3:8b
```

### 2. Clone and set up the project

```bash
git clone git@github.com:Abolmw4/task-doer-agent.git
cd task-doer-agent

python -m venv .venv
source .venv/bin/activate

pip install langgraph langchain langchain-ollama pydantic
```

### 3. Run the agent

```bash
python main.py
```

The demo task (a human-vs-computer Tic-Tac-Toe game) is hard-coded in `main.py`. When the agent reaches the human decision point, you'll see the generated code in your terminal:

```
Do you approved this code?yes/no:
```

- Type **`yes`** to approve and finish.
- Type anything else to reject — the agent loops back to `write_code` and revises.

### Running your own task

Edit the initial state in `main.py`:

```python
inital_state = TaskDoerAgent(
    code_id="code-101",
    result_code=None,
    task="Your task title",
    description="A detailed description of what you want built",
    prompt=None,
    tester_result=None,
)
```

---

## Configuration

Configuration is currently hard-coded (environment-based config is planned):

| Setting | Location | Current value |
|---|---|---|
| Model | `app/nodes/task_doer_nodes.py` | `qwen3:8b` |
| Ollama URL | `app/nodes/task_doer_nodes.py` | `http://localhost:11434` |
| Demo task | `main.py` | Tic-Tac-Toe game |
| Thread ID | `main.py` | `task-doer-101` |

To use a different model, pull it with Ollama and change the model name in `task_doer_nodes.py`:

```python
OLLAMA_RAW_MODEL = ChatOllama(model="your-model", base_url="http://localhost:11434")
```

---

## ⚠️ Security Notice

The `python_code_executer` tool runs LLM-generated code with `exec()` **on your machine, with no sandboxing**. This is the point of the project — the agent tests its own code — but you should:

- Only run it in a disposable environment (VM, container, or dedicated machine)
- Review the generated code at the human approval step (that's what it's for)
- Never point it at tasks involving credentials, files you care about, or the network

---

## Roadmap

The project is under active development. Planned improvements:

- [ ] Dependency manifest (`requirements.txt` / `pyproject.toml`)
- [ ] Environment-based configuration (`.env` support for model, URL, etc.)
- [ ] CLI arguments for tasks instead of hard-coded values
- [ ] More tools (file I/O, web search, package installation)
- [ ] Persistent checkpointing (SQLite/Postgres instead of in-memory)
- [ ] Sandboxed code execution (Docker / `nsjail`)
- [ ] Test suite

---

## Tech Stack

- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — agent graph, routing, interrupts, checkpointing
- **[LangChain](https://www.langchain.com/)** — tool definitions, structured output
- **[Ollama](https://ollama.com/)** — local model serving (`qwen3:8b`)
- **[Pydantic](https://docs.pydantic.dev/)** — state and schema validation

---

## Contributing

Contributions are welcome! The codebase is small and a good starting point for learning LangGraph. Open an issue or a pull request at [github.com/Abolmw4/task-doer-agent](https://github.com/Abolmw4/task-doer-agent).

---

## License

This project is currently unlicensed. Contact the author before reuse.
