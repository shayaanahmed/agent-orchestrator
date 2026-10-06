# Agent Orchestrator

A local-first project execution system that turns a goal into a validated team plan, runs specialized AI agents, reviews their work, executes safe validation commands, and produces downloadable project artifacts.

This repository is a complete single-tenant deployment for a trusted local network. It does not depend on CrewAI: the stable base is explicit domain models, PostgreSQL, Temporal, and small provider adapters, so the orchestration rules remain under your control.

## What it does

1. Accepts a natural-language objective.
2. Uses a planner model to select the smallest capable team and create a task DAG.
3. Deterministically validates roles, capabilities, task references, and cycles.
4. Executes dependency-ready tasks concurrently through a durable Temporal workflow.
5. Makes agents return structured files, not descriptions of files.
6. Materializes those files into a shared project workspace.
7. Runs allowlisted validation commands in a non-root, resource-limited sandbox container.
8. Sends each result to a separate reviewer model and permits one revision cycle.
9. Stops at an approval gate for deployment-capable work.
10. Publishes individual artifacts and a final `project-workspace.zip` through the API and dashboard.

Project, task, approval, review, artifact, and event state is persisted in PostgreSQL. Temporal provides durable orchestration and retry behavior. Ollama runs on a separate machine; only the model gateway has network egress to it.

## Services

| Service | Purpose |
|---|---|
| `reverse-proxy` | Serves the dashboard and `/api/*` on one port |
| `web` | React project dashboard |
| `api` | Project, approval, event, model, and artifact API |
| `orchestrator-worker` | Temporal worker that plans and executes projects |
| `model-gateway` | Authenticated, OpenAI-compatible proxy to remote Ollama |
| `sandbox-controller` | Isolated Python/Node validation runner with an allowlist |
| `postgres` | Application state and audit history |
| `temporal` / `temporal-postgres` | Durable workflow engine |
| `prometheus` / `grafana` | Metrics collection and inspection |

The application network is Docker-internal. The model gateway alone joins a separate egress network. The sandbox is on its own internal control network and has no database or model-gateway credentials.

## Prerequisites

- Docker Engine with Docker Compose v2
- A reachable Ollama server on another machine in the local network
- The configured Ollama models already pulled on that machine

On the Ollama machine, bind Ollama to an address reachable from the Docker host, protect the network with your firewall, and pull the models selected in `.env`. For example:

```bash
ollama pull qwen3:8b
ollama pull qwen2.5-coder:7b
ollama pull qwen3:4b
```

## Configure and run

From the repository root:

```bash
cp platform/deploy/compose/.env.example platform/deploy/compose/.env
```

Edit `.env` and set at least:

- `OLLAMA_BASE_URL`, including `/v1`, such as `http://192.168.1.50:11434/v1`
- `OLLAMA_API_TOKEN` if the remote endpoint requires one
- strong values for `POSTGRES_PASSWORD`, `MODEL_GATEWAY_TOKEN`, `SANDBOX_TOKEN`, and `GRAFANA_ADMIN_PASSWORD`
- model aliases that exactly match models installed in Ollama

Start everything:

```bash
docker compose -f platform/deploy/compose/docker-compose.yml up --build -d
docker compose -f platform/deploy/compose/docker-compose.yml ps
```

Open:

- Dashboard and API: <http://localhost:8088>
- API documentation: <http://localhost:8088/api/docs>
- Temporal UI: <http://localhost:8080>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3001>

The API bootstraps its idempotent PostgreSQL schema automatically. Named Docker volumes retain application state, Temporal state, workspaces, and monitoring data across restarts.

## Use the API

Create and automatically start a project:

```bash
curl -sS http://localhost:8088/api/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Paper Trading App",
    "goal": "Build a runnable paper-trading web application with risk limits, tests, Docker deployment files, and operator documentation. Do not place real trades."
  }'
```

Inspect it:

```bash
curl -sS http://localhost:8088/api/projects/PROJECT_ID
curl -N http://localhost:8088/api/projects/PROJECT_ID/events/stream
```

When a deployment task reaches an approval gate:

```bash
curl -sS -X POST http://localhost:8088/api/approvals/APPROVAL_ID/approve \
  -H 'Content-Type: application/json' \
  -d '{"comment":"Approved for the local test environment"}'
```

Artifact objects returned by the project endpoint contain an `id`. Download one with:

```bash
curl -OJ http://localhost:8088/api/artifacts/ARTIFACT_ID/download
```

## Lifecycle and recovery

Project states are `created`, `planning`, `validating_plan`, `executing`, `awaiting_approval`, `reviewing`, `completed`, `failed`, `paused`, and `cancelled`. Every important transition is written to `project_events`.

Temporal retries recoverable worker failures. Task completion is persisted before the workflow proceeds, so a restarted worker skips completed work. Approval decisions reset the gated task and signal the existing workflow to continue.

## Sandbox policy

Agent-provided commands are argv arrays rather than shell text. The controller accepts only:

- `python` / `python3` with `-m` or `-c`
- `pytest`
- `node --check` / `node --test`
- `npm test` / `npm run ...`

It rejects parent traversal, sensitive absolute paths, and unapproved executables. The container runs non-root with all Linux capabilities dropped, `no-new-privileges`, a read-only root filesystem, PID/CPU/memory limits, a bounded timeout, capped output, and no connection to the application database/model network. Generated programs may still be untrusted; keep this stack on a trusted host and do not mount host directories or the Docker socket into the sandbox.

## Quality checks

```bash
docker compose -f platform/deploy/compose/docker-compose.yml build
docker run --rm \
  -v "$PWD:/src" -w /src agent-orchestrator-api:latest \
  sh -c 'ruff check platform && ruff format --check platform && mypy --config-file platform/pyproject.toml platform && PYTHONPATH=platform pytest -q platform/tests'
```

Check runtime health:

```bash
curl -sS http://localhost:8088/api/system/health
docker compose -f platform/deploy/compose/docker-compose.yml logs -f api orchestrator-worker model-gateway
```

## Operational scope

This deployment is deliberately single-tenant and local-network oriented. Before exposing it to untrusted users or the public internet, add identity-aware authentication and authorization, TLS termination, per-user quotas, external secret management, backups, and stricter per-execution isolation. Those are deployment controls rather than missing project-execution paths.
