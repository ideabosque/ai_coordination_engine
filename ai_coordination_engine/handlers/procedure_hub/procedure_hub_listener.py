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
from ..ai_coordination_utility import (
    create_listener_info,
    get_async_task,
    invoke_ask_model,
)
from .action_rules import execute_action_rules
from .session_agent import (
    execute_session_agent,
    init_in_degree,
    init_session_agents,
    update_session_agent,
)

"""System Instructions:
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

    Utility.invoke_funct_on_aws_lambda(
        info.context["logger"],
        info.context["endpoint_id"],
        "async_execute_procedure_task_session",
        params={"coordination_uuid": coordination_uuid, "session_uuid": session_uuid},
        setting=info.context["setting"],
        test_mode=info.context["setting"].get("test_mode"),
        aws_lambda=Config.aws_lambda,
    )


def _process_task_completion(
    info: ResolveInfo, ask_model: Dict[str, Any], **variables: Dict[str, Any]
) -> None:
    start = time.time()
    timeout = 60

    while time.time() - start <= timeout:
        task = get_async_task(
            info.context.get("logger"),
            info.context.get("endpoint_id"),
            info.context.get("setting"),
            functionName="async_execute_ask_model",
            asyncTaskUuid=ask_model["async_task_uuid"],
        )

        if task["status"] == "completed":
            result = Utility.json_loads(task["result"])
            info.context["logger"].info(f"Result: {result}.")

            if "subtask_queries" in result:
                variables["subtask_queries"] = result["subtask_queries"]
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
                        [{"run_uuid": ask_model["current_run_uuid"], "log": error_msg}]
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
                                "run_uuid": ask_model["current_run_uuid"],
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
                            "run_uuid": ask_model["current_run_uuid"],
                            "log": f"Task timed out after {timeout} seconds",
                        }
                    ]
                ),
            }
        )

    return variables


def async_decompose_task_query(
    logger: logging.Logger, setting: Dict[str, Any], **kwargs: Dict[str, Any]
) -> None:
    # Initialize info and get session
    info = create_listener_info(logger, "async_decompose_task_query", setting, **kwargs)
    session = resolve_session(
        info,
        coordination_uuid=kwargs["coordination_uuid"],
        session_uuid=kwargs["session_uuid"],
    )

    # Get decompose agent
    decompose_agent = next(
        (
            agent
            for agent in session.coordination["agents"]
            if agent["agent_type"] == "decompose"
        ),
        None,
    )

    # Get task agents with their actions
    agents = [
        {
            **agent,
            "predecessors": session.task["agent_actions"]
            .get(agent["agent_uuid"], {})
            .get("predecessors"),
            "primary_path": session.task["agent_actions"]
            .get(agent["agent_uuid"], {})
            .get("primary_path"),
        }
        for agent in session.coordination["agents"]
        if agent["agent_type"] == "task"
    ]

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

    # Ask model to decompose task
    ask_model = invoke_ask_model(
        info.context.get("logger"),
        info.context.get("endpoint_id"),
        setting=info.context.get("setting"),
        agentUuid=decompose_agent["agent_uuid"],
        userQuery=query,
        updatedBy="operation_hub",
    )

    # Wait for task completion
    variables = _process_task_completion(
        info,
        ask_model,
        **{
            "coordination_uuid": session.coordination["coordination_uuid"],
            "session_uuid": session.session_uuid,
            "status": "dispatched",
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
    return


def _check_session_status(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionType:
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
                coordination_uuid=session.task["coordination"]["coordination_uuid"],
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
                "coordination_uuid": session.task["coordination_uuid"],
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
    if any(
        agent.state == "wait_for_user_input"
        for agent in session_agent_list.session_agent_list
    ):
        info.context["logger"].info(
            "🔄 Pending due to the status of wait_for_user_input. Self-invoking for the next iteration."
        )
        return

    if any(
        agent.state in ["initial", "pending", "executing"]
        for agent in session_agent_list.session_agent_list
    ):
        _handle_pending_agents(info, session)

    insert_update_session(
        info,
        **{
            "coordination_uuid": session.task["coordination"]["coordination_uuid"],
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
    MAX_ITERATIONS = 5

    if session.iteration_count >= MAX_ITERATIONS:
        info.context["logger"].error(
            f"Maximum iterations ({MAX_ITERATIONS}) reached - possible infinite loop detected"
        )
        insert_update_session(
            info,
            **{
                "coordination_uuid": session.task["coordination"]["coordination_uuid"],
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
            "coordination_uuid": session.task["coordination"]["coordination_uuid"],
            "session_uuid": session.session_uuid,
            "iteration_count": int(session.iteration_count),
            "updated_by": "procedure_hub",
        },
    )

    time.sleep(10)
    invoke_next_iteration(
        info,
        session.task["coordination"]["coordination_uuid"],
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
            execute_action_rules(info, session_agent)
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
            session.task["coordination"]["coordination_uuid"],
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
