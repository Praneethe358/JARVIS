"""
skills/notes.py
───────────────
Note-Taking Skill — voice-dictated notes with timestamps and search.

TRIGGERS:
    "note", "write down", "remember", "take note", "my notes", "show notes"
"""

import json
import os
import datetime
from core.logger import log


class NotesSkill:

    triggers = ["note", "write down", "remember that", "take note",
                "show notes", "my notes", "read notes", "search notes"]

    NOTES_FILE = "data/notes.json"

    def __init__(self):
        self._notes = self._load()

    def handle(self, command: str) -> str:
        if any(w in command for w in ["show", "read", "list", "my notes"]):
            return self._list_notes()

        elif "search" in command:
            import re
            q = re.sub(r'\bsearch notes\b|\bsearch\b', '', command).strip()
            return self._search_notes(q)

        elif any(w in command for w in ["delete", "remove", "clear notes"]):
            return self._clear_notes()

        else:
            # Treat the command as the note content
            content = command
            for kw in ["take note", "write down", "note that", "remember that",
                       "note", "remember"]:
                if kw in content:
                    content = content.split(kw, 1)[-1].strip()
                    break

            return self._save_note(content)

    def _save_note(self, content: str) -> str:
        if not content:
            return "[Notes] Nothing to save."

        note = {
            "id"       : len(self._notes) + 1,
            "content"  : content,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds")
        }
        self._notes.append(note)
        self._save()
        log.info(f"[NotesSkill] Saved note #{note['id']}")
        return f"[Notes] Note saved: '{content[:60]}{'...' if len(content)>60 else ''}'."

    def _list_notes(self) -> str:
        if not self._notes:
            return "[Notes] No notes saved yet."
        recent = self._notes[-5:]
        lines = [f"#{n['id']} [{n['timestamp'][:10]}]: {n['content']}" for n in reversed(recent)]
        return "Recent notes:\n" + "\n".join(lines)

    def _search_notes(self, query: str) -> str:
        if not query:
            return self._list_notes()
        results = [n for n in self._notes if query.lower() in n["content"].lower()]
        if not results:
            return f"[Notes] No notes matching '{query}'."
        lines = [f"#{n['id']}: {n['content']}" for n in results[:5]]
        return f"Found {len(results)} note(s):\n" + "\n".join(lines)

    def _clear_notes(self) -> str:
        self._notes = []
        self._save()
        return "[Notes] All notes cleared."

    def _load(self) -> list:
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.NOTES_FILE):
            with open(self.NOTES_FILE) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.NOTES_FILE, "w") as f:
            json.dump(self._notes, f, indent=2)
