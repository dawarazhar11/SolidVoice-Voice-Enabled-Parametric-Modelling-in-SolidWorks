# SolidWorks Sketch Automation – Voice-Enabled with Claude AI

Voice-controlled SolidWorks sketch automation powered by **Anthropic Claude**, **local Whisper STT**, and a **vector memory graph** (Qdrant + Nomic embeddings via Ollama) that gives each part persistent, context-aware history.

## What it does

1. **Listen** – captures voice commands via microphone, transcribed locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (no audio leaves your machine).
2. **Understand** – Claude interprets the command and routes it to the correct SolidWorks operation.
3. **Execute** – creates sketches, extrudes, fillets, chamfers, patterns, mirrors, and exports via the SolidWorks COM API (pywin32 / pySldWrap).
4. **Label** – Claude generates a descriptive feature-tree label for every operation (e.g. *"Base Plate Sketch"*, *"Main Body Extrude"*) and renames the feature in SolidWorks.
5. **Remember** – every operation is embedded with [nomic-embed-text](https://ollama.com/library/nomic-embed-text) (running locally in Ollama) and stored in [Qdrant](https://qdrant.tech/). When the user issues a new command, the most relevant past operations are retrieved and injected into the Claude prompt so the AI is fully context-aware of what the part looks like.

## Architecture

```
Microphone
    │
    ▼
faster-whisper (local STT)
    │
    ▼
Claude API  ◄──── part history from Qdrant (semantic search)
(Anthropic / sub2api)          ▲
    │                          │
    ├─ route command           │
    ├─ generate feature label  │
    ▼                          │
SolidWorks COM API             │
(pySldWrap / pywin32)          │
    │                          │
    └─ record operation ──────►│
       (nomic-embed-text       │
        via Ollama → Qdrant)   │
```

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| SolidWorks | 2020 – 2025 | Set version in `config.ini` |
| Python | 3.10+ | |
| Anthropic API key | — | Or use [sub2api](https://github.com/Wei-Shaw/sub2api) proxy |
| Ollama | latest | `ollama pull nomic-embed-text` |
| Qdrant | latest | `docker run -p 6333:6333 qdrant/qdrant` |

## Installation

```bash
# Clone
git clone https://github.com/dawarazhar11/chatgpt-solidworks-sketch-automation-voice-enabled.git
cd chatgpt-solidworks-sketch-automation-voice-enabled

# Install Python dependencies
pip install -r requirements.txt

# Start Qdrant (vector database)
docker run -d -p 6333:6333 qdrant/qdrant

# Pull the embedding model into Ollama
ollama pull nomic-embed-text

# Configure
# Edit config.ini with your Anthropic API key (or sub2api base URL)
```

## Configuration (`config.ini`)

```ini
[ANTHROPIC]
API_KEY = sk-ant-...
# Optional: proxy URL for sub2api or similar gateway
BASE_URL =
# Claude model (claude-sonnet-4-20250514, claude-opus-4-20250514, etc.)
MODEL = claude-sonnet-4-20250514

[SOLIDWORKS]
VERSION = 2025

[WHISPER]
# Local model size: tiny | base | small | medium | large-v3
MODEL_SIZE = base

[QDRANT]
URL = http://localhost:6333

[OLLAMA]
URL = http://localhost:11434
```

### Using sub2api

If you use [sub2api](https://github.com/Wei-Shaw/sub2api) to proxy Claude through a subscription gateway, set:

```ini
BASE_URL = http://your-sub2api-server:8080/antigravity
API_KEY = your-sub2api-key
```

The Anthropic SDK will route all requests through the proxy automatically.

## Usage

```bash
# Make sure SolidWorks is open, then:
python solidworks_sketch.py
```

### Supported voice commands

| Command | Action |
|---------|--------|
| *"draw a rectangle"* | Create a rectangle sketch |
| *"create a circle 5cm radius"* | Create a circle sketch with parameters |
| *"draw a line from 0,0 to 10,10"* | Create a line sketch |
| *"extrude 10 millimetres"* | Boss-extrude the current sketch |
| *"add a fillet"* | Fillet selected edges |
| *"chamfer 2mm"* | Chamfer selected edges |
| *"mirror about the right plane"* | Mirror features |
| *"create a pattern, 5 copies, 20mm spacing"* | Linear pattern |
| *"add dimensions"* | Modify sketch dimensions via voice |
| *"export to STEP"* | Export the model |
| *"what have I done so far"* | Recall part history from memory |
| *"quit"* | Exit the program |

## Part Memory System

Each part gets its own Qdrant collection. Every feature operation is:

1. **Embedded** using `nomic-embed-text` (768-dimensional vectors) running locally in Ollama
2. **Stored** in Qdrant with a payload containing: feature type, AI-generated label, original voice command, parameters, and timestamp
3. **Retrieved** via semantic search when a new command arrives, so Claude understands the full build history of the part

This means you can say things like *"make the base plate thicker"* and Claude will know which extrude operation created the base plate, what its current depth is, and how to modify it.

### Memory payload structure

```json
{
  "feature_type": "extrude",
  "label": "Main Body Extrude",
  "user_intent": "extrude it by 10 millimetres",
  "parameters": {"depth": 0.01},
  "timestamp": "2025-01-15T10:30:00Z",
  "description": "extrude: Main Body Extrude. Intent: extrude it by 10 millimetres. Params: {'depth': 0.01}"
}
```

## Project Structure

```
├── solidworks_sketch.py   # Main application (voice loop, Claude, SolidWorks)
├── part_memory.py         # Vector memory module (Qdrant + Ollama/Nomic)
├── pySldWrap/
│   ├── __init__.py
│   └── sw_tools.py        # SolidWorks COM API wrapper (SW2012–SW2025)
├── config.ini             # Configuration (API keys, model, SW version)
├── requirements.txt       # Python dependencies
└── README.md
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `anthropic` | Claude API client |
| `faster-whisper` | Local Whisper STT (CTranslate2) |
| `qdrant-client` | Vector database client |
| `httpx` | HTTP client for Ollama embedding API |
| `pywin32` | Windows COM interface for SolidWorks |
| `SpeechRecognition` | Microphone audio capture |
| `PyAudio` | Audio I/O |

## License

MIT License. See [LICENSE](LICENSE) for details.
