# Retail Multi-Agent System

This project implements a multi-agent system for retail management, featuring a Laravel-based Admin Portal and a Python-based backend powered by LLMs.

## 📋 Prerequisites

Before setting up the project, ensure you have the following ready:

### Environment & Software
* **Docker:** Required for running the Admin Portal (Web Server, MySQL, Laravel).
* **Linux VM or WSL (Windows Subsystem for Linux):** Required for hosting the vLLM (Language Model), as vLLM currently supports Linux environments only.

### API Keys & Accounts
* **LangSmith Account:** Required for agent tracing and evaluation.
    * [Sign up here](https://smith.langchain.com/) to get your API Key.
* **Google Gemini API Key:** Required for the LLM Judge agent evaluation.
    * [Get your key here](https://aistudio.google.com/app/apikey).

---

## ⚙️ Setup & Installation

### 1. LLM Hosting (vLLM)
You must set up the vLLM server to host the language model.
* **Note:** If you are on Windows, you must use **Docker** or **WSL**.
* Follow the official quickstart guide to get the server running: [vLLM Quickstart](https://docs.vllm.ai/en/latest/getting_started/quickstart.html#offline-batched-inference).

### 2. Multi-Agent Backend (`./multi-agent/`)

#### Configuration
1.  **API Keys Configuration:**
    Open `env` and set your Gemini & LangSmith API key:
    ```python
    LANGSMITH_API_KEY='......'
    GEMINI_API_KEY='......'
    ```

2.  **vLLM Connection:**
    In `retail_multi_agent_and_fast_api.py`, configure the IP address of your vLLM host:
    ```python
    # Replace ADDRESS_HERE and PORT_NUMBER with your specific details
    client = OpenAI(base_url="http://ADDRESS_HERE:PORT_NUMBER/v1", api_key="not-needed")
    ```

3.  **Gemini API Key:**
    Open (or create) the `.env` file in the directory and add your Google Gemini key:
    ```env
    GEMINI_API_KEY=PUT_YOUR_GEMINI_KEY_HERE
    ```

#### Running the Agent API
Start the API endpoint using Uvicorn:
```bash
uvicorn retail_multi_agent_and_fast_api:app --reload --port 8181
```

#### Agent Evaluation

To run the evaluation notebooks:

1. Open `agent_evalution.ipynb`.
2. Update the vLLM client configuration matches your hosting setup:
```python
client = OpenAI(base_url="http://ADDRESS_HERE:PORT_NUMBER/v1", api_key="not-needed")

```

### 3. Admin Portal (`./ui/`)

The admin portal is a Laravel application running on Docker.

1. **Launch Docker:**
Navigate to `./ui` (relevant Docker files are located in `./ui/docker` and `./ui`) and start your container.
2. **Database Setup:**
* Create a new MySQL database named `retail`.
* Import the SQL dump file located at `./multi-agent/inventory_dump_latest.sql` into the `retail` database.


3. **Access the Portal:**
Once the container is running and the database is imported, open your browser and navigate to:
[http://localhost:8080](http://localhost:8080)

---

## 📂 Project Structure

* **`/multi-agent`**: Contains Python scripts for agents, FastAPI implementation, evaluation notebooks, and database dumps.
* **`/ui`**: Contains the Laravel source code for the Admin Portal.
* **`/ui/docker`**: Docker configuration files for the web server and database.
* **`/pre_project_backup`**: Previous files that were used for development and exploration on multi-agent and small language model's domain