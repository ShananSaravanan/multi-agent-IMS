# Retail Multi-Agent IMS — Setup Guide

> Tested on Windows 11 + WSL2 (Ubuntu 24), NVIDIA GPU (8GB VRAM minimum), Docker Desktop.

---

## What Runs Where

| Component | Where |
|---|---|
| Laravel Admin UI + MySQL | Docker Desktop (Windows) |
| FastAPI Multi-Agent Backend | WSL2 (Ubuntu) |
| LLM Server (llama-cpp) | WSL2 (Ubuntu) |
| Browser | Windows |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Windows 10/11 | WSL2 must be enabled |
| NVIDIA GPU | 8GB VRAM minimum |
| Docker Desktop | With WSL2 backend enabled |
| 30GB free disk space | Preferably on a non-OS drive (e.g. D:\) |
| HuggingFace account | Free — for downloading the model |

---

## Step 1 — Install WSL2

Open **PowerShell as Administrator**:

```powershell
wsl --install
```

Restart your PC. Open **Ubuntu** from the Start Menu and set your username/password when prompted.

---

## Step 2 — Install Miniconda in WSL2

Inside the Ubuntu terminal:

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# Accept all prompts, say yes to init
source ~/.bashrc
```

---

## Step 3 — Clone the Repo & Create Conda Environment

```bash
git clone https://github.com/ShananSaravanan/multi-agent-IMS.git
cd multi-agent-IMS

conda create -n retail_agent python=3.12 -y
conda activate retail_agent
```

---

## Step 4 — Install PyTorch with CUDA

Verify your GPU is visible first:

```bash
nvidia-smi
# Should show your GPU and CUDA version
```

Install PyTorch:

```bash
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 \
  --index-url https://download.pytorch.org/whl/cu121 --no-cache-dir
```

> If no GPU, omit `--index-url` to install the CPU-only version.

---

## Step 5 — Install Python Dependencies

```bash
pip install -r requirements.txt --no-cache-dir
```

---

## Step 6 — Install llama-cpp-python (LLM Server)

Install build tools first:

```bash
sudo apt update && sudo apt install -y gcc g++ cmake build-essential nvidia-cuda-toolkit
```

Install llama-cpp with CUDA support:

```bash
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python[server] --no-cache-dir
```

---

## Step 7 — Download the LLM Model

Login to HuggingFace (get your token at https://huggingface.co/settings/tokens):

```bash
huggingface-cli login
```

Download the quantized model (~2.5GB):

```bash
huggingface-cli download Qwen/Qwen3-4B-GGUF \
  Qwen3-4B-Q4_K_M.gguf \
  --local-dir ~/models
```

---

## Step 8 — Configure the Python Backend

### 8a. Update the model name in the code

Open `multi-agent/retail_multi_agent_and_fast_api.py` (accessible via Windows File Explorer at `\\wsl$\Ubuntu\home\<username>\multi-agent-IMS\multi-agent`).

Find **every line** with `model="Qwen/Qwen3-4B"` and replace with:

```python
model="/home/<your_username>/models/Qwen3-4B-Q4_K_M.gguf"
```

Or run this in WSL2 to do it automatically (replace `shanan03` with your username):

```bash
sed -i 's|model="Qwen/Qwen3-4B"|model="/home/shanan03/models/Qwen3-4B-Q4_K_M.gguf"|g' \
  ~/multi-agent-IMS/multi-agent/retail_multi_agent_and_fast_api.py
```

### 8b. Reduce max_tokens to avoid context length errors

Find all occurrences of `max_tokens = 4000` and change to:

```python
max_tokens = 1024
```

Or run:

```bash
sed -i 's/max_tokens = 4000/max_tokens = 1024/g' \
  ~/multi-agent-IMS/multi-agent/retail_multi_agent_and_fast_api.py
```

### 8c. Ensure load_dotenv import exists

Check the first line of `retail_multi_agent_and_fast_api.py`. If `from dotenv import load_dotenv` is missing, add it:

```bash
sed -i '1s/^/from dotenv import load_dotenv\n/' \
  ~/multi-agent-IMS/multi-agent/retail_multi_agent_and_fast_api.py
