"""
core/brain.py
─────────────
Local-only conversational brain for NEXUS.

This version does not use any external model APIs. It provides:
- friendly local replies
- basic study explanations
- simple memory reset support
"""

from collections import deque
from core.logger import log


_STUDY_BANK = {
    "gradient descent": (
        "Gradient descent is an optimisation method that moves parameters in the direction "
        "that reduces error the fastest. Think of it like walking downhill by feeling the slope under your feet."
    ),
    "overfitting": (
        "Overfitting happens when a model memorises training data instead of learning the general pattern. "
        "It scores high on training data but struggles on new data."
    ),
    "underfitting": (
        "Underfitting means the model is too simple to capture the underlying pattern in the data. "
        "It performs poorly on both training and test data."
    ),
    "backpropagation": (
        "Backpropagation is the method neural networks use to distribute error backward through the layers. "
        "That error is used to update weights and improve predictions."
    ),
    "classification": (
        "Classification is a supervised learning task where the model predicts a category label, such as spam or not spam."
    ),
    "regression": (
        "Regression is a supervised learning task where the model predicts a numeric value, such as house price."
    ),
    "normalization": (
        "Normalization rescales values into a common range so features with larger magnitudes do not dominate learning."
    ),
    "bias variance": (
        "Bias is error from overly simple assumptions. Variance is error from being too sensitive to training data. "
        "Good models balance both."
    ),
}


class Brain:
    """Conversational local brain for NEXUS."""

    def __init__(self):
        self.history = deque(maxlen=20)
        log.info("Local Brain initialised.")

    def _local_reply(self, user_input: str, context: str = "") -> str:
        text = user_input.lower().strip()

        if context:
            return context

        if any(phrase in text for phrase in ["how are you", "how r you", "how r u"]):
            return "I am running locally and ready, Sir."

        if any(phrase in text for phrase in ["what can you do", "help", "features", "what are your features"]):
            return (
                "I can open apps, handle notes and reminders, manage your schedule, show the time and date, "
                "do local study explanations, check weather or news if keys are configured, and help with system tasks."
            )

        if any(phrase in text for phrase in ["who are you", "what are you"]):
            return "I am NEXUS, your local assistant."

        if any(phrase in text for phrase in ["thank you", "thanks"]):
            return "You are welcome, Sir."

        if any(phrase in text for phrase in ["good night", "bye", "goodbye"]):
            return "Goodbye, Sir."

        return (
            "I can help with local tasks, notes, reminders, schedule management, app launching, "
            "and study explanations. Try asking for help, your schedule, or a specific app to open."
        )

    def think(self, user_input: str, context: str = "") -> str:
        content = user_input
        if context:
            content = f"{user_input}\n\n[Skill context]:\n{context}"

        self.history.append({"role": "user", "content": content})
        reply = self._local_reply(user_input, context)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def study(self, topic: str, depth: str = "explain") -> str:
        topic_clean = topic.lower().strip()
        matched = None
        for key in _STUDY_BANK:
            if key in topic_clean:
                matched = key
                break

        if depth == "quiz":
            return (
                f"Quiz on {topic}:\n"
                f"1. What is {topic}?\n"
                f"2. Why is {topic} important?\n"
                f"3. Give one real-world use of {topic}."
            )

        if depth == "summarise":
            if matched:
                return f"Summary of {topic}:\n- {_STUDY_BANK[matched]}"
            return (
                f"Summary of {topic}:\n"
                f"- It is a core concept to study.\n"
                f"- Focus on the definition, example, and why it matters.\n"
                f"- Practice one small real-world example."
            )

        if matched:
            return _STUDY_BANK[matched]

        return (
            f"{topic} is a useful topic to study. Start with the definition, then a simple example, then a small use case. "
            f"If you want, I can turn it into a short quiz or summary."
        )

    def clear_memory(self):
        self.history.clear()
        log.info("Conversation memory cleared.")
