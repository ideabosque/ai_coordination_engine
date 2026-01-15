#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict, Optional

from graphene import ResolveInfo
from silvaengine_utility.debugger import Debugger
from silvaengine_utility.invoker import Invoker
from silvaengine_utility.serializer import Serializer

from ...models.coordination import resolve_coordination
from ...models.session import insert_update_session
from ...models.session_run import insert_update_session_run
from ...types.coordination import CoordinationType
from ...types.operation_hub import AskOperationHubType
from ...types.session import SessionType
from ...types.session_run import SessionRunType
from ..ai_coordination_utility import get_connection_by_email, invoke_ask_model
from ..config import Config

"""System Instructions:
Name: Triage Agent

Description: Triage user queries by identifying and assigning the most suitable agent based on available agent profiles.

Task: Triage user queries by identifying and assigning the most suitable agent based on available agent profiles.

Role: You are a triage assistant responsible for analyzing user queries and determining the best-fit agent by evaluating each agent's expertise and description. Your goal is to ensure the query is routed to the most appropriate agent, or report if no match is found.

Steps:
1. Review Agent Profiles: Examine each agent's `agent_name` and `agent_description`.
2. Match Against User Query: Compare the user’s query with each agent’s profile to identify the best match.
3. Respond with Assignment Status:
   - If a relevant agent is found:
     ```json
     {
       "status": "assigned",
       "agent_uuid": "<Agent UUID of the matched agent>"
     }
     ```
   - If no relevant agent is found:
     ```json
     {
       "status": "unassigned",
       "message": "No matching agent could be found based on the provided query and agent descriptions."
     }
     ```

Handling Ambiguity and Errors:
- If agent data is unavailable or cannot be retrieved, respond with:
  ```json
  {
    "status": "error",
    "message": "Unable to retrieve agent data. Please verify the input and try again."
  }
  ```

Output Format:
All responses must use the JSON structure shown above for each scenario.

Examples:
Input
User Query: `"Find an agent capable of handling financial analysis."`

Output (Assigned)
```json
{
  "status": "assigned",
  "agent_uuid": "9423760127059366384"
}
```

Output (Unassigned)
```json
{
  "status": "unassigned",
  "message": "No matching agent could be found based on the provided query and agent descriptions."
}
```

Output (Error)
```json
{
  "status": "error",
  "message": "Unable to retrieve agent data. Please verify the input and try again."
}
```
"""


