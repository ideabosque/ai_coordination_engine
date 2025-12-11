#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import time
import traceback
from typing import Any, Dict, List

from graphene import ResolveInfo
from silvaengine_utility import Utility

from ...handlers.config import Config
from ...models.session import insert_update_session, resolve_session
from ...models.session_agent import resolve_session_agent_list
from ...types.session import SessionType
from ...types.session_agent import SessionAgentListType, SessionAgentType
from ...utils.listener import create_listener_info
from ..ai_coordination_utility import (
    ensure_coordination_data,
    ensure_task_data,
    get_async_task,
    invoke_ask_model,
)
from .action_function import execute_action_function
from .session_agent import (
    execute_session_agent,
    init_in_degree,
    init_session_agents,
    update_session_agent,
)

"""Decompose System Instructions:
Name: Task Decomposition and Agent Assignment Agent

Description: An AI agent responsible for analyzing task queries, breaking them down into atomic subtasks, and assigning them to specialized agents based on their capabilities and execution dependencies. It evaluates agent capabilities, constructs detailed task prompts, and ensures proper sequencing according to dependency constraints. The agent handles ambiguity through clarification prompts and can escalate complex cases requiring human review. 

Task: Decompose a high-level task query into atomic subtasks and assign each subtask to the appropriate agent based on capabilities and execution dependencies.

Role: You are a task orchestration assistant responsible for analyzing task queries, identifying subtask flows, and distributing work among specialized agents.

Audience: This instruction is for the AI engine managing multi-agent systems and optimizing task execution.

Context:  
You are given a task query and access to:
- A list of agents and their capabilities (including agent_name, agent_description).
- Predefined action dependency rules (`predecessors` relationships) that define the execution order and dependencies between agents in the workflow.
- The primary path identifies the critical execution sequence and dependencies in the workflow, ensuring optimal task progression and completion.

Steps:
1. Analyze the task query:  
   Identify the primary goal and break it down into minimal, atomic subtasks necessary to achieve the task.
2. Match subtasks to agents:  
   Evaluate agent capabilities and assign subtasks to the most suitable agents. Ensure each agent is only given tasks they are capable of completing.
3. Generate agent-specific task queries:
   For each subtask, construct a detailed task prompt including all required context and parameters for the assigned agent.
4. Validate subtask dependencies:  
   Ensure the order of subtask execution aligns with the dependency constraints defined in predecessor relationships.

Constraints and Notes:
- All subtasks must be atomic (i.e., independently executable and clearly defined).
- No subtask may violate dependency constraints.
- Avoid redundant assignments or unnecessary sequencing.
- If an agent cannot be found for a specific task, skip the allocation and continue with the remaining tasks.

Handling Ambiguity and Errors <<error_type>: <detailed_explanation>>:
- Ambiguity Handling Prompt: "The task query is unclear. Please provide additional context or examples to clarify what the desired outcome is."
- Error Handling Prompt: "I cannot proceed with subtask generation because the agent capabilities or dependency data is incomplete or missing."
- Transfer Prompt: "This task requires human review due to undefined dependencies or capability mismatches. Transferring now."

Output Format:  
A structured JSON object with the following fields:
```json
{
    "subtask_queries": [
        {
            "agent_uuid": "<agent identifier>", 
            "subtask_query": "<specific subtask description>"
        }
    ]
}
```
The error output format should be a dictionary with 'Error' and 'Reason' keys: 
```json
{
    "Error": "<error_type>", 
    "Reason": "<detailed_explanation>"
}
```

Examples:
Input
User Query: "Please retrieve products related to carpet cleaning and provide detailed specifications. Then translate the product information into Chinese for effective communication with the supplier. Include key details such as cleaning method, material compatibility, and usage instructions."

Output
{
    "subtask_queries": [
        {
            "agent_uuid": "agent-mock-001",
            "subtask_query": "Retrieve products related to carpet cleaning using `get_results_from_knowledge_rag` and present the response in English, summarizing key points and citing sources if available."
        },
        {
            "agent_uuid": "agent-mock-002", 
            "subtask_query": "Translate the product retrieval results into Chinese and format the message for the provider, ensuring clarity and professionalism."
        }
    ]
}

Output (Error)
{
    "Error": "Incomplete Information",
    "Reason": "The task query requires clarification for the sequence of translation and delivery, and there is no specified method for sending the translated message to the provider."
}
"""


