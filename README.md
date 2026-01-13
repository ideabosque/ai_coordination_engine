# AI Coordination Engine

The **AI Coordination Engine** is a modular system designed to orchestrate complex interactions between multiple AI agents, tasks, and sessions. It provides a robust framework for managing the lifecycle of AI-driven workflows, from defining coordination strategies to executing and tracking individual agent actions.

## Architecture Overview

The engine is built around the concept of **Coordinations**, which define the blueprint for how agents interact. **Sessions** are specific instances of these coordinations, where **Tasks** are executed. The system tracks the state of each agent within a session via **SessionAgents** and records every execution step in **SessionRuns**.

### High-Level Architecture

```mermaid
graph TD
    subgraph "Configuration"
        C[Coordination] -->|Defines| T[Task]
        T -->|Scheduled via| TS[Task Schedule]
    end

    subgraph "Execution"
        C -->|Instantiates| S[Session]
        S -->|Tracks State| SA[Session Agent]
        S -->|Records Execution| SR[Session Run]
        SA -.->|Updates| SR
    end

    subgraph "Actors"
        A[Agent]
        U[User]
    end

    C -.->|Configures| A
    S -.->|Interacts with| U
```

## Data Model Architecture

The core data models are designed to support scalable and traceable AI orchestration. The relationships between these models ensure that every action is linked back to its originating session and coordination context.

### Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    CoordinationModel ||--o{ TaskModel : "has"
    CoordinationModel ||--o{ SessionModel : "instantiates"
    
    TaskModel ||--o{ TaskScheduleModel : "scheduled by"
    
    SessionModel ||--o{ SessionAgentModel : "tracks agent state"
    SessionModel ||--o{ SessionRunModel : "executes"
    
    SessionAgentModel }o--|| CoordinationModel : "references agent in"
    SessionRunModel }o--|| SessionAgentModel : "associated with"
    SessionRunModel }o--|| CoordinationModel : "references"

    CoordinationModel {
        string partition_key PK
        string coordination_uuid PK
        string endpoint_id
        string part_id
        string coordination_name
        string coordination_description
        list agents
    }

    TaskModel {
        string coordination_uuid PK
        string task_uuid PK
        string partition_key
        string task_name
        string task_description
        string initial_task_query
        list subtask_queries
        map agent_actions
    }

    TaskScheduleModel {
        string task_uuid PK
        string schedule_uuid PK
        string coordination_uuid
        string partition_key
        string schedule
        string status
    }

    SessionModel {
        string coordination_uuid PK
        string session_uuid PK
        string partition_key
        string task_uuid
        string user_id
        string task_query
        string status
        int iteration_count
        list input_files
        list subtask_queries
        string logs
    }

    SessionAgentModel {
        string session_uuid PK
        string session_agent_uuid PK
        string coordination_uuid
        string agent_uuid
        map agent_action
        string user_input
        string agent_input
        string agent_output
        int in_degree
        string state
        string notes
    }

    SessionRunModel {
        string session_uuid PK
        string run_uuid PK
        string partition_key
        string thread_uuid
        string agent_uuid
        string coordination_uuid
        string async_task_uuid
        string session_agent_uuid
    }
```

### 🔗 **Relationship Patterns**

#### **1. Orchestration Hierarchy** (Primary Workflow)

```
┌─────────────────────────────────────────────────────────────┐
│                  ORCHESTRATION HIERARCHY                     │
└─────────────────────────────────────────────────────────────┘

Coordination (Blueprint)
  │
  ├──> Task (1:N) ──> TaskSchedule (1:N)
  │
  └──> Session (1:N) ──┬──> SessionAgent (1:N) ──> Agent (Logical Reference)
                       │
                       └──> SessionRun (1:N) ──> Thread (Logical Reference)
```

**Cascade Delete Protection:**
- Cannot delete Coordination if Sessions or Tasks exist
- Cannot delete Session if SessionAgents or SessionRuns exist
- Cannot delete Task if TaskSchedules exist

**Key Fields:**
- Task references Coordination via: `coordination_uuid`
- Session references Coordination via: `coordination_uuid`
- SessionAgent references Session via: `session_uuid`
- SessionRun references Session via: `session_uuid`

---

#### **2. Execution State Tracking**

```
┌─────────────────────────────────────────────────────────────┐
│                  EXECUTION STATE TRACKING                    │
└─────────────────────────────────────────────────────────────┘

Session (Context Holder)
  │
  ├──> SessionAgent (1:N)
  │       │
  │       ├──> State (e.g., "initial", "in_progress")
  │       └──> In-Degree (Dependency Tracking)
  │
  └──> SessionRun (1:N)
          │
          ├──> Thread UUID (Conversation History)
          └──> Async Task UUID (Long-running Operations)
```

**Reference Patterns:**
- SessionAgent tracks the state of a specific `agent_uuid` within the Session.
- SessionRun records an immutable execution step, linking `run_uuid` to `thread_uuid`.
- Async operations are tracked via `async_task_uuid` on the SessionRun.
