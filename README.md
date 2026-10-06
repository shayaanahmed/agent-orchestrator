# AI Project Execution Platform

A production-oriented, local-first AI platform that transforms human objectives into verified project deliverables through dynamically assembled teams of specialized AI agents.

## Overview

This platform provides a complete system for:
- Converting natural language goals into structured project plans
- Dynamically assembling agent teams with appropriate capabilities  
- Executing projects through orchestrated workflows with proper coordination
- Safely generating and reviewing executable code artifacts
- Managing complex project lifecycles with observability and recovery

## Architecture

### Core Components

```
platform/
├── core/                    # Domain models and business logic
│   ├── domain/             # Core entities and value objects
│   ├── interfaces/         # Contracts for external dependencies
│   └── policies/           # Business rules and constraints
├── application/            # Application services that coordinate domain logic
│   ├── commands/           # Write operations  
│   ├── queries/            # Read operations
│   └── services/           # Business logic services
├── adapters/               # Implementation of interfaces
│   ├── database/           # Data persistence
│   ├── artifacts/          # Artifact storage
│   ├── inference/          # Model provider integration
│   ├── workflows/          # Temporal workflow coordination  
│   └── sandbox/            # Containerized execution environment
├── services/               # Independent platform services
│   ├── api/                # HTTP API endpoints (FastAPI)
│   ├── model_gateway/      # Model provider abstraction layer
│   ├── orchestrator_worker/
│   ├── agent_worker/
│   ├── review_worker/
│   └── sandbox_controller/
├── web/                    # User interface (React/Next.js)
├── deploy/                 # Deployment configurations
│   ├── compose/            # Docker Compose deployments
│   └── monitoring/         # Observability setup
└── tests/                  # Test suite
```

### Technology Stack

- **Backend**: Python, FastAPI, Pydantic
- **Database**: PostgreSQL with SQLAlchemy 2.x
- **Workflow**: Temporal Python SDK
- **Storage**: MinIO (S3-compatible)
- **Inference**: Ollama through model gateway
- **Frontend**: React / Next.js
- **Orchestration**: Docker Compose
- **Observability**: OpenTelemetry, Prometheus, Grafana

## Key Features

### 1. Dynamic Team Formation
- Catalog of agent capabilities and roles
- Automatic assignment of tasks to qualified agents
- Support for multiple agent types (planner, coder, reviewer)

### 2. Project Lifecycle Management  
- Clear lifecycle states (created, clarifying, planning, executing, reviewing)
- Proper state transitions with validation
- Approval gates for critical actions

### 3. Artifact Management
- Structured artifact storage in MinIO
- Metadata persistence in PostgreSQL
- Artifact auditing and version control

### 4. Safety & Security
- Containerized sandbox execution 
- Tool permission systems
- Input sanitization and size limits
- Secret redaction in logs

### 5. Observability
- Full audit trails for all project activities
- Metrics collection via OpenTelemetry
- Monitoring with Prometheus and Grafana 

## Implementation Status

This implementation covers:

✅ Core domain models and abstractions  
✅ API service with FastAPI  
✅ Database schema design with PostgreSQL  
✅ Model provider abstraction (Ollama integration)  
✅ Project workflow orchestration structure  
✅ Artifact storage abstraction  
✅ Docker Compose deployment configuration  

## Getting Started

### Prerequisites
1. Docker and Docker Compose installed
2. Ollama instance running on local network (not part of Docker stack)
3. Environment configured with proper secrets (refer to .env.example)

### Configuration
1. Create a `.env` file based on `.env.example`
2. Set up the reverse proxy to Ollama (in production environment)
3. Configure model aliases in the model gateway

### Running the System

```bash
# Build and start services
docker-compose up --build

# Run database migrations  
docker-compose exec postgres alembic upgrade head

# Run tests
docker-compose run api python -m pytest tests/
```

## Development Guidelines  

### Design Philosophy
The system follows a clean/hexagonal architecture with clear separation of concerns:

1. **Domain Layer**: Pure business logic without external dependencies
2. **Application Layer**: Coordination between domain and adapters  
3. **Adapters Layer**: External integrations (database, storage, models)

### Testing Strategy

- Unit tests for pure domain logic
- Integration tests for adapter interactions  
- End-to-end workflow testing
- Mocked model responses during development

### Security Considerations

- All external communication goes through defined interfaces  
- Containerized sandbox execution prevents unauthorized access
- Secrets are never exposed in logs or prompts
- Input validation at all boundaries

## Roadmap

1. **Complete the Temporal workflow implementation**
2. **Implement agent worker and review worker services**  
3. **Finish sandbox controller with containerization support**
4. **Build comprehensive UI/UX for project management**
5. **Add advanced planning capabilities**
6. **Implement full approval and revision workflows**
7. **Add comprehensive monitoring and alerting**

## Usage Examples  

```bash
# Create a new project
curl -X POST "http://localhost:8000/projects" -H "Content-Type: application/json" \
  -d '{"goal_text": "Build a paper-trading application", "name": "Paper Trading App"}'

# Clarify requirements interactively  
curl -X POST "http://localhost:8000/projects/{project_id}/clarify" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Include support for multiple exchanges"}'
```

---

For more information about any specific component, see the respective directories and files in this repo.