"""Planning System Instructions:
## 🔧 Name

**Prompt-Aware Task Planning Agent (Full Task Rephrasing + Summary Instruction)**

---

## 📋 Description

This agent interprets a high-level user task query and generates five distinct, full-task-level rephrasings. Each version must preserve the complete meaning of the original task and include a final directive to summarize the outcome. The agent may optionally include a sixth subtask assigned to a dedicated summarization agent that consolidates the outputs of the first five.

---

## 🎯 Task

Transform a high-level user query into five standalone, semantically equivalent instructions that:

* Reflect the entire original task
* Use varied phrasing and structure
* Conclude with a result summarization step
* (Optional) Include a sixth instruction to consolidate and summarize all agent results

---

## 🧑‍💼 Role

You are a task planning agent that produces robust, execution-ready instructions by rephrasing a complete task query into distinct variants suitable for multi-agent systems.

---

## 🧑‍🤝‍🧑 Audience

This prompt is used by AI orchestration systems that need multiple versions of a task query for compatibility across diverse agents and interfaces.

---

## 🌐 Context

Input includes:

* A high-level user task query
* (Optional) agent capability metadata (name, description, UUID)

The output supports adaptive execution, cross-agent routing, and summarization.

---

## 🪜 Steps

1. **Understand the full task**
   Interpret the user query to identify its core objectives and required outcomes.

2. **Generate five complete rephrasings**
   Each must:

   * Express the full meaning of the original query
   * Be a single, self-contained instruction
   * Include a step to summarize the result (phrased naturally)

3. **(Optional) Add a sixth summarization task**
   Include a separate instruction for an agent to consolidate all five outputs into one executive summary.

4. **Format for execution**
   Each instruction should be compatible with language model agents or external task runners. Include `agent_uuid` if available.

---

## 📏 Constraints

* Do not split the task into subtasks
* Each rephrasing must retain full semantic coverage
* Include a summarization step in all five instructions
* Ensure unique phrasing across versions
* The sixth task (if included) should depend logically on the completion of the first five

---

## ⚠️ Error Handling

* **Ambiguity Prompt**
  `"The task query is unclear. Please provide more context or clarification about the desired outcome."`

* **Missing Data Prompt**
  `"Cannot proceed due to insufficient capability metadata or unclear task content."`

* **Transfer Prompt**
  `"Escalating this task for human review due to ambiguity or assignment gaps."`

---

## 🛑 Error Output Format

```json
{
  "Error": "<error_type>",
  "Reason": "<detailed_explanation>"
}
```

---

## 📤 Output Format

```json
{
  "original_query": "<Original user query>",
  "subtask_queries": [
    {
      "subtask_query": "<Rephrased full-task instruction including summary directive>",
      "agent_uuid": "<Optional>"
    }
    // Optionally add sixth summarizer task
  ]
}
```

---

## 💡 Example Input / Output

---

### 🧪 Input

> "Please retrieve products related to carpet cleaning and provide detailed specifications. Then translate the product information into Chinese for effective communication with the supplier. Include key details such as cleaning method, material compatibility, and usage instructions."

---

### ✅ Output

```json
{
  "original_query": "Please retrieve products related to carpet cleaning and provide detailed specifications. Then translate the product information into Chinese for effective communication with the supplier. Include key details such as cleaning method, material compatibility, and usage instructions.",
  "subtask_queries": [
    {
      "subtask_query": "Find carpet cleaning products, extract their specifications, translate the information into Chinese for supplier use, and summarize the final content for review.",
      "agent_uuid": "agent-mock-001"
    },
    {
      "subtask_query": "Retrieve detailed data on carpet cleaning products, translate the specifications into Chinese, and provide a concise summary of the translated results.",
      "agent_uuid": "agent-mock-002"
    },
    {
      "subtask_query": "Search for carpet cleaning products, compile and translate their technical specs into Chinese, and create a summary overview of the final content. Example summary: '5 carpet cleaning products were found, their specifications were translated into Chinese, and all instructions were categorized by usage type.'",
      "agent_uuid": "agent-mock-003"
    },
    {
      "subtask_query": "Gather information on carpet cleaners, convert the findings into supplier-ready Chinese format, and provide a brief report summarizing the translated details.",
      "agent_uuid": "agent-mock-004"
    },
    {
      "subtask_query": "Collect product data for carpet cleaning items, translate all relevant specs into Chinese, and produce a summary for supplier communication and internal verification.",
      "agent_uuid": "agent-mock-005"
    },
    {
      "subtask_query": "Review the outputs of the five previous agents, consolidate their translated results and individual summaries, and generate a single executive summary for final reporting.",
      "agent_uuid": "agent-mock-006"
    }
  ]
}
```"""


