from __future__ import annotations

from base_typed_int import BaseTypedInt


class AgentCount(BaseTypedInt):
    "Number of agents"


class RequiredAgentCount(AgentCount):
    """
    Number of agents required by specifications
    """


class AssignedAgentCount(AgentCount):
    """
    Number of agents assigned to task/role
    """
