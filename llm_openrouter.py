"""
llm_openrouter.py
─────────────────
OpenRouter LLM module.
Handles multi-turn conversational history and self-healing model fallback.
"""

import json
import time
import requests
import hashlib
from config import OPENROUTER_URL, OPENROUTER_API_KEY, LLM_MODEL_DEFAULT, LLM_MODEL_FALLBACK, LLM_SYSTEM_PROMPT, LLM_HEADERS, CACHE_TTL_SEC

class OpenRouterLLM:
    def __init__(self):
        self.history = []
        self.cache = {}
        self.model = LLM_MODEL_DEFAULT
        self.max_history = 10 # Keep last 10 messages

    def clear_memory(self):
        self.history.clear()

    def generate(self, user_input: str, context: str = "") -> str:
        """
        Generate response from OpenRouter, with context injection and caching.
        """
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
            print("\r[🔴] OpenRouter API Key missing. Check .env")
            return "My reasoning core is offline due to a missing API key."

        # ── Caching ──────────────────────────────────────────────────────────
        cache_key = hashlib.md5(f"{user_input}{context}".encode()).hexdigest()
        if cache_key in self.cache:
            resp, timestamp = self.cache[cache_key]
            if time.time() - timestamp < CACHE_TTL_SEC:
                return resp

        # ── Build Messages ───────────────────────────────────────────────────
        messages = [{"role": "system", "content": LLM_SYSTEM_PROMPT}]
        
        for msg in self.history:
            messages.append(msg)
            
        if context:
            full_prompt = f"[SYSTEM CONTEXT]\n{context}\n\n[USER]\n{user_input}"
        else:
            full_prompt = user_input
            
        messages.append({"role": "user", "content": full_prompt})

        # ── Fallback Loop ────────────────────────────────────────────────────
        models_to_try = [
            "openrouter/free",
            "meta-llama/llama-4-scout:free",
            "meta-llama/llama-4-maverick:free",
            "google/gemini-2.0-flash-exp:free",
            "mistralai/mistral-small-3:free",
            "deepseek/deepseek-r1:free"
        ]

        for attempt_model in models_to_try:
            print(f"\r[⚡] Thinking ({attempt_model})...")
            payload = {
                "model": attempt_model,
                "messages": messages,
                "max_tokens": 512,
                "temperature": 0.7,
            }

            try:
                response = requests.post(
                    OPENROUTER_URL,
                    headers=LLM_HEADERS,
                    json=payload,
                    timeout=30
                )
                
                # Check for errors (404, 429, 500, etc)
                if response.status_code != 200:
                    print(f"\r[🔴] Model {attempt_model} failed with HTTP {response.status_code}. Trying next...")
                    continue
                    
                data = response.json()
                
                choices = data.get("choices", [])
                if not choices:
                    print(f"\r[🔴] Model {attempt_model} returned empty response. Trying next...")
                    continue
                    
                reply = choices[0].get("message", {}).get("content", "").strip()
                
                # Strip thinking tags <think>...</think>
                import re
                reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()
                
                # Update history
                self.history.append({"role": "user", "content": user_input})
                self.history.append({"role": "assistant", "content": reply})
                
                # Prune history
                if len(self.history) > self.max_history:
                    self.history = self.history[-self.max_history:]
                    
                # Cache response
                self.cache[cache_key] = (reply, time.time())
                return reply
                
            except requests.exceptions.Timeout:
                print(f"\r[🔴] Model {attempt_model} timed out. Trying next...")
                continue
            except Exception as e:
                print(f"\r[🔴] Model {attempt_model} exception: {e}. Trying next...")
                continue

        return "NEXUS offline. Try again shortly."
