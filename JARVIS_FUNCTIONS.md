# 📋 JARVIS Complete Function & Method Inventory

**Generated on**: May 11, 2026  
**Version**: 1.0  
**Project**: JARVIS Personal Assistant  

---

## Table of Contents

1. [main.py](#mainpy)
2. [core/brain.py](#corebrainpy)
3. [core/config.py](#coreconfigpy)
4. [core/logger.py](#coreloggerpy)
5. [core/voice.py](#corevoicepy)
6. [core/router.py](#corerouterpy)
7. [core/wake_word.py](#corewake_wordpy)
8. [core/face_auth.py](#coreface_authpy)
9. [skills/weather.py](#skillsweatherpy)
10. [skills/news.py](#skillsnewspy)
11. [skills/notes.py](#skillsnotespy)
12. [skills/personal.py](#skillspersonalpy)
13. [skills/study.py](#skillsstudypy)
14. [skills/analytics.py](#skillsanalyticspy)
15. [Summary Statistics](#summary-statistics)

---

## main.py

**Purpose**: Main entry point and orchestrator for JARVIS personal assistant system.

### JARVIS Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | None | None | Initializes all JARVIS subsystems: voice engine, brain, wake-word detector, face authentication, skills registry, and command router |
| `run()` | None | None | Main event loop that: checks due reminders, listens for wake word, verifies face auth (if enabled), processes commands, and speaks responses |

---

## core/brain.py

**Purpose**: Conversational AI engine with local fallback (OpenAI removed).

### Brain Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | None | None | Initializes conversation history (max 20 messages) and logger instance |
| `think()` | `user_input: str`<br>`context: str = ""` | `str` | Main conversational interface; appends user message to history, generates local reply based on keywords |
| `_local_reply()` | `user_input: str`<br>`context: str = ""` | `str` | Generates contextual conversational replies using keyword matching; returns fallback responses when no context available |
| `study()` | `topic: str`<br>`depth: str = "explain"` | `str` | Generates study content (explanation, summary, or quiz) from internal knowledge bank (used by StudySkill) |
| `clear_memory()` | None | None | Clears conversation history and logs the memory clear event |

---

## core/config.py

**Purpose**: Configuration management - loads settings from config.json and environment variables.

### Module-Level Functions

| Function | Parameters | Return Type | Description |
|----------|------------|-------------|-------------|
| `_load_config()` | None | `dict` | Loads configuration from `config.json`, merges with hardcoded defaults, applies environment variable overrides for API keys |

### Module-Level Variables

| Variable | Type | Description |
|----------|------|-------------|
| `CONFIG` | `dict` | Global configuration dictionary containing all JARVIS settings (voice, stt/tts backends, API keys, city, user name, etc.) |

---

## core/logger.py

**Purpose**: Global logging configuration.

### Module-Level Variables

| Variable | Type | Description |
|----------|------|-------------|
| `log` | `logging.Logger` | Global logger instance configured with console and file handlers; used throughout JARVIS codebase for debug/info/error messages |

---

## core/voice.py

**Purpose**: Speech-to-Text (STT) and Text-to-Speech (TTS) engine.

### VoiceEngine Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | None | None | Initializes pyttsx3 TTS engine with voice configuration, initializes SpeechRecognition with microphone/audio setup, handles fallback to typed input |
| `_configure_tts()` | None | None | Configures TTS voice selection (female eSpeak variant "gmw/en-us+f3"), speech rate (160 wpm), and volume (1.0) |
| `speak()` | `text: str` | None | Converts text to speech synchronously (blocking) via pyttsx3 with configured voice settings |
| `speak_async()` | `text: str` | None | Non-blocking text-to-speech; runs TTS in separate daemon thread |
| `listen()` | `timeout: int = 10`<br>`phrase_limit: int = 15` | `str \| None` | Captures microphone input (or falls back to typed input) and returns transcribed text in lowercase; returns None if failed |
| `_google_recognise()` | `audio` | `str \| None` | Uses Google Speech Recognition API to transcribe audio data (requires internet) |
| `_whisper_recognise()` | `audio` | `str \| None` | Uses offline OpenAI Whisper model for speech-to-text (local, no internet required) |

---

## core/router.py

**Purpose**: Command routing - matches user commands to appropriate skills or fallback to brain.

### CommandRouter Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | `skills: list`<br>`brain` | None | Initializes router with skill instances and brain; caches analytics skill reference for logging |
| `handle()` | `command: str` | `str` | Routes command to appropriate skill or brain fallback; handles special built-in commands (exit, time, date) first |
| `_match_skill()` | `command: str` | `Skill instance \| None` | Finds highest-priority skill matching the command using scoring algorithm; returns skill or None |
| `_score()` | `command: str`<br>`triggers: list[str]` | `int` | Scores command match against skill triggers using regex word boundary matching; higher score = better match |

---

## core/wake_word.py

**Purpose**: Wake word detection - detects "jarvis" keyword to activate listening.

### WakeWordDetector Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | `keyword: str = "jarvis"` | None | Initializes wake-word detector with chosen backend (Porcupine/SpeechRecognition/Typed); attempts Porcupine first, falls back to SR, then typed |
| `listen()` | None | None | Blocks until wake word is detected; calls appropriate backend listener method |
| `_init_porcupine()` | None | None | Initializes Porcupine wake-word engine; falls back to SR backend if Porcupine unavailable or license missing |
| `_init_sr_backend()` | None | None | Initializes SpeechRecognition backend with microphone for wake-word detection |
| `_listen_porcupine()` | None | None | Continuously processes audio frames using Porcupine wake-word engine until keyword detected |
| `_listen_sr()` | None | None | Processes short audio chunks (3-5 sec) to detect keyword via Google STT or falls back to typed input |
| `_listen_typed()` | None | None | Fallback typed input mode for wake-word detection; reads user input from keyboard |

---

## core/face_auth.py

**Purpose**: Face authentication - optional biometric verification on startup.

### FaceAuth Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | None | None | Initializes face authentication; loads saved face encodings if enabled in config, otherwise disables auth |
| `verify()` | None | `bool` | Attempts real-time face recognition via webcam; returns True if user recognized or auth disabled in config |
| `enroll()` | `name: str`<br>`num_samples: int = 20` | None | Captures 20 face images from webcam and saves face encodings for user registration |
| `_save_encodings()` | None | None | Saves face encodings and person names to `.npy` binary files in data/ directory |
| `_load_encodings()` | None | None | Loads previously saved face encodings and names from `.npy` files in data/ directory |

---

## skills/weather.py

**Purpose**: Weather information retrieval via OpenWeatherMap API.

### WeatherSkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `handle()` | `command: str` | `str` | Fetches live weather from OpenWeatherMap API for configured city and returns formatted weather report (temperature, conditions, humidity, wind) |

---

## skills/news.py

**Purpose**: Multi-skill module for calendar, music, search, and system controls.

### NewsSkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `handle()` | `command: str` | `str` | Fetches top headlines from NewsAPI and returns formatted list with titles and summaries |

### CalendarSkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | None | None | Loads local calendar events from JSON file at initialization |
| `handle()` | `command: str` | `str` | Routes to `_add_event()` or `_list_events()` based on command keywords and context |
| `_list_events()` | None | `str` | Lists upcoming events from today onwards (max 5 events); shows date, time, and title |
| `_add_event()` | `command: str` | `str` | Parses command to extract event title, date/time; adds to calendar and saves to JSON |
| `_load_local()` | None | `list` | Loads events from local JSON file; creates empty list if file doesn't exist |
| `_save_local()` | None | None | Persists all events to local JSON file |

### MusicSkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | None | None | Initializes with lazy-loading for Spotify client (avoids blocking startup) |
| `_get_sp()` | None | `spotipy.Spotify \| None` | Lazy-initializes and returns Spotify client; requires valid API credentials |
| `handle()` | `command: str` | `str` | Executes Spotify playback commands: pause, next, previous, play, resume based on voice input |

### SearchSkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `handle()` | `command: str` | `str` | Performs DuckDuckGo web search; returns instant answer or opens search results in browser |

### SystemSkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `handle()` | `command: str` | `str` | Routes to appropriate system control method (volume, apps, shutdown, battery, stats) based on command keywords |
| `_screenshot()` | None | `str` | Takes screenshot via scrot/ImageGrab and saves with timestamp to data/ directory |
| `_volume()` | `delta: int`<br>`system: str` | `str` | Adjusts system volume up/down by delta percent; platform-specific (Windows/Linux/macOS) using pactl/osascript |
| `_mute()` | `system: str` | `str` | Toggles system mute state; platform-specific implementation |
| `_open_app()` | `command: str` | `str` | Opens applications or URLs based on command; supports app names (chrome, spotify, github, chatgpt) with fallback browser opening |
| `_shutdown()` | `system: str` | `str` | Triggers system shutdown after 5-second delay; platform-specific (uses shutdown/osascript) |
| `_restart()` | `system: str` | `str` | Triggers system restart after 5-second delay; platform-specific implementation |
| `_battery()` | None | `str` | Returns battery status (charging/discharging) and charge percentage via psutil |
| `_system_stats()` | None | `str` | Returns CPU usage, RAM usage, and available memory statistics |

---

## skills/notes.py

**Purpose**: Note-taking skill - create, list, search, and delete notes stored locally.

### NotesSkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | None | None | Loads existing notes from JSON file on initialization |
| `handle()` | `command: str` | `str` | Routes to add, list, search, or clear notes based on command keywords |
| `_save_note()` | `content: str` | `str` | Creates note object with unique ID and timestamp; saves to notes list and persists to file |
| `_list_notes()` | None | `str` | Returns formatted list of last 5 notes in reverse chronological order (newest first) |
| `_search_notes()` | `query: str` | `str` | Searches notes for keyword match; returns up to 5 matching notes with context |
| `_clear_notes()` | None | `str` | Deletes all notes and clears notes file |
| `_load()` | None | `list` | Loads notes from JSON file or returns empty list if file missing |
| `_save()` | None | None | Persists all notes to JSON file |

---

## skills/personal.py

**Purpose**: Personal assistant skill - reminders, daily schedule, user profile, and study help.

### PersonalAssistantSkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | None | None | Loads reminders and schedule from JSON files; initializes `_pending_reminder` state for multi-step reminder creation |
| `handle()` | `command: str` | `str` | Routes to reminders, schedule, profile, or features handlers; intercepts follow-up commands when pending reminder exists |
| `check_due_reminders()` | None | `list[str]` | Checks for overdue reminders and returns notification messages for reminders that should fire |
| `_features()` | None | `str` | Returns formatted list of available features (reminders, schedule, profiles, study help, daily plan) |
| `_profile()` | None | `str` | Returns user profile information (name, city, greeting message) |
| `_add_reminder()` | `command: str` | `str` | Parses reminder command, extracts due date/time, creates reminder entry; handles multi-step creation via pending state |
| `_list_reminders()` | None | `str` | Returns formatted list of active (non-completed) reminders with due dates/times (max 5) |
| `_clear_reminders()` | None | `str` | Deletes all reminders and clears reminders JSON file |
| `_add_schedule()` | `command: str` | `str` | Parses schedule command, extracts date/time, creates schedule item entry and saves |
| `_daily_plan()` | None | `str` | Returns combined view of today's schedule items and active reminders (user's daily plan) |
| `_extract_text()` | `command: str`<br>`prefixes: list[str]` | `str` | Extracts and cleans relevant content from command by removing common keywords and temporal references |
| `_extract_due_datetime()` | `command: str` | `datetime.datetime \| None` | Parses date/time expressions from command: specific dates, times with am/pm, relative references ("tomorrow", "next week"), month names |
| `_load_json()` | `path: str` | `list` | Loads JSON data from file; returns empty list if file missing |
| `_save_json()` | `path: str`<br>`data: list` | None | Persists data to JSON file with proper formatting |

**Special Instance Variable**:
- `_pending_reminder`: Dictionary tracking state across multi-step reminder creation (format: `{"due_at": datetime}`)

---

## skills/study.py

**Purpose**: Study assistant skill - quiz, explain, and summarize topics.

### StudySkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `handle()` | `command: str` | `str` | Determines study mode (quiz/explain/summarize from command), extracts topic, delegates to Brain.study() |
| `_extract_topic()` | `command: str`<br>`keywords: list` | `str` | Extracts topic by removing common study keywords from command text |

---

## skills/analytics.py

**Purpose**: Interaction analytics and logging - tracks command usage and skill routing patterns.

### AnalyticsSkill Class

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `__init__()` | None | None | Loads interaction logs from JSON file on initialization |
| `handle()` | `command: str` | `str` | Returns formatted analytics summary and usage statistics |
| `log_interaction()` | `command: str`<br>`response: str` | None | Records command execution with timestamp, detected skill, and response; saves every 10 entries to JSON |
| `_detect_skill()` | `command: str` | `str` | Identifies which skill handled the command using keyword matching |
| `_summary()` | None | `str` | Generates analytics report showing: today's interaction count, most-used skills, and usage patterns |
| `_load()` | None | `list` | Loads interaction logs from JSON or returns empty list |
| `_save()` | None | None | Persists last 1000 interaction records to JSON file |

---

## Summary Statistics

### Code Organization

| Metric | Count |
|--------|-------|
| **Python Files** | 20 |
| **Total Classes** | 15 |
| **Total Public Methods** | 70+ |
| **Module-Level Functions** | 2 |
| **Instance Variables** | 30+ |

### Class Breakdown

| Class | File | Purpose |
|-------|------|---------|
| **JARVIS** | main.py | Main orchestrator |
| **Brain** | core/brain.py | Conversational engine |
| **VoiceEngine** | core/voice.py | STT/TTS handler |
| **WakeWordDetector** | core/wake_word.py | Wake-word detection |
| **FaceAuth** | core/face_auth.py | Biometric auth |
| **CommandRouter** | core/router.py | Command routing |
| **WeatherSkill** | skills/weather.py | Weather info |
| **NewsSkill** | skills/news.py | News headlines |
| **CalendarSkill** | skills/news.py | Calendar events |
| **MusicSkill** | skills/news.py | Music playback |
| **SearchSkill** | skills/news.py | Web search |
| **SystemSkill** | skills/news.py | System controls |
| **NotesSkill** | skills/notes.py | Notes management |
| **PersonalAssistantSkill** | skills/personal.py | Reminders, schedule, profile |
| **AnalyticsSkill** | skills/analytics.py | Usage analytics |

### Key Features

- **15 Skill Classes** providing distinct capabilities
- **Multi-step Reminder Flow** with state tracking
- **Local-Only Operation** (OpenAI removed, no external AI APIs)
- **Typed I/O Mode** for keyboard input (no voice required)
- **JSON-Based Storage** for reminders, schedules, notes, events
- **Optional Face Authentication** for security
- **Platform-Independent** system controls (Windows/Linux/macOS)
- **Lazy Loading** for optional dependencies (Spotify, Porcupine)
- **Async TTS** for non-blocking speech output

---

**End of JARVIS Function Inventory**

*For updates or additions, edit this file or run the discovery process again.*
