"""
Thin shim modules — import from news.py where all are defined together.
Split into separate files if the project grows large.
"""
from skills.news import CalendarSkill, SearchSkill, SystemSkill

__all__ = ["CalendarSkill", "SearchSkill", "SystemSkill"]
