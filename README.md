# J.A.R.V.I.S — Personal AI Assistant
### Just A Rather Very Intelligent System | Built by Praneeth

---

## What This Does

A fully local, voice-controlled AI assistant that:
- Wakes up when you say **"JARVIS"**
- Recognises your **face** before granting access
- Listens to your **voice commands**
- Responds intelligently via **OpenAI**
- Controls your **music, weather, news, calendar, system**, and more
- Helps you **study** and tracks your **personal analytics**

---

## Project Structure

```
jarvis/
├── main.py                  ← Entry point (run this)
├── config.json              ← Your API keys and settings
├── requirements.txt         ← All pip dependencies
│
├── core/                    ← Core engine
│   ├── voice.py             ← STT + TTS (mic in, speaker out)
│   ├── brain.py             ← OpenAI API — AI conversation
│   ├── wake_word.py         ← "JARVIS" wake word detector
│   ├── face_auth.py         ← OpenCV face recognition gate
│   ├── router.py            ← Routes commands to skills
│   └── config.py            ← Config loader + logger
│
├── skills/                  ← Plug-in skill modules
│   ├── weather.py           ← OpenWeatherMap live weather
│   ├── news.py              ← NewsAPI top headlines
│   ├── calendar_skill.py    ← Events and reminders
│   ├── music.py             ← Spotify playback control
│   ├── search.py            ← DuckDuckGo web search
│   ├── system.py            ← Volume, apps, shutdown, stats
│   ├── notes.py             ← Voice-dictated notes
│   ├── analytics.py         ← Personal usage analytics
│   └── study.py             ← Study buddy (OpenAI-powered)
│
└── data/                    ← Auto-created at runtime
    ├── notes.json
    ├── analytics.json
    ├── local_events.json
    ├── face_encodings.npy
    └── jarvis.log
```

---

## Setup Guide (Step by Step)

### Step 1 — Prerequisites

- Python 3.11 or higher
- A working microphone and speakers

### Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

> Windows users: if `pyaudio` fails:
> ```
> pip install pipwin
> pipwin install pyaudio
> ```

### Step 3 — Get API Keys (all free)

| Service | Key Needed | Where to Get |
|---|---|---|
| OpenAI (brain) | `openai_api_key` | platform.openai.com/api-keys |
| Weather | `openweather_api_key` | openweathermap.org/api |
| News | `newsapi_key` | newsapi.org |
| Spotify | `client_id` + `client_secret` | developer.spotify.com |

### Step 4 — Edit config.json

Open `config.json` and add your local API keys, or set them through environment variables before running JARVIS. Keep secrets out of version control and change `city` to your city.

### Step 5 — Enroll Your Face (Optional)

```python
# Run this ONCE to register your face with JARVIS
from core.face_auth import FaceAuth
auth = FaceAuth()
auth.enroll("Praneeth")   # looks at your webcam for ~3 seconds
```

Then set `"face_auth_enabled": true` in `config.json`.

### Step 6 — Run JARVIS

```bash
cd jarvis
python main.py
```

---

## Voice Commands Reference

| What to Say | What Happens |
|---|---|
| `JARVIS` | Wake word — activates listening |
| `What's the weather?` | Live weather for your city |
| `Read me the news` | Top 5 tech headlines |
| `Play Believer by Imagine Dragons` | Spotify search + play |
| `Pause music` / `Next song` | Spotify playback control |
| `Add event team meeting on 2025-06-15 at 10:00` | Saves to calendar |
| `What's on my calendar?` | Lists upcoming events |
| `Take note: buy groceries tomorrow` | Saves timestamped note |
| `Show my notes` | Reads recent notes |
| `Open Chrome` / `Take screenshot` | System control |
| `Volume up` / `Volume down` | OS audio control |
| `Battery status` / `CPU usage` | System stats |
| `Search for quantum computing` | DuckDuckGo search |
| `Explain backpropagation` | OpenAI explains the topic |
| `Quiz me on neural networks` | Generates 3 quiz questions |
| `My analytics` | Shows daily usage stats |
| `Clear memory` | Resets conversation history |
| `Shutdown JARVIS` / `Exit` | Closes the program |

---

## Build Phases

| Phase | What to Build | Time |
|---|---|---|
| **1** | voice loop + OpenAI brain (main.py, voice.py, brain.py) | 1–2 days |
| **2** | weather + news + notes + search skills | 2–3 days |
| **3** | system control + Spotify + calendar | 2–3 days |
| **4** | GUI (PyQt6 animated orb interface) | 3–4 days |
| **5** | face recognition + wake word (Porcupine) | 2–3 days |
| **6** | analytics dashboard + study mode polish | 2–3 days |

---

## Upgrading for Portfolio Impact

| Upgrade | How |
|---|---|
| Natural voice | Replace pyttsx3 with ElevenLabs API |
| Offline STT | Replace Google STT with `openai-whisper` |
| Better wake word | Use Porcupine (`pvporcupine`) |
| GUI | Build PyQt6 interface with animated orb |
| PDF study | Add PyMuPDF to summarise your lecture notes |
| IoT control | Add MQTT for smart home integration |
| Gesture unlock | Integrate your MediaPipe gesture project |
