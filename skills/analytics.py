"""
skills/analytics.py
────────────────────
Personal Analytics Skill — tracks interactions, daily usage, and summaries.
"""

import json
import os
import datetime
from collections import Counter
from core.logger import log


class AnalyticsSkill:
    """
    Logs every JARVIS interaction and generates productivity summaries.
    """

    triggers = ["analytics", "productivity", "how have i been",
                "my stats", "daily summary", "how many times", "usage"]

    LOG_FILE = "data/analytics.json"

    def __init__(self):
        self._log = self._load()

    def handle(self, command: str) -> str:
        return self._summary()

    def log_interaction(self, command: str, response: str):
        """Called by router after every successful interaction."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "command"  : command[:120],
            "skill"    : self._detect_skill(command),
        }
        self._log.append(entry)
        if len(self._log) % 10 == 0:   # save every 10 entries
            self._save()

    def _detect_skill(self, command: str) -> str:
        keywords = {
            "weather": "weather", "news": "news", "play": "music",
            "calendar": "calendar", "note": "notes", "search": "search",
            "open": "system", "shutdown": "system", "study": "study",
        }
        for kw, skill in keywords.items():
            if kw in command:
                return skill
        return "brain"

    def _summary(self) -> str:
        if not self._log:
            return "[Analytics] No data yet — start using JARVIS to build your stats."

        today = datetime.date.today().isoformat()
        today_entries = [e for e in self._log if e["timestamp"].startswith(today)]

        skill_counts = Counter(e["skill"] for e in self._log[-50:])
        most_used    = skill_counts.most_common(3)
        most_str     = ", ".join(f"{s} ({c}x)" for s, c in most_used)

        return (
            f"[Analytics] Today: {len(today_entries)} interactions. "
            f"Total: {len(self._log)} interactions logged. "
            f"Most used (last 50): {most_str}."
        )

    def _load(self) -> list:
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.LOG_FILE):
            with open(self.LOG_FILE) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.LOG_FILE, "w") as f:
            json.dump(self._log[-1000:], f, indent=2)  # keep last 1000 entries


# ══════════════════════════════════════════════════════════════════════════════
# STUDY SKILL
# ══════════════════════════════════════════════════════════════════════════════


class StudySkill:
    """
    Study buddy powered by the Brain (Claude API).
    Handles topic explanations, quiz generation, and PDF summarisation.

    TRIGGERS:
        "explain", "what is", "study", "quiz", "teach me", "summarise"
    """

    triggers = ["explain", "study", "quiz me", "teach me", "help me understand",
                "what does", "define", "summarise this", "exam", "revision"]

    def __init__(self):
        self._brain = None  # injected lazily to avoid circular import

    def _get_brain(self):
        if self._brain is None:
            from core.brain import Brain
            self._brain = Brain()
        return self._brain

    def handle(self, command: str) -> str:
        brain = self._get_brain()

        # Determine mode
        if "quiz" in command:
            topic = self._extract_topic(command, ["quiz me on", "quiz", "test me on"])
            return brain.study(topic, depth="quiz")

        elif any(w in command for w in ["summarise", "summary"]):
            topic = self._extract_topic(command, ["summarise", "summary of"])
            return brain.study(topic, depth="summarise")

        else:
            topic = self._extract_topic(command, ["explain", "what is", "what does",
                                                   "teach me", "help me understand", "define"])
            return brain.study(topic, depth="explain")

    def _extract_topic(self, command: str, keywords: list) -> str:
        topic = command
        for kw in sorted(keywords, key=len, reverse=True):
            if kw in topic:
                topic = topic.split(kw, 1)[-1].strip()
                break
        return topic or command
