"""Public allocation entry points; implementation lives in allocation.py."""

from .allocation import optimise, pareto_frontier

__all__ = ["optimise", "pareto_frontier"]
