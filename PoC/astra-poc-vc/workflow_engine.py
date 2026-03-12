"""
Workflow Engine — detects repeated action patterns and proposes automations.

Lifecycle:
  1. log_action(trigger, action) — called after every tool use
  2. check_patterns() — returns a workflow proposal if pattern seen 2+ times
  3. enable/disable workflows stored in memory
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("astra.workflows")

# ---------------------------------------------------------------------------
# Seed workflows — pre-loaded for demo
# ---------------------------------------------------------------------------

SEED_WORKFLOWS = [
    {
        "id": "bloomberg_stock_alert",
        "name": "Bloomberg → Stock Alert",
        "description": "When a Bloomberg email arrives, automatically analyze mentioned stocks and show an alert widget.",
        "trigger": "email_from:bloomberg",
        "hit_count": 1,  # one more trigger = proposal shown
        "enabled": False,
    },
    {
        "id": "meeting_prep",
        "name": "Auto Meeting Prep",
        "description": "30 minutes before a client meeting, automatically prepare a briefing with attendee history and relevant files.",
        "trigger": "calendar_event_soon",
        "hit_count": 0,
        "enabled": False,
    },
    {
        "id": "morning_briefing",
        "name": "Morning Briefing",
        "description": "On first login each day, show a full briefing: emails, calendar, stocks, and travel alerts.",
        "trigger": "session_start",
        "hit_count": 0,
        "enabled": True,  # always on
    },
]


@dataclass
class WorkflowProposal:
    workflow_id: str
    name: str
    description: str
    trigger_description: str


class WorkflowEngine:
    """
    Tracks action sequences and detects automation opportunities.
    Stateless between restarts — uses memory store for persistence.
    """

    def __init__(self):
        # In-memory action log: trigger -> list of action sequences
        self._action_log: dict[str, list[list[str]]] = defaultdict(list)
        self._current_sequence: list[str] = []
        self._current_trigger: Optional[str] = None
        # Workflow state: id -> dict
        self._workflows: dict[str, dict] = {w["id"]: dict(w) for w in SEED_WORKFLOWS}
        # Track which proposals have already been shown
        self._proposed: set[str] = set()

    def start_turn(self, trigger: str):
        """Call at the start of each agent turn with the trigger type."""
        self._current_trigger = trigger
        self._current_sequence = []

    def log_action(self, tool_name: str):
        """Call each time the agent uses a tool."""
        self._current_sequence.append(tool_name)

    def end_turn(self) -> Optional[WorkflowProposal]:
        """
        Call at the end of each agent turn.
        Returns a WorkflowProposal if a new pattern was detected, else None.
        """
        if not self._current_trigger or not self._current_sequence:
            return None

        trigger = self._current_trigger
        actions = list(self._current_sequence)

        # Log this sequence
        self._action_log[trigger].append(actions)

        # Check if any seed workflow matches this trigger and should be proposed
        for wf_id, wf in self._workflows.items():
            if wf["enabled"]:
                continue  # already enabled, no need to propose
            if wf_id in self._proposed:
                continue  # already proposed this session

            if self._trigger_matches(trigger, wf["trigger"]):
                wf["hit_count"] += 1
                if wf["hit_count"] >= 2:
                    self._proposed.add(wf_id)
                    return WorkflowProposal(
                        workflow_id=wf_id,
                        name=wf["name"],
                        description=wf["description"],
                        trigger_description=self._trigger_label(trigger),
                    )

        # Check for emergent patterns (not in seed workflows)
        return self._detect_emergent_pattern(trigger, actions)

    def _trigger_matches(self, actual: str, pattern: str) -> bool:
        """Check if an actual trigger matches a workflow trigger pattern."""
        if pattern == actual:
            return True
        if pattern.startswith("email_from:"):
            domain = pattern.split(":", 1)[1]
            return actual.startswith("email_") and domain in actual
        return False

    def _trigger_label(self, trigger: str) -> str:
        labels = {
            "session_start": "you open AstraOS",
            "email_bloomberg": "a Bloomberg email arrives",
            "calendar_event_soon": "a meeting is coming up",
        }
        return labels.get(trigger, trigger.replace("_", " "))

    def _detect_emergent_pattern(self, trigger: str, actions: list[str]) -> Optional[WorkflowProposal]:
        """Detect a new pattern from the action log (not in seed workflows)."""
        history = self._action_log[trigger]
        if len(history) < 2:
            return None

        # Check if last 2 sequences share the same first 2 actions
        if len(history) >= 2:
            prev = history[-2]
            curr = history[-1]
            shared = [a for a, b in zip(prev, curr) if a == b]
            if len(shared) >= 2:
                pattern_id = f"auto_{trigger}_{shared[0]}"
                if pattern_id not in self._proposed and pattern_id not in self._workflows:
                    self._proposed.add(pattern_id)
                    action_desc = " → ".join(shared[:3])
                    return WorkflowProposal(
                        workflow_id=pattern_id,
                        name=f"Auto: {action_desc}",
                        description=f"I noticed that when {self._trigger_label(trigger)}, you always {action_desc.replace('_', ' ')}. Want me to do this automatically?",
                        trigger_description=self._trigger_label(trigger),
                    )
        return None

    def enable(self, workflow_id: str):
        if workflow_id in self._workflows:
            self._workflows[workflow_id]["enabled"] = True
            logger.info("Workflow enabled: %s", workflow_id)

    def disable(self, workflow_id: str):
        if workflow_id in self._workflows:
            self._workflows[workflow_id]["enabled"] = False
            logger.info("Workflow disabled: %s", workflow_id)

    def is_enabled(self, workflow_id: str) -> bool:
        return self._workflows.get(workflow_id, {}).get("enabled", False)

    def list_workflows(self) -> list[dict]:
        return list(self._workflows.values())

    def to_proposal_components(self, proposal: WorkflowProposal) -> list[dict]:
        """Convert a WorkflowProposal into A2UI components for emit_ui."""
        return [
            {
                "id": "root",
                "type": "Card",
                "props": {"variant": "glass"},
                "children": ["header", "desc", "actions"],
            },
            {
                "id": "header",
                "type": "Text",
                "props": {
                    "content": "🔄 Workflow Suggestion",
                    "variant": "title",
                    "style": {"color": "#f59e0b", "marginBottom": "8px"},
                },
                "children": [],
            },
            {
                "id": "desc",
                "type": "Text",
                "props": {
                    "content": proposal.description,
                    "variant": "body",
                    "style": {"marginBottom": "16px"},
                },
                "children": [],
            },
            {
                "id": "actions",
                "type": "Row",
                "props": {"gap": 8},
                "children": ["btn-enable", "btn-dismiss"],
            },
            {
                "id": "btn-enable",
                "type": "Button",
                "props": {
                    "label": "Enable",
                    "variant": "primary",
                    "action": f"workflow_enable:{proposal.workflow_id}",
                },
                "children": [],
            },
            {
                "id": "btn-dismiss",
                "type": "Button",
                "props": {
                    "label": "Not Now",
                    "variant": "secondary",
                    "action": f"workflow_dismiss:{proposal.workflow_id}",
                },
                "children": [],
            },
        ]


# Singleton
_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
