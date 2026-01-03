# Voice Agent Testing Plan

This document outlines the strategy for validating the Voice Agent's functionality, reliability, and performance with Cloud Redis.

## 1. Unit Testing (Automated)
**Goal**: Verify individual components work in isolation.

*   **Tools (`tests/test_tools.py`)**:
    *   Verify `billing_tools` (balance calculation logic).
    *   Verify `network_tools` (mock status logic).
    *   Verify `escalation_tools` (ticket ID generation).
*   **Factory (`tests/test_factory.py`)**:
    *   Verify `create_agent_graph` injects User ID into System Prompt.
    *   Verify agents have correct tools attached.

**Action**: Run `pytest tests/`

## 2. Functional Testing (Automated)
**Goal**: Verify the system flows correctly without real telephony.

*   **Server Logic (`tests/test_server_logic.py`)**:
    *   Mock `RedisDatabase` and `Twilio`.
    *   Simulate `/voice` -> Greeting.
    *   Simulate `/gather_speech` -> Hangup Intent (Instant).
    *   Simulate `/gather_speech` -> Agent Intent (Task creation).

## 3. Integration Testing (Manual)
**Goal**: Verify the end-to-end system with **Real Cloud Redis**.

| Test Case | Step | Expected Result | Verified |
| :--- | :--- | :--- | :--- |
| **Cloud DB Connect** | Start Server | "Connected to Redis" in logs | [✓] |
| **Latency Check** | "Check balance" | Filler: "Checking details..." -> Delay -> Correct Balance | [✓] |
| **Persistence** | "Talk to human" | Ticket ID generated. Check Redis for key `ticket:TICKET-...` | [✓] |
| **Hangup** | "Thanks bye" | Instant hangup (No Agent Latency) | [✓] |

## 4. Performance & Reliability
*   **Latency**: Cloud Redis adds ~500ms round-trip.
    *   *Mitigation*: Smart Fillers ("Checking balance...") run *before* the DB query in the Agent flow?
    *   *Correction*: Smart Fillers run *before* the Agent invocation. Actual DB tools run *inside* the Agent.
    *   *Impact*: tool execution will take longer. We need to ensure `Runner` doesn't timeout.

## Execution Steps
1.  Create `tests/` directory.
2.  Write Unit/Functional tests.
3.  Run `pytest`.
4.  Perform Manual Integration steps.