def ask_operation_hub(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AskOperationHubType:
    """
    Orchestrates operation hub requests and agent coordination by managing sessions,
    processing queries, and handling asynchronous updates.

    The function performs the following key operations:
    1. Resolves coordination details and creates/updates sessions
    2. Selects appropriate agent (task or triage) based on request
    3. Processes and enhances user queries for triage scenarios
    4. Manages connection IDs and receiver email routing
    5. Invokes AI model and creates session runs
    6. Triggers asynchronous session updates via Lambda

    Args:
        info (ResolveInfo): GraphQL context and metadata
        **kwargs: Request parameters including:
            - coordination_uuid: Unique identifier for coordination
            - user_id: Optional user identifier
            - agent_uuid: Optional agent identifier
            - session_uuid: Optional session identifier
            - user_query: User's input query
            - receiver_email: Optional email for routing
            - thread_uuid: Optional thread ID for conversation continuity

    Returns:
        AskOperationHubType: Structured response with session details and run metadata
    """
    Debugger.info(
        variable=info.context,
        stage=__name__,
    )

    try:
        # Step 1: Initialize and validate coordination
        coordination = resolve_coordination(
            info,
            **{
                "coordination_uuid": kwargs["coordination_uuid"],
            },
        )

        # Step 2: Create/update session
        session = _handle_session(info, **kwargs)

        # Step 3: Select and validate agent
        agent = _select_agent(coordination, **kwargs)

        # Step 4: Process query and handle routing
        user_query = _process_query(info, kwargs["user_query"], agent, coordination)
        connection_id = _handle_connection_routing(info, agent, **kwargs)

        # Step 5: Execute AI model and record session run
        variables = {
            "agentUuid": agent.get("agent_uuid"),
            "userQuery": user_query,
            "stream": kwargs.get("stream", False),
            "updatedBy": "operation_hub",
        }

        if kwargs.get("thread_uuid") is not None:
            variables["threadUuid"] = kwargs.get("thread_uuid")

        if kwargs.get("user_id") is not None:
            variables["userId"] = kwargs.get("user_id")

        if kwargs.get("thread_life_minutes") is not None:
            variables["threadLifeMinutes"] = kwargs["thread_life_minutes"]

        if kwargs.get("input_files") is not None:
            variables["inputFiles"] = kwargs["input_files"]

        ask_model = invoke_ask_model(context=info.context, **variables)
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>", info.context)
        session_run: SessionRunType = insert_update_session_run(
            info,
            **{
                "session_uuid": session.session_uuid,
                "run_uuid": ask_model["current_run_uuid"],
                "thread_uuid": ask_model["thread_uuid"],
                "agent_uuid": agent["agent_uuid"],
                "coordination_uuid": session.coordination_uuid,
                "async_task_uuid": ask_model["async_task_uuid"],
                "updated_by": "operation_hub",
            },
        )

        # Step 6: Handle async updates
        _trigger_async_update(info, session_run, connection_id, agent, **kwargs)

        # Step 7: Return response
        return AskOperationHubType(
            **{
                "coordination_uuid": session.coordination_uuid,
                "session_uuid": session.session_uuid,
                "partition_key": session.partition_key,
                "run_uuid": session_run.run_uuid,
                "thread_uuid": session_run.thread_uuid,
                "agent_uuid": session_run.agent_uuid,
                "async_task_uuid": session_run.async_task_uuid,
                "updated_at": session_run.updated_at,
            }
        )

    except Exception as e:
        Debugger.info(
            variable=f"Error: {e}, Trace: {traceback.format_exc()}",
            stage="AI Coordination Engine (ask_operation_hub)",
            setting=info.context.get("setting"),
            logger=info.context.get("logger"),
        )
        raise e


def _handle_session(info: ResolveInfo, **kwargs: Dict[str, Any]) -> SessionType | None:
    """
    Helper function to create or update a session.

    Args:
        info (ResolveInfo): GraphQL context and metadata
        **kwargs: Request parameters including:
            - coordination_uuid: Unique identifier for coordination
            - user_id: Optional user identifier
            - session_uuid: Optional session identifier
            - agent_uuid: Optional agent identifier

    Returns:
        SessionType: Session object with updated details
    """
    variables = {
        "coordination_uuid": kwargs["coordination_uuid"],
        "user_id": kwargs.get("user_id"),
        "updated_by": "operation_hub",
    }

    if "agent_uuid" in kwargs:
        variables.update({"status": "active"})
    else:
        variables.update({"status": "in_transit"})

    if "session_uuid" in kwargs:
        variables.update({"session_uuid": kwargs["session_uuid"]})

    return insert_update_session(info, **variables)


def _select_agent(
    coordination: CoordinationType, **kwargs: Dict[str, Any]
) -> Dict[str, Any] | None:
    """
    Helper function to select appropriate agent.

    Args:
        coordination (CoordinationType): Coordination object containing agent details
        **kwargs: Request parameters including:
            - agent_uuid: Optional agent identifier

    Returns:
        Dict[str, Any]: Selected agent details

    Raises:
        AssertionError: If no agents found for coordination
    """
    assert len(coordination.agents) > 0, "No agent found for the coordination."

    return next(
        (
            agent
            for agent in coordination.agents
            if agent.get("agent_uuid") == kwargs.get("agent_uuid")
        ),
        next(
            (
                agent
                for agent in coordination.agents
                if agent.get("agent_type") == "triage"
            ),
            None,
        ),
    )


def _process_query(
    info: ResolveInfo,
    user_query: str,
    agent: Dict[str, Any],
    coordination: CoordinationType,
) -> str:
    """
    Helper function to process and enhance user queries.

    Args:
        info (ResolveInfo): GraphQL context and metadata
        user_query (str): Original user query
        agent (Dict[str, Any]): Selected agent details
        coordination (CoordinationType): Coordination object containing agent details

    Returns:
        str: Processed query string with enhanced context for triage agents
    """
    if type(agent) is dict and agent.get("agent_type") == "triage":
        available_task_agents = [
            {
                "agent_uuid": agent["agent_uuid"],
                "agent_name": agent["agent_name"],
                "agent_description": agent["agent_description"],
            }
            for agent in coordination.agents
            if agent.get("agent_type") == "task"
        ]

        user_query = (
            f"Based on the following user query, please analyze and select the most appropriate agent:\n"
            f"User Query: {user_query}\n"
            f"Available Agents: {Serializer.json_dumps(available_task_agents)}\n"
            f"Please assess the intent behind the query and align it with the agent's most appropriate capabilities, then export the results in JSON format."
        )
        info.context.get("logger").info(f"Enhanced triage request: {user_query}")
    return user_query


def _handle_connection_routing(
    info: ResolveInfo,
    agent: Dict[str, Any],
    **kwargs: Dict[str, Any],
) -> Optional[str]:
    """
    Helper function to handle connection routing.

    Args:
        info (ResolveInfo): GraphQL context and metadata
        agent (Dict[str, Any]): Selected agent details
        **kwargs: Request parameters including:
            - receiver_email: Optional email for routing

    Returns:
        Optional[str]: Connection ID for routing messages
    """
    connection_id = info.context.get("connection_id")
    if "receiver_email" in kwargs and agent["agent_type"] != "triage":
        receiver_connection = get_connection_by_email(
            info.context.get("logger"),
            info.context.get("endpoint_id"),
            email=kwargs["receiver_email"],
        )
        if receiver_connection:
            connection_id = receiver_connection.get("connection_id", connection_id)
    return connection_id


def _trigger_async_update(
    info: ResolveInfo,
    session_run: SessionRunType,
    connection_id: str,
    agent: Dict[str, Any],
    **kwargs: Dict[str, Any],
) -> None:
    """
    Helper function to trigger async session updates.

    Args:
        info (ResolveInfo): GraphQL context and metadata
        session_run (SessionRunType): Current session run details
        connection_id (str): Connection ID for routing
        agent (Dict[str, Any]): Selected agent details
        **kwargs: Request parameters including:
            - receiver_email: Optional email for routing
    """
    params = {
        "coordination_uuid": session_run.coordination_uuid,
        "session_uuid": session_run.session_uuid,
        "run_uuid": session_run.run_uuid,
    }
    if connection_id:
        params["connection_id"] = connection_id

    if (
        connection_id is None
        and "receiver_email" in kwargs
        and agent["agent_type"] != "triage"
    ):
        params["receiver_email"] = kwargs["receiver_email"]

    Invoker.sync_call_async_compatible(
        coroutine_task=Invoker.create_async_task(
            task=Invoker.resolve_proxied_callable(
                module_name="ai_coordination_engine",
                function_name="async_insert_update_session",
                class_name="AICoordinationEngine",
                constructor_parameters={
                    "logger": info.context.get("logger"),
                    **info.context.get("setting", {}),
                },
            ),
            parameters=params,
        )
    )

    # Invoker.invoke_funct_on_aws_lambda(
    #     info.context,
    #     "async_insert_update_session",
    #     params=params,
    #     aws_lambda=Config.aws_lambda,
    #     invocation_type="Event",
    # )
