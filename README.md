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

1. **`getting_task`** — Loads long-term memories for the user, decomposes the task into a `TaskPlan` with `TaskDecomposer`, and composes the generation prompt.
2. **`write_code`** — Runs each plan step through a ReAct loop (`python_code_executer`), then calls the LLM with structured output (`ResultCode`) so the model always returns valid JSON containing the code. On retries, the previous test failures (`syntactic_issue`, `logic_issue`) are appended to the prompt so the model can fix its own mistakes.
3. **`test_code`** — The LLM is given the `python_code_executer` tool. It calls the tool to actually execute the generated code, then reviews the output and returns a structured `TesterResult` verdict (pass/fail, syntax issues, logic issues). Failures route back to `write_code` automatically.
4. **`human_decision`** — Uses LangGraph's `interrupt()` to pause the graph and surface the generated code to you in the terminal. Approve it, or reject it with feedback — the agent loops back and revises.
5. **`show_result`** — Prints the final, human-approved code.

---

## Features

- 🤖 **Fully local LLM** — runs on Ollama (`qwen3:8b`), no API keys or cloud costs
- 🔄 **Self-healing code loop (in progress)** — test failures are reported as structured feedback; feeding that feedback back into `write_code` is on the roadmap
- 🛠️ **Real tool calling** — the agent executes the code it writes via `python_code_executer` and reviews the actual runtime output
- 🧑‍⚖️ **Human-in-the-loop approval** — the graph interrupts and waits for your `yes/no` (plus optional feedback) before finishing
- 💾 **Checkpointed state** — in-memory by default, Redis-backed in production; thread IDs make interrupt/resume reliable
- 📐 **Structured output** — Pydantic schemas (`ResultCode`, `TesterResult`) keep model responses machine-readable

---

## Project Structure

```
task-doer-agent/
├── main.py                          # Interactive CLI entry point
├── app/
│   ├── graph.py                     # LangGraph workflow definition + compilation
│   ├── hitl.py                      # Human-in-the-loop approval parsing
│   ├── observability.py             # Phoenix/OpenTelemetry setup
│   ├── nodes/
│   │   └── task_doer_nodes.py       # All 5 node implementations
│   ├── planning/
│   │   ├── decomposer.py            # Task -> TaskPlan decomposition
│   │   └── react.py                 # ReAct loop used by each plan step
│   ├── states/
│   │   └── task_doer_agent_state.py # Pydantic state models
│   └── tools/
│       └── task_doer_tools.py       # python_code_executer tool
├── tests/
│   └── test_workflow.py             # Mocked unit + graph tests
├── phoenix-monitorin/
│   └── docker-compose.yml           # Phoenix + Postgres + Redis
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.com/)** installed and running locally
- **Docker** (optional — only needed for `MODE=production` and Phoenix tracing)

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

pip install -r requirements.txt
```

### 3. Run the agent

```bash
python main.py
```

By default `MODE=development`, so state is kept in memory and **no database is
required**. Copy `.env.example` to `.env` if you want to override the defaults.

The demo task (a human-vs-computer Tic-Tac-Toe game) is hard-coded in `main.py`. When the agent reaches the human decision point, you'll see the generated code in your terminal:

```
Do you approve this code? (yes/no):
```

- Type **`yes`** (or `y`, `true`, `approved`) to approve and finish.
- Type anything else to reject — the agent asks for feedback, loops back to `write_code`, and revises. Empty input and `no`/`false` are always treated as rejection.

### Running your own task

Edit the initial state in `main.py`:

```python
inital_state: TaskDoerAgent = {
    "code_id": "code-101",
    "result_code": None,
    "task": "Your task title",
    "description": "A detailed description of what you want built",
    "prompt": None,
    "tester_result": None,
    "plan": None,
    "current_step": 0,
    "step_results": None,
    "latest_observation": None,
}
```

---

## Configuration

Settings are read from environment variables. A local `.env` file is loaded
automatically (see `.env.example`).

| Variable | Default | Used when | Description |
|---|---|---|---|
| `MODE` | `development` | always | `development` uses in-memory state; `production` uses Redis + Postgres |
| `REDIS_URL` | `redis://localhost:6380` | `MODE=production` | Short-term checkpoint store |
| `LONG_TERM_MEMORY_URL` | `postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable` | `MODE=production` | Long-term memory store |
| `PHOENIX_COLLECTOR_ENDPOINT` | `http://127.0.0.1:6006/v1/traces` | always | OpenTelemetry trace endpoint |

The model and Ollama URL are still hard-coded in `app/nodes/task_doer_nodes.py`:

```python
OLLAMA_RAW_MODEL = ChatOllama(model="qwen3:8b", base_url="http://localhost:11434")
```

### Production mode (Redis + Postgres)

`MODE=production` enables persistent short-term (Redis) and long-term
(Postgres) memory. The bundled compose file starts Phoenix, Postgres, and Redis
on the ports the app expects:

```bash
cd phoenix-monitorin
docker compose up -d
cd ..

MODE=production python main.py
```

> Postgres is exposed on `127.0.0.1:5432` and Redis on `127.0.0.1:6380`.
> Stop any local services on those ports first, or override `REDIS_URL` /
> `LONG_TERM_MEMORY_URL` in `.env`.

### Tests

The test suite is fully mocked and does not need Ollama or any database:

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

---

## ⚠️ Security Notice

The `python_code_executer` tool runs LLM-generated code as a subprocess **on your machine, with no sandboxing**. This is the point of the project — the agent tests its own code — but you should:

- Only run it in a disposable environment (VM, container, or dedicated machine)
- Review the generated code at the human approval step (that's what it's for)
- Never point it at tasks involving credentials, files you care about, or the network

---

## Roadmap

The project is under active development. Planned improvements:

- [x] Dependency manifest (`requirements.txt`)
- [x] Environment-based configuration (`.env` support for mode, database URLs, tracing)
- [ ] CLI arguments for tasks instead of hard-coded values
- [ ] More tools (file I/O, web search, package installation)
- [x] Persistent checkpointing (Redis + Postgres in production mode)
- [ ] Sandboxed code execution (Docker / `nsjail`)
- [x] Test suite (mocked, no external services)
- [ ] Consume tester feedback inside `write_code` so failed reviews actually repair the code

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

MIT — see [LICENSE](LICENSE).
