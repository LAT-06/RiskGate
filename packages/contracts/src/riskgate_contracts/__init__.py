"""Shared contracts: identifiers, API schemas, and event schemas.

Services must not share ORM models — only the schemas defined here.
"""

from riskgate_contracts.decisions import RiskDecision

__all__ = ["RiskDecision"]
