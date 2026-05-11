"""
skills/study.py
───────────────
Local study helper shim.
"""

from core.logger import log


class StudySkill:
	triggers = ["explain", "study", "quiz me", "teach me", "help me understand",
				"what does", "summarise this", "exam", "revision"]

	def handle(self, command: str) -> str:
		from core.brain import Brain
		topic = self._extract_topic(command, ["explain", "study", "quiz me", "teach me", "help me understand", "what does", "summarise", "summary"])
		mode = "quiz" if "quiz" in command else "summarise" if any(w in command for w in ["summarise", "summary"]) else "explain"
		brain = Brain()
		result = brain.study(topic, depth=mode)
		log.info(f"[StudySkill] {mode} -> {topic}")
		return result

	def _extract_topic(self, command: str, keywords: list) -> str:
		topic = command
		for kw in sorted(keywords, key=len, reverse=True):
			if kw in topic:
				topic = topic.split(kw, 1)[-1].strip()
				break
		return topic or command
