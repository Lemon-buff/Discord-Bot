# 🎧 Burmese Discord Music Bot

A Discord music bot with **fully Burmese voice commands**, built for simplicity, reliability, and fun.  
The bot can **join your voice channel**, **search and play YouTube music**, manage a **song queue**, and **continue playing automatically** — all while responding in Burmese.

---

##  Features

###  Current Features
- **Burmese Command System** (`!ဖွင့်`, `!ဝင်`, `!ထွက်`, etc.)
- **YouTube Music Playback** (Search text or paste URL)
- **Queue Support** (New songs are added and auto-play continues)
- **Auto Next Song Logic** (No need to repeat commands)
- **Resilient Voice Connection** with retry and reconnect logic
- **Per-server Music State** (Each server has its own queue and player state)

### 🎧 Playback UI
- Custom **Burmese embed messages**
- Now Playing display with:
  - Song title
  - Thumbnail
  - Requested-by attribution

---

## 🗂 Commands 

| Command | Aliases | Usage | Description |
|--------|---------|-------|-------------|
| `!ဝင်` | `!j` | `!ဝင်` | Bot joins your current voice channel |
| `!ထွက်` | `!l` | `!ထွက်` | Bot leaves the voice channel + clears queue |
| `!ဖွင့် <သီချင်း>` | `!p`, `!phwint` | Search / play / resume music |
| *(Auto)* | — | — | When a song finishes, the next one plays automatically |

---

## 🧰 Tech Stack

| Layer | Technology |
|------|------------|
| Bot Framework | **discord.py** |
| Audio Fetching | **yt-dlp** |
| Streaming | **FFmpeg** |
| Language | Python 3.10+ |

---
git clone https://github.com/<your-username>/<your-repository>.git
cd <your-repository>
