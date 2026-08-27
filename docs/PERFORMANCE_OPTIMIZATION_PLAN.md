# `ask_operation_hub` Performance Optimization Plan

> **Status**: Phase 1 reviewed and stabilized
> **Priority**: High
> **Last Updated**: April 7, 2026
> **Scope**: `ai_coordination_engine.handlers.operation_hub` and related query/model paths

---

## Executive Summary

The current codebase is materially closer to the optimization plan than it was in the earlier review. Phase 1 improvements are now present in the main request path and in the async listener path:

- redundant single-record DynamoDB reads were removed
- connection routing now uses the correct DynamoDB resource
- `ask_operation_hub()` emits structured step timing logs
- the async listener no longer reloads the session on every poll iteration
- outbound GraphQL calls now have configurable timeout enforcement

During this review, one regression in the new GraphQL wrapper was fixed before closing the phase: the wrapper was calling `Graphql.request_graphql()` with incorrect keyword names. That issue is now corrected.

Phase 2 and Phase 3 remain valid, but they should continue to be driven by measurement rather than assumptions.

---

## Current State vs Plan

### Phase 1

Status: complete after review fixes

Implemented:

- Corrected `Config.aws_dynamodb` usage to `Config.dynamodb` in connection lookup
- Replaced count-then-get patterns with direct fetch plus `DoesNotExist` handling in:
  - `models/coordination.py`
  - `models/session.py`
  - `models/session_run.py`
  - `models/session_agent.py`
  - `models/task.py`
  - `models/task_schedule.py`
- Replaced `print()` timing output in `operation_hub.py` with structured logger calls
- Simplified `_select_agent()` into explicit early-return loops
- Reduced async listener waste by loading the session only when a final write is needed
- Added adaptive polling backoff in `operation_hub_listener.py`
- Added timeout configuration in `Config`
- Added timeout enforcement around outbound GraphQL calls used by:
  - `invoke_ask_model()`
  - `get_async_task()`

Additional hardening applied during this review:

- fixed the GraphQL wrapper argument mismatch so requests actually execute correctly
- added an early coordination existence check before session creation in `ask_operation_hub()`
- added null guards for missing session run and session in the async listener path

### Phase 2

Status: pending

Still recommended:

- measure cache hit rates before adding more caching
- measure triage prompt serialization cost before caching it
- measure receiver-email lookup frequency before caching connection lookups
- collect step-level latency data from production-like traffic

### Phase 3

Status: pending

Still recommended:

- replace polling with event-driven completion if downstream infrastructure supports it
- otherwise continue improving the polling fallback with stronger backoff and idempotency checks

---

## What Was Fixed in This Review

### 1. GraphQL timeout wrapper regression

Issue:

- the new wrapper used `graphql_operation_name` and `graphql_operation_type`
- `Graphql.request_graphql()` expects `operation_name` and `operation_type`

Impact:

- outbound GraphQL calls could fail before execution

Fix:

- corrected the argument names
- kept structured logging
- added actual timeout enforcement via `ThreadPoolExecutor(...).result(timeout=...)`

### 2. Coordination validation ordering

Issue:

- `ask_operation_hub()` resolved coordination first but did not stop if it returned `None`
- session creation could still happen before the request failed

Fix:

- added an explicit guard: fail fast when coordination does not exist

### 3. Listener null safety

Issue:

- the optimized listener assumed `resolve_session_run()` and `resolve_session()` always returned objects

Fix:

- added explicit error checks for missing session run and missing session

---

## Remaining Opportunities

### Phase 2: Measured caching improvements

Do next:

1. instrument cache hit and miss rates by entity type
2. baseline p50, p95, and p99 latency for `ask_operation_hub`
3. measure triage request frequency and triage prompt assembly cost
4. decide whether serialized task-agent data is worth caching

Notes:

- request-scoped DataLoaders already exist for list and nested resolver paths
- they do not materially change the `ask_operation_hub()` hot path today
- any new cache should have a clear invalidation boundary tied to coordination updates

### Phase 3: Event-driven completion

Preferred design:

- downstream async completion emits an event
- this module updates the session from that event
- polling is removed from the critical runtime path

Fallback:

- keep polling
- retain lazy session loading
- consider increasing max backoff and adding idempotency protection

---

## Success Criteria

Phase 1 should now be considered successful if the implementation continues to hold these properties:

- one DynamoDB read for single-record resolver paths instead of count plus get
- no repeated session reload inside the polling loop
- structured timing logs for the `ask_operation_hub()` request path
- timeout enforcement on outbound GraphQL calls
- correct connection lookup resource usage

Phase 2 and Phase 3 should only proceed after baseline metrics are available.

---

## Verification Notes

This review included a compile pass for the modified modules and it completed successfully.

Validation performed:

- Python compile check for modified handler and model files

Not performed:

- integration tests against the downstream GraphQL service
- end-to-end execution against live DynamoDB or Lambda infrastructure

---

## Summary

The current development is broadly aligned with the performance plan, and the largest Phase 1 items are now in place. The main work required in this review was to stabilize the new implementation by fixing the GraphQL wrapper regression, enforcing the configured timeout boundary, and tightening a few correctness guards around coordination and listener state. The next sensible step is measurement, not more speculative optimization.
