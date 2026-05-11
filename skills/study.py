"""
skills/study.py
───────────────
Study / explain skill powered by Ollama.

All queries are routed to the Ollama reasoning core for accurate, dynamic
responses instead of a hardcoded keyword bank.
Falls back to a generic prompt message when Ollama is unavailable.
"""

from core.logger import log


class StudySkill:
    triggers = [
        "explain", "study", "quiz me", "teach me", "help me understand",
        "what does", "summarise this", "exam", "revision", "how does",
    ]

    def handle(self, command: str) -> str:
        """
        Route study/explain queries directly to Ollama via the Brain's
        ask_ollama() helper, which bypasses local keyword banks.
        """
        from core.brain import Brain

        # Extract the topic/question the user actually wants explained
        topic = self._extract_topic(command, [
            "explain", "study", "quiz me", "teach me",
            "help me understand", "what does", "summarise",
            "summary", "how does",
        ])

        # Build a focused study prompt for Ollama
        mode = (
            "quiz" if "quiz" in command
            else "summarise" if any(w in command for w in ["summarise", "summary"])
            else "explain"
        )
        prompt = f"{mode.capitalize()} '{topic}' in a clear, conversational way suitable for spoken delivery."

        log.info(f"[StudySkill] Routing to Ollama — mode={mode}, topic='{topic}'")

        # Instantiate brain and ask Ollama directly
        brain = Brain()
        result = brain.ask_ollama(prompt)

        if result:
            return result

        # Graceful fallback when Ollama is offline
        return (
            f"My reasoning core is offline. I can't dynamically explain {topic} right now. "
            "Try again when the Ollama service is running."
        )

    def _extract_topic(self, command: str, keywords: list) -> str:
        """Strip the trigger keyword and return the remaining topic string."""
        topic = command
        for kw in sorted(keywords, key=len, reverse=True):
            if kw in topic:
                topic = topic.split(kw, 1)[-1].strip()
                break
        return topic or command
