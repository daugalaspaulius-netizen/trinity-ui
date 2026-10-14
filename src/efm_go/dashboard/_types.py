"""Shared TYPE_CHECKING imports for dashboard modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from efm_go.context import ContextBuilder
    from efm_go.cron import CronService
    from efm_go.history import ConversationLog, HistoryConsolidator
    from efm_go.learn import LessonStore
    from efm_go.session import SessionManager
    from efm_go.subagent import SubagentManager
    from efm_go.taskrunner import TaskRunner

__all__ = [
    "ContextBuilder",
    "CronService",
    "ConversationLog",
    "HistoryConsolidator",
    "LessonStore",
    "SessionManager",
    "SubagentManager",
    "TaskRunner",
]
