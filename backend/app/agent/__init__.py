"""
agent/__init__.py
─────────────────
AI Agent Reasoner & State Machine Orchestrator (Phase 10).

Exposes:
  - AgentOrchestrator: High-level orchestrator driving recovery cases through the state machine.
  - run_agent_for_case: Helper to execute the autonomous reasoning loop for a case.
"""

from app.agent.orchestrator import AgentOrchestrator, run_agent_for_case

__all__ = ["AgentOrchestrator", "run_agent_for_case"]
