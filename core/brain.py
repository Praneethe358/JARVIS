"""
core/brain.py
─────────────
AI Brain — powered by the OpenAI API.

Handles:
  • General conversation
  • Study buddy Q&A
  • Multi-turn memory (rolling context window)
  • Personality: JARVIS-like — concise, intelligent, respectful

INSTALL:
    pip install openai
"""

from openai import OpenAI, AuthenticationError, RateLimitError
from collections import deque
from core.config import CONFIG
from core.logger import log


SYSTEM_PROMPT = """
You are JARVIS (Just A Rather Very Intelligent System), a personal AI assistant
for Praneeth — a 2nd-year AI & Data Science student at Karunya Institute of
Technology, India.

Personality:
- Concise, intelligent, slightly formal — like the JARVIS from Iron Man.
- Address the user as "Sir" occasionally, as Praneeth prefers.
- Keep spoken responses SHORT (2–3 sentences max) unless asked to explain in detail.
- For study topics (AI, ML, CV, Data Science), give clear, accurate technical answers.
- You are running on the user's laptop as a local Python application.

Current capabilities (handled by skill modules — do NOT fabricate results):
  weather, news, calendar, music, web search, system control, notes, analytics.

When a skill is handling the request, you will receive the skill's output and
should relay it naturally. When no skill matches, answer conversationally.
"""


class Brain:
    """
    Conversational AI core using OpenAI chat models.

    Usage:
        brain = Brain()
        response = brain.think("Explain gradient descent")
    """

    def __init__(self):
        api_key = CONFIG.get("openai_api_key")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not set in config.json or environment. "
                "Get your key at https://platform.openai.com/api-keys"
            )
        self.client  = OpenAI(api_key=api_key)
        self.model   = "gpt-4o-mini"
        self.history = deque(maxlen=20)  # rolling window: last 20 turns

        log.info(f"Brain (OpenAI {self.model}) initialised.")

    # ──────────────────────────────────────────────────────
    def think(self, user_input: str, context: str = "") -> str:
        """
        Send a message to OpenAI and return the text response.

        Args:
            user_input : what the user said
            context    : optional extra context injected by a skill
                         (e.g. weather data, search results)

        Returns:
            str: JARVIS's spoken response
        """
        content = user_input
        if context:
            content = f"{user_input}\n\n[Skill context for your response]:\n{context}"

        self.history.append({"role": "user", "content": content})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=300,          # short spoken answers
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *list(self.history)]
            )
            reply = (response.choices[0].message.content or "").strip()
            if not reply:
                reply = "I could not generate a response right now."
            self.history.append({"role": "assistant", "content": reply})
            return reply

        except AuthenticationError:
            return "I'm unable to connect — please check your API key, Sir."
        except RateLimitError:
            return "I'm being rate-limited. Please wait a moment."
        except Exception as e:
            log.error(f"Brain.think() error: {e}")
            return "I encountered an error processing that request."

    # ──────────────────────────────────────────────────────
    def study(self, topic: str, depth: str = "explain") -> str:
        """
        Study buddy mode — longer, detailed responses for learning.

        Args:
            topic : concept to explain (e.g. "backpropagation")
            depth : "explain" | "quiz" | "summarise"
        """
        prompts = {
            "explain"  : f"Explain '{topic}' clearly with an analogy and a simple example. Target audience: 2nd-year AI student.",
            "quiz"     : f"Give me 3 short quiz questions on '{topic}' with answers. Format: Q: ... A: ...",
            "summarise": f"Give a bullet-point summary of the key concepts in '{topic}' for quick revision.",
        }
        prompt = prompts.get(depth, prompts["explain"])

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=600,          # longer for study mode
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            return (response.choices[0].message.content or "").strip()

        except Exception as e:
            log.error(f"Brain.study() error: {e}")
            return "I couldn't fetch that topic right now."

    # ──────────────────────────────────────────────────────
    def clear_memory(self):
        """Reset conversation history."""
        self.history.clear()
        log.info("Conversation memory cleared.")
