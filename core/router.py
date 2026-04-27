"""
core/router.py
──────────────
Command Router — maps a voice command (text) to the correct skill.

Strategy: keyword matching first → LLM fallback.

Each skill declares `triggers: list[str]` — keywords that activate it.
Router finds the best match; if none found, Brain handles it.
"""

import re
from core.logger import log


class CommandRouter:
    """
    Routes parsed voice commands to skill handlers or the AI brain.

    Args:
        skills  : list of skill instances (each has .triggers and .handle())
        brain   : Brain instance for fallback conversation
    """

    def __init__(self, skills: list, brain):
        self.skills    = skills
        self.brain     = brain

        # Build skill reference for analytics access
        self.analytics = next(
            (s for s in skills if s.__class__.__name__ == "AnalyticsSkill"),
            None
        )
        log.info(f"Router loaded with {len(skills)} skills.")

    # ──────────────────────────────────────────────────────
    def handle(self, command: str) -> str:
        """
        Match command to a skill or fall through to AI brain.

        Returns:
            str: response text to be spoken
        """
        if not command:
            return "I didn't receive a command."

        command_lower = command.lower().strip()

        # ── 1. Special commands ────────────────────────────
        if any(w in command_lower for w in ["exit", "shutdown jarvis", "goodbye"]):
            return "Shutting down. Goodbye, Sir."

        if "clear memory" in command_lower or "forget everything" in command_lower:
            self.brain.clear_memory()
            return "Conversation memory cleared, Sir."

        # ── 2. Skill matching ──────────────────────────────
        matched_skill = self._match_skill(command_lower)

        if matched_skill:
            log.info(f"Routing to skill: {matched_skill.__class__.__name__}")
            try:
                result = matched_skill.handle(command_lower)
                # Pass skill output through brain for natural delivery
                return self.brain.think(command_lower, context=result)
            except Exception as e:
                log.error(f"Skill {matched_skill.__class__.__name__} error: {e}")
                return f"I encountered an issue with that, Sir. {str(e)}"

        # ── 3. Brain fallback ──────────────────────────────
        log.info("No skill matched — routing to Brain.")
        return self.brain.think(command_lower)

    # ──────────────────────────────────────────────────────
    def _match_skill(self, command: str):
        """
        Find the highest-priority skill matching the command.
        Returns the skill instance or None.
        """
        best_skill  = None
        best_score  = 0

        for skill in self.skills:
            score = self._score(command, skill.triggers)
            if score > best_score:
                best_score = score
                best_skill = skill

        if best_score > 0:
            return best_skill
        return None

    def _score(self, command: str, triggers: list[str]) -> int:
        """
        Score how well a command matches a skill's triggers.
        Returns count of trigger words found in command.
        """
        count = 0
        for trigger in triggers:
            if re.search(r'\b' + re.escape(trigger) + r'\b', command):
                count += 1
        return count
