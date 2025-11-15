# AI Coder Agent

A local AI coding assistant powered by LLM running via Ollama in Google Colab.

## Features

- 📝 Read and write files
- 🔍 Search code across files
- 💻 Execute bash commands
- 📁 Navigate directories
- 🤖 Natural language interaction
- 💬 Conversation history

## Quick Start

### Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   Local PC      │         │  Google Colab    │
│                 │         │                  │
│  local_agent.py │◄───────►│ colab_server.py  │
│  (Tools/CLI)    │  HTTP   │  (LLM Brain)     │
│                 │  ngrok  │  + Ollama        │
└─────────────────┘         └──────────────────┘
```

### Setup Steps

**1. In Google Colab:**

```python
# Run your existing Cell 1 & 2 to setup Ollama and download model

# Then add this cell to start the server:
!pip install -q flask pyngrok

# Upload colab_server.py
from google.colab import files
files.upload()

# Start the server
from pyngrok import ngrok
import threading
from colab_server import app

def run_flask():
    app.run(host='0.0.0.0', port=5000, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()
import time; time.sleep(3)

public_url = ngrok.connect(5000)
print(f"🌐 Server URL: {public_url}")
print(f"Copy this URL and use it on your local PC!")

# Keep running
while True:
    time.sleep(1)
```

**2. On Your Local PC:**

```bash
# Install requirements
pip install requests

# Run the agent
python local_agent.py https://xxxx.ngrok.io

# Or just run and paste URL when prompted
python local_agent.py
```

That's it! The agent runs on your PC with all file access, but the LLM runs in Colab with GPU.

## Architecture

```
ai_coder_agent.py   - Core data structures and file system tools
agent_core.py       - Main agent logic and LLM interaction
run_agent.py        - CLI interface for the agent
colab_setup.ipynb   - Complete Colab setup notebook
```

## How It Works

1. User sends a message
2. Agent processes it with the LLM
3. If LLM wants to use a tool, it outputs JSON
4. Agent executes the tool and feeds result back to LLM
5. LLM provides final response to user

## Available Tools

- `read_file` - Read file contents
- `write_file` - Create or update files
- `list_directory` - Show directory contents
- `execute_bash` - Run bash commands
- `search_code` - Search for patterns in code

## Future Enhancements

- [ ] Multi-file editing
- [ ] Git integration
- [ ] Code analysis and linting
- [ ] Test generation
- [ ] Debugging assistance
- [ ] Project scaffolding
- [ ] API integration
- [ ] Web search capability
- [ ] Better error handling
- [ ] Syntax highlighting
- [ ] Code completion suggestions

## Example Usage

```
You: Create a simple Flask web server in app.py