```

---

## Step 9 — Set Up Docker (Laravel + MySQL)

1. Open **Docker Desktop** on Windows
2. Go to **Settings → Resources → WSL Integration** → Enable for **Ubuntu** → Apply & Restart
3. In Ubuntu terminal:

```bash
cd ~/multi-agent-IMS/ui
docker compose up -d
```

4. Install Laravel dependencies inside the container:

```bash
docker exec -it retail_app composer install
```

---

## Step 10 — Seed the Database

> Docker containers must be running before this step.

```bash
conda activate retail_agent
cd ~/multi-agent-IMS/multi-agent
python seed_wire_harness.py
```

This creates the database schema and populates it with sample data. Only needs to be run once.

---

## Step 11 — Running the Full System

You need **3 terminals** open simultaneously. Always run `conda activate retail_agent` first in each.

### Terminal 1 — LLM Server

```bash
conda activate retail_agent
python -m llama_cpp.server \
  --model ~/models/Qwen3-4B-Q4_K_M.gguf \
  --n_gpu_layers 35 \
  --port 8000 \
  --n_ctx 8192
```

Wait until you see:
```
INFO:     Uvicorn running on http://localhost:8000
```

### Terminal 2 — FastAPI Multi-Agent Backend

```bash
conda activate retail_agent
cd ~/multi-agent-IMS/multi-agent
uvicorn retail_multi_agent_and_fast_api:app --reload --port 8181
```

Wait until you see:
```
Application startup complete.
```

### Terminal 3 — Docker (if not already running)

```bash
cd ~/multi-agent-IMS/ui
docker compose up -d
```

---

## Step 12 — Access the App

Open your browser on Windows:

| Service | URL |
|---|---|
| Laravel Admin Portal | http://localhost:8080 |
| FastAPI API Docs | http://localhost:8181/docs |
| LLM Server | http://localhost:8000/v1/models |

---

## After Every Reboot

Docker and WSL2 don't auto-start. After every reboot:

1. Open Docker Desktop on Windows and wait for it to fully start
2. Open Ubuntu terminal and run:

```bash
conda activate retail_agent

# Start LLM server (Terminal 1)
python -m llama_cpp.server \
  --model ~/models/Qwen3-4B-Q4_K_M.gguf \
  --n_gpu_layers 35 \
  --port 8000 \
  --n_ctx 8192
```

```bash
# Start FastAPI backend (Terminal 2)
conda activate retail_agent
cd ~/multi-agent-IMS/multi-agent
uvicorn retail_multi_agent_and_fast_api:app --reload --port 8181
```

```bash
# Start Docker containers (Terminal 3)
cd ~/multi-agent-IMS/ui
docker compose up -d
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` on any import | Make sure `conda activate retail_agent` was run first |
| `context_length_exceeded` error | Find all `max_tokens = 4000` in the Python file and change to `max_tokens = 1024` |
| LLM server OOM / no cache blocks | Reduce `--n_ctx` to 4096 |
| Docker: permission denied | Enable WSL2 integration in Docker Desktop → Settings → Resources → WSL Integration |
| Laravel blank page | Run `docker exec -it retail_app composer install` |
| `load_dotenv` not defined | Add `from dotenv import load_dotenv` as the first line of `retail_multi_agent_and_fast_api.py` |
| Tool calls returned as raw text | The `try_parse_tool_calls` function handles this — make sure you're using the updated version of the file |
| `tool_call_id` 500 error | Ensure both `ToolMessage` conversion blocks in the Python file include `"tool_call_id": getattr(msg, 'tool_call_id', None) or msg.name` |
| `seed_wire_harness.py` fails | Make sure Docker containers are running first (`docker compose up -d`) |

---

## System Architecture

```
Browser
  ↓
Nginx (Docker :8080)
  ↓
Laravel Admin UI ←→ MySQL (Docker)
  ↓ SSE stream
FastAPI :8181
  ↓
LangGraph Multi-Agent System
  ├── Supervisor Agent
  ├── Inventory Management Agent
  ├── Sales Analyst Agent
  └── SQL Agent (queries MySQL directly)
  ↓ inference
llama-cpp LLM Server :8000
(Qwen3-4B-Q4_K_M.gguf)
```

LangSmith traces all agent interactions (optional — lines are commented out by default).
Gemini is used as a judge model for response evaluation (configured via GEMINI_API_KEY if needed).