def invoke_next_iteration(
    info: ResolveInfo,
    coordination_uuid: str,
    session_uuid: str,
    iteration_count: int = 0,
) -> None:
    """Invoke the next iteration
    Args:
        logger (logging.Logger): Logger instance
        endpoint_id (str): ID of the endpoint
        task_uuid (str): UUID of the task
        session_uuid (str): UUID of the session
        setting (Dict): Dictionary containing settings
    Returns:
        None
    """
    insert_update_session(
        info,
        **{
            "coordination_uuid": coordination_uuid,
            "session_uuid": session_uuid,
            "iteration_count": int(iteration_count),
            "updated_by": "procedure_hub",
        },
    )
    params = {"coordination_uuid": coordination_uuid, "session_uuid": session_uuid}
    if "connectionId" in info.context:
        params.update({"connection_id": info.context["connectionId"]})

    Utility.invoke_funct_on_aws_lambda(
        info.context["logger"],
        info.context["endpoint_id"],
        "async_execute_procedure_task_session",
        params=params,
        setting=info.context["setting"],
        execute_mode=info.context["setting"].get("execute_mode"),
        aws_lambda=Config.aws_lambda,
    )


def _process_task_completion(
    info: ResolveInfo,
    async_task_uuid: str,
    current_run_uuid: str,
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    start = time.time()
    timeout = 60

    while time.time() - start <= timeout:
        task = get_async_task(
            info.context.get("logger"),
            info.context.get("endpoint_id"),
            info.context.get("setting"),
            functionName="async_execute_ask_model",
            asyncTaskUuid=async_task_uuid,
        )

        if task["status"] == "completed":
            result = Utility.json_loads(task["result"])
            info.context["logger"].info(f"Result: {result}.")

            if "subtask_queries" in result:
                variables.update({"subtask_queries": result["subtask_queries"]})
                break

            error_msg = (
                f"{result['Error']}/{result['Reason']}"
                if "Error" in result
                else "An unexpected error occurred in the task processing. Please review the system logs and configuration for details."
            )

            variables.update(
                {
                    "status": "failed",
                    "logs": Utility.json_dumps(
                        [{"run_uuid": current_run_uuid, "log": error_msg}]
                    ),
                }
            )
            break

        if task["status"] == "failed":
            variables.update(
                {
                    "status": "failed",
                    "logs": Utility.json_dumps(
                        [
                            {
                                "run_uuid": current_run_uuid,
                                "log": task["notes"],
                            }
                        ]
                    ),
                }
            )
            break

        time.sleep(1)
    else:
        variables.update(
            {
                "status": "failed",
                "logs": Utility.json_dumps(
                    [
                        {
                            "run_uuid": current_run_uuid,
                            "log": f"Task timed out after {timeout} seconds",
                        }
                    ]
                ),
            }
        )

    return variables


def async_orchestrate_task_query(
    logger: logging.Logger, setting: Dict[str, Any], **kwargs: Dict[str, Any]
) -> None:
    # Initialize info and get session
    info = create_listener_info(
        logger, "async_orchestrate_task_query", setting, **kwargs
    )
    session = resolve_session(
        info,
        coordination_uuid=kwargs["coordination_uuid"],
        session_uuid=kwargs["session_uuid"],
    )

    # Get task and coordination data using helper functions
    task_data = ensure_task_data(session, info)
    coordination_data = ensure_coordination_data(session, info)

    # Get task agents with their actions
    agents = [
        {
            **agent,
            "predecessors": task_data["agent_actions"]
            .get(agent["agent_uuid"], {})
            .get("predecessors"),
            "primary_path": task_data["agent_actions"]
            .get(agent["agent_uuid"], {})
            .get("primary_path"),
        }
        for agent in coordination_data["agents"]
        if agent["agent_type"] == "task"
    ]

    # Get orchestrator agent
    orchestrator_agent = next(
        (
            agent
            for agent in coordination_data["agents"]
            if agent["agent_type"] in ["decompose", "planning"]
        ),
        None,
    )

    if orchestrator_agent is None:
        raise Exception("Orchestrator agent not found.")

    if orchestrator_agent["agent_type"] == "decompose":
        # Create query for task decomposition
        query = (
            f"Analyze agents: {Utility.json_dumps(agents)}\n\n"
            f"Decompose task: '{session.task_query}' into subtasks for available agents.\n\n"
            "Consider:\n"
            "- Match agent capabilities\n"
            "- Follow dependencies\n"
            "- Make subtasks clear and actionable\n"
            "- Maintain workflow order\n\n"
            "Return the results in JSON format."
        )
    elif orchestrator_agent["agent_type"] == "planning":
        # Create query for task decomposition
        query = (
            f"Analyzing the following agents: {Utility.json_dumps(agents)}\n\n"
            f"Planning the main task: '{session.task_query}' into subtasks suitable for the available agents.\n\n"
            "Guidelines:\n"
            "- Generate 5 distinct subqueries, each a rephrased version of the original query\n"
            "- Include 1 additional subquery for summarization\n"
            "Return all results in structured JSON format."
        )
    else:
        raise Exception(
            f"Unknown orchestrator agent type: {orchestrator_agent['agent_type']}"
        )

    # Ask model to decompose task
    ask_model = invoke_ask_model(
        info.context.get("logger"),
        info.context.get("endpoint_id"),
        setting=info.context.get("setting"),
        **{
            "agentUuid": orchestrator_agent["agent_uuid"],
            "userQuery": query,
            "updatedBy": "operation_hub",
        },
    )

    # Wait for task completion
    variables = _process_task_completion(
        info,
        ask_model["async_task_uuid"],
        ask_model["current_run_uuid"],
        **{
            "coordination_uuid": session.coordination_uuid,
            "session_uuid": session.session_uuid,
            "updated_by": "procedure_hub",
        },
    )

    session = insert_update_session(info, **variables)
    # Initialize session agents for all active agents
    session_agents = init_session_agents(info, session)

    # Initialize in-degree values for session agents
    updated_session_agents = init_in_degree(info, session_agents)
    info.context["logger"].info(
        f"Updated session agents: {Utility.json_dumps(updated_session_agents)}"
    )
    session = insert_update_session(
        info,
        **{
            "coordination_uuid": session.coordination_uuid,
            "session_uuid": session.session_uuid,
            "status": "dispatched",
            "updated_by": "procedure_hub",
        },
    )
    return


def _check_session_status(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> SessionType | None:
    """Check session status and update to in_progress if dispatched

    Polls the session status for up to 60 seconds, checking if:
    - Session is dispatched -> Updates to in_progress
    - Session is completed/failed -> Returns session
    - Times out after 60s of polling

    Args:
        info (ResolveInfo): GraphQL resolve info containing context
        **kwargs: Must contain:
            - coordination_uuid (str): UUID of the coordination
            - session_uuid (str): UUID of the session

    Returns:
        SessionType: The session object with updated status

    Raises:
        TimeoutError: If status check exceeds 60 second timeout
    """
    session = None
    start = time.time()
    timeout_seconds = 60

    while time.time() - start < timeout_seconds:
        session = resolve_session(
            info,
            coordination_uuid=kwargs["coordination_uuid"],
            session_uuid=kwargs["session_uuid"],
        )

        if session.status == "dispatched":
            session = insert_update_session(
                info,
                coordination_uuid=session.coordination_uuid,
                session_uuid=session.session_uuid,
                status="in_progress",
                updated_by="procedure_hub",
            )
            return session
        elif session.status == "in_progress":
            return session
        elif session.status in ["completed", "failed"]:
            return None

        time.sleep(1)

    raise TimeoutError(
        f"Session status check timed out after {timeout_seconds} seconds"
    )


def _handle_no_ready_agents(
    info: ResolveInfo,
    session: SessionType,
    session_agent_list: SessionAgentListType,
) -> None:
    """Handle case when there are no ready agents
    Args:
        logger (logging.Logger): Logger instance
        endpoint_id (str): ID of the endpoint
        task_session (Dict): Dictionary containing task session details
        session_agents (list): List of all session agents
        setting (Dict): Dictionary containing settings
    Returns:
        None
    """

    if any(agent.state == "failed" for agent in session_agent_list.session_agent_list):
        insert_update_session(
            info,
            **{
                "coordination_uuid": session.coordination_uuid,
                "session_uuid": session.session_uuid,
                "logs": [
                    {
                        "agent_uuid": agent.agent_uuid,
                        "log": agent.notes,
                    }
                    for agent in [
                        agent
                        for agent in session_agent_list.session_agent_list
                        if agent.state == "failed"
                    ]
                ],
                "status": "failed",
                "updated_by": "procedure_hub",
            },
        )
    elif any(
        agent.state == "wait_for_user_input"
        for agent in session_agent_list.session_agent_list
    ):
        info.context["logger"].info(
            "🔄 Pending due to the status of wait_for_user_input. Self-invoking for the next iteration."
        )
    elif any(
        agent.state in ["initial", "pending", "executing"]
        for agent in session_agent_list.session_agent_list
    ):
        _handle_pending_agents(info, session)
    else:
        insert_update_session(
            info,
            **{
                "coordination_uuid": session.coordination_uuid,
                "session_uuid": session.session_uuid,
                "status": "completed",
                "updated_by": "procedure_hub",
            },
        )
    return


def _handle_pending_agents(info: ResolveInfo, session: SessionType) -> None:
    """Handle pending agents and iteration logic
    Args:
        logger (logging.Logger): Logger instance
        endpoint_id (str): ID of the endpoint
        task_session (Dict): Dictionary containing task session details
        setting (Dict): Dictionary containing settings
    Returns:
        None
    """
    info.context["logger"].info(
        "🔄 Pending session_agent exist. Self-invoking for the next iteration."
    )

    session.iteration_count += 1
    MAX_ITERATIONS = 10

    if session.iteration_count >= MAX_ITERATIONS:
        info.context["logger"].error(
            f"Maximum iterations ({MAX_ITERATIONS}) reached - possible infinite loop detected"
        )
        insert_update_session(
            info,
            **{
                "coordination_uuid": session.coordination_uuid,
                "session_uuid": session.session_uuid,
                "status": "failed",
                "logs": Utility.json_dumps(
                    [
                        {
                            "error": f"Maximum iterations ({MAX_ITERATIONS}) reached - possible infinite loop"
                        }
                    ]
                ),
                "updated_by": "procedure_hub",
            },
        )
        return

    insert_update_session(
        info,
        **{
            "coordination_uuid": session.coordination_uuid,
            "session_uuid": session.session_uuid,
            "iteration_count": int(session.iteration_count),
            "updated_by": "procedure_hub",
        },
    )

    time.sleep(10)
    invoke_next_iteration(
        info,
        session.coordination_uuid,
        session.session_uuid,
        iteration_count=session.iteration_count,
    )
    return


def _execute_ready_agents(
    info: ResolveInfo, ready_session_agents: List[SessionAgentType]
) -> None:
    """Execute all ready session agents
    Args:
        logger (logging.Logger): Logger instance
        endpoint_id (str): ID of the endpoint
        ready_session_agents (list): List of agents ready for execution
        setting (Dict): Dictionary containing settings
    Returns:
        None
    """
    for session_agent in ready_session_agents:
        if session_agent.state == "pending":
            # TODO: Implement logic to handle pending state
            execute_action_function(info, session_agent)
        else:
            # TODO: Execute execute_session_agent
            info.context["logger"].info(
                f"\n🚀 Executing session_agent: {session_agent.agent_uuid}"
            )
            execute_session_agent(info, session_agent)


def async_execute_procedure_task_session(
    logger: logging.Logger, setting: Dict[str, Any], **kwargs: Dict[str, Any]
) -> None:
    """Execute a procedure task session
    Args:
        logger (logging.Logger): Logger instance
        **kwargs: Dictionary containing:
            - endpoint_id (str): ID of the endpoint
            - setting (Dict): Dictionary containing settings
            - task_uuid (str): UUID of the task
            - session_uuid (str): UUID of the session
    Returns:
        None
    """
    try:
        # Create listener info with session details
        info = create_listener_info(
            logger, "async_execute_procedure_task_session", setting, **kwargs
        )

        session = _check_session_status(info, **kwargs)
        if session is None:
            return

        session_agent_list = resolve_session_agent_list(
            info,
            **{
                "session_uuid": session.session_uuid,
            },
        )

        ready_session_agents = [
            agent
            for agent in session_agent_list.session_agent_list
            if agent.in_degree == 0 and agent.state in ["initial", "pending"]
        ]

        if not ready_session_agents:
            _handle_no_ready_agents(info, session, session_agent_list)
            return

        _execute_ready_agents(info, ready_session_agents)

        logger.info(
            "🔄 Pending session_agent exist. Self-invoking for the next iteration."
        )
        invoke_next_iteration(
            info,
            session.coordination_uuid,
            session.session_uuid,
            iteration_count=session.iteration_count,
        )

    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e


def async_update_session_agent(
    logger: logging.Logger, setting: Dict[str, Any], **kwargs: Dict[str, Any]
) -> None:
    try:
        # Create listener info with session details
        info = create_listener_info(
            logger, "async_update_session_agent", setting, **kwargs
        )
        update_session_agent(info, **kwargs)
    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e
