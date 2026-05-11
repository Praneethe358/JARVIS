"""
skills/personal.py
──────────────────
Local personal-assistant skill for FAQs, schedules, reminders, and daily planning.
"""

import datetime
import json
import os
import re
from core.config import CONFIG
from core.logger import log


class PersonalAssistantSkill:
    triggers = [
        "help", "assistant", "faq", "features", "what can you do",
        "who are you", "who am i", "my profile", "my schedule",
        "work schedule", "schedule", "remind me", "reminder",
        "reminders", "my reminders", "my day", "today plan", "today schedule", "daily plan",
        "routine", "plan my day", "todo", "task"
    ]

    REMINDERS_FILE = "data/reminders.json"
    SCHEDULE_FILE = "data/work_schedule.json"

    def __init__(self):
        self._reminders = self._load_json(self.REMINDERS_FILE)
        self._schedule = self._load_json(self.SCHEDULE_FILE)

    def handle(self, command: str) -> str:
        text = command.lower().strip()

        if any(phrase in text for phrase in ["what can you do", "help", "features", "faq"]):
            return self._features()

        if any(phrase in text for phrase in ["who are you", "who am i", "my profile"]):
            return self._profile()

        if "remind" in text or "reminder" in text:
            if any(phrase in text for phrase in ["show", "list", "what are", "my reminders", "check reminders"]):
                return self._list_reminders()
            if any(phrase in text for phrase in ["clear", "delete", "remove all"]):
                return self._clear_reminders()
            return self._add_reminder(text)

        if any(phrase in text for phrase in ["schedule", "work schedule", "today plan", "today schedule", "daily plan", "my day", "routine", "plan my day", "todo", "task"]):
            if any(phrase in text for phrase in ["add", "set", "create", "note"]):
                return self._add_schedule(text)
            return self._daily_plan()

        return self._features()

    def check_due_reminders(self) -> list[str]:
        now = datetime.datetime.now()
        due_messages = []
        changed = False

        for reminder in self._reminders:
            if reminder.get("done"):
                continue
            due_at = reminder.get("due_at")
            if not due_at:
                continue
            try:
                due_time = datetime.datetime.fromisoformat(due_at)
            except ValueError:
                continue
            if due_time <= now:
                reminder["done"] = True
                due_messages.append(f"Reminder: {reminder['text']}")
                changed = True

        if changed:
            self._save_json(self.REMINDERS_FILE, self._reminders)

        return due_messages

    def _features(self) -> str:
        user_name = CONFIG.get("user_name", "Praneeth")
        return (
            f"I can help you, {user_name}, with local features like:\n"
            "- open apps and websites\n"
            "- save notes\n"
            "- add and check reminders\n"
            "- store your work schedule\n"
            "- show time and date\n"
            "- give study explanations and quick quizzes\n"
            "- show weather, news, and system info when those keys are configured"
        )

    def _profile(self) -> str:
        user_name = CONFIG.get("user_name", "Praneeth")
        city = CONFIG.get("city", "Coimbatore")
        return f"You are {user_name} and your default city is {city}. I can remember reminders, schedule entries, and notes locally."

    def _add_reminder(self, command: str) -> str:
        # Determine due datetime first
        due_at = self._extract_due_datetime(command)

        # Remove common leading phrases robustly via regex
        text = command
        prefix_pattern = r'^(?:\s*)(?:add reminder(?: to| for| at)?|remind me(?: to| that)?|set reminder(?: to| for)?)(?:\b|\s)'
        text = re.sub(prefix_pattern, '', text, flags=re.IGNORECASE)

        # Strip date/time tokens from the remaining text
        text = re.sub(r'\b(\d{4}-\d{2}-\d{2})\b', ' ', text)
        text = re.sub(r'\b\d{1,2}:\d{2}\b', ' ', text)
        text = re.sub(r'\b\d{1,2}(?::\d{2})?\s*(am|pm)\b', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(today|tomorrow|at|on)\b', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip(' ,.')

        if not text:
            return "[Reminders] Tell me what to remind you about."

        entry = {
            "id": len(self._reminders) + 1,
            "text": text,
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "due_at": due_at.isoformat(timespec="seconds") if due_at else "",
            "done": False,
        }
        self._reminders.append(entry)
        self._save_json(self.REMINDERS_FILE, self._reminders)
        when = due_at.strftime("%Y-%m-%d %H:%M") if due_at else "no specific time"
        log.info(f"[PersonalAssistantSkill] Saved reminder #{entry['id']}")
        return f"[Reminders] Reminder saved for {when}: {text}"

    def _list_reminders(self) -> str:
        active = [r for r in self._reminders if not r.get("done")]
        if not active:
            return "[Reminders] You have no active reminders."
        lines = []
        for reminder in active[-5:]:
            when = reminder.get("due_at") or "unscheduled"
            lines.append(f"#{reminder['id']} [{when}]: {reminder['text']}")
        return "Active reminders:\n" + "\n".join(lines)

    def _clear_reminders(self) -> str:
        self._reminders = []
        self._save_json(self.REMINDERS_FILE, self._reminders)
        return "[Reminders] All reminders cleared."

    def _add_schedule(self, command: str) -> str:
        text = self._extract_text(command, ["add schedule", "set schedule", "create schedule", "schedule", "add task", "plan"])
        due_at = self._extract_due_datetime(command)
        if not text:
            return "[Schedule] Tell me what to add to your schedule."

        entry = {
            "id": len(self._schedule) + 1,
            "text": text,
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "due_at": due_at.isoformat(timespec="seconds") if due_at else "",
        }
        self._schedule.append(entry)
        self._save_json(self.SCHEDULE_FILE, self._schedule)
        when = due_at.strftime("%Y-%m-%d %H:%M") if due_at else "no specific time"
        log.info(f"[PersonalAssistantSkill] Saved schedule item #{entry['id']}")
        return f"[Schedule] Added to your schedule for {when}: {text}"

    def _daily_plan(self) -> str:
        today = datetime.date.today().isoformat()
        todays_schedule = [s for s in self._schedule if s.get("due_at", "").startswith(today)]
        active_reminders = [r for r in self._reminders if not r.get("done")]

        lines = [f"JARVIS daily plan for {CONFIG.get('user_name', 'Praneeth')}:"]
        if todays_schedule:
            lines.append("Today’s schedule:")
            for item in todays_schedule[-5:]:
                lines.append(f"- {item.get('due_at', 'unscheduled')}: {item['text']}")
        else:
            lines.append("- No schedule entries for today.")

        if active_reminders:
            lines.append("Active reminders:")
            for item in active_reminders[-3:]:
                lines.append(f"- {item['text']}")

        return "\n".join(lines)

    def _extract_text(self, command: str, prefixes: list[str]) -> str:
        text = command
        # Prefer matching prefixes at the start for more reliable extraction
        for prefix in sorted(prefixes, key=len, reverse=True):
            pattern = r'^\s*' + re.escape(prefix) + r'\b(.*)'
            m = re.match(pattern, text, flags=re.IGNORECASE)
            if m:
                text = m.group(1).strip()
                break
            # fallback: if prefix appears elsewhere, split as before
            if prefix in text:
                text = text.split(prefix, 1)[-1].strip()
                break

        text = re.sub(r'\b(today|tomorrow|at|on|remind me|set reminder|add schedule|set schedule|create schedule|add task|plan)\b', ' ', text)
        text = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', ' ', text)
        text = re.sub(r'\b\d{1,2}:\d{2}\b', ' ', text)
        # remove am/pm times like '2pm' or '2:30 am'
        text = re.sub(r'\b\d{1,2}(?::\d{2})?\s*(am|pm)\b', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip(" ,.")
        return text

    def _extract_due_datetime(self, command: str):
        now = datetime.datetime.now()
        date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', command)
        time_match = re.search(r'\b(\d{1,2}:\d{2})\b', command)

        # match times like '2pm' or '2:30 am'
        ampm_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", command, flags=re.IGNORECASE)

        if "tomorrow" in command:
            base_date = now.date() + datetime.timedelta(days=1)
        elif date_match:
            base_date = datetime.date.fromisoformat(date_match.group(1))
        else:
            base_date = now.date()

        if time_match:
            hour, minute = map(int, time_match.group(1).split(":"))
            return datetime.datetime.combine(base_date, datetime.time(hour=hour, minute=minute))

        if ampm_match:
            hour = int(ampm_match.group(1))
            minute = int(ampm_match.group(2)) if ampm_match.group(2) else 0
            ampm = ampm_match.group(3).lower()
            if ampm == 'pm' and hour != 12:
                hour += 12
            if ampm == 'am' and hour == 12:
                hour = 0
            return datetime.datetime.combine(base_date, datetime.time(hour=hour, minute=minute))

        if "morning" in command:
            return datetime.datetime.combine(base_date, datetime.time(hour=9, minute=0))
        if "afternoon" in command:
            return datetime.datetime.combine(base_date, datetime.time(hour=14, minute=0))
        if "evening" in command:
            return datetime.datetime.combine(base_date, datetime.time(hour=18, minute=0))

        return None

    def _load_json(self, path: str) -> list:
        os.makedirs("data", exist_ok=True)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return []

    def _save_json(self, path: str, data: list):
        os.makedirs("data", exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
