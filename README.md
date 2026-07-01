# 🤖 DevOps Concierge Agent

An enterprise-grade, highly resilient AI DevOps automation platform. Scaffold projects, provision cloud infrastructure, deploy to Vercel, orchestrate Kafka pipelines, and generate consulting-grade documentation through natural conversation.

Developed as a state-of-the-art virtual engineer, this platform is structured as a **decoupled monorepo** — combining the simplicity of local development with the scalability of decoupled production services.

---

## 🌟 Advanced Enterprise Features

### 🔄 1. KeyOptimus API Key Router & Optimizer Microservice
*   **Independent Decoupled Microservice:** Runs on port `8005` in the same repo, serving as a smart, deterministic gateway. It uses **zero AI tokens** to make routing and optimization decisions.
*   **Capability-Aware Routing:** Automatically routes simple text tasks to basic keys (like Groq/OpenAI mini) and reserves premium keys (like Gemini) strictly for specialized tasks (image generation, multimodal vision, PDF/Office document reading).
*   **Wastage Prevention (Utility Preservation):** If a premium key's daily limit drops to **5 or fewer requests remaining**, KeyOptimus locks it out of simple text tasks, preserving it exclusively for image or video generation!
*   **Self-Healing Model Swapping:** If a model hits a 429 rate limit, KeyOptimus attempts to swap to an alternative model on the *same key* (e.g. `gemini-2.5-flash` -> `gemini-2.5-pro`) if it still has quota, preventing key rotation overhead.
*   **Excel Audit Logger:** Log every single request, latency, token count, and quarantine state automatically to a beautifully styled [api_key_metrics.xlsx](file:///c:/Users/HP/DevOps-Concierge-Agent/api_key_metrics.xlsx) sheet in your workspace.
*   **Self-Healing Quarantine:** Quarantines failing keys (e.g., 401 Unauthorized) globally for 5 minutes, allowing other concurrent chats to fail over seamlessly.

### 🌐 2. Unified Resource Reader & Authenticated Scraping
*   **Active Browser Profile Inheritance:** Read private URLs (like your private ChatGPT chats, private GitHub issues, or AWS dashboards). The agent scans your Windows machine for local **Google Chrome** or **Microsoft Edge** profiles.
*   **Zero-Downtime Profile Cloning:** To bypass browser file locks when Chrome/Edge is active, the agent instantly makes a lightweight clone (<15MB) of your profile, skipping heavy caches and media while preserving cookies and active logins. It launches a headless browser using Playwright to extract Javascript-rendered SPA chats!
*   **Multi-Format File Parser:** Pass absolute file paths directly to the agent. It natively parses:
    *   **Word (`.docx`)**: Extracts paragraphs and formats data tables.
    *   **PowerPoint (`.pptx`)**: Parses text slide-by-slide.
    *   **PDF (`.pdf`)**: Extracts text page-by-page.
    *   **Images & Configs**: Handles plain text configs (`.env`, `.json`, `.yml`) and extracts image metadata.

### 🔌 3. Automated Neon PostgreSQL + Vercel Deployment
*   **Zero-Touch Full Stack Deployments:** When you trigger a Vercel deployment, the agent checks if a `NEON_API_KEY` is configured.
*   **Instant Provisioning:** It automatically calls the Neon API to spin up an isolated serverless PostgreSQL database named after your project, extracts the connection string, and **injects it as `DATABASE_URL` directly into your Vercel project environment variables** (across Dev, Preview, and Production).

### 🛠️ 4. Local QLoRA Fine-Tuning Pipeline
*   **GPU-Accelerated Local Training:** Supports complete, offline fine-tuning of lightweight models (e.g., Qwen 2.5 Coder 1.5B/7B) on local hardware (e.g., NVIDIA Laptop GPU RTX 3050).
*   **Dynamic BFloat16 Precision:** Automatically detects GPU capabilities to run training using `bfloat16` precision, bypassing PyTorch's Automatic Mixed Precision (AMP) scaling overhead, maximizing throughput, and preventing out-of-memory crashes.
*   **Data Privacy:** Fine-tuned LoRA adapters are saved directly to your workspace, giving you complete data privacy and offline agent control.

### ⚡ 5. Concurrent ReAct Loop & Async Tool Orchestration
*   **Non-Blocking Parallel Execution:** Runs independent tools concurrently using asynchronous task gathering, keeping execution high-speed.
*   **UUID Call ID Mapping:** Dynamically tracks each tool call using a unique `call_id`, preventing frontend state race conditions and ensuring parallel tool cards update, succeed, or error out independently.

### 🔐 6. Secure Human-in-the-Loop Authorization Gateway
*   **Interactive Permission Gates:** Sensitive external actions (like running terminal commands or writing project files) are bound to a secure callback gateway.
*   **Direct Sync Approval:** Clicking **✓ Approve** or **✕ Deny** maps directly to the active `action_id`, instantly resuming execution or reporting the denial without long timeouts or safety bypasses.

### 📂 7. Workspace Isolation & Clean Project Scaffolding
*   **Preserved Directory Tree:** Safely redirects and isolates all generated code, assets, and configs into clean subdirectories within your designated projects folder (preserving complex structures like `src/app/page.jsx` instead of flattening them).
*   **Standalone IDE Workspaces:** Generates clean, isolated project roots that you can open directly in VS Code as a standalone workspace without cross-contaminating other projects.

### 🔌 8. Standard Agent Developer Skills & MCP Support
*   **Interactive Terminal Skill (`run_terminal_command`)**: The agent can run arbitrary build, test, or git commands locally. Protected by a **Human-in-the-loop approval gate** (requires your explicit click in the Chat UI).
*   **Workspace Access (`read_project_file` / `write_project_file`)**: Safe reading and approved writing of files within your designated project folders.
*   **Model Context Protocol (MCP)**: Out-of-the-box support for connecting standard stdio, SSE, or HTTP MCP servers as a client.
*   **Built-in Custom MCP Server**: The project exposes a zero-dependency Python stdio MCP server at `backend/agent/mcp_server.py`. It allows any external client (like Claude Desktop or another agent) to securely trigger non-authorizing skills:
    *   `check_credentials`: Returns configuration state of API keys without exposing secrets.
    *   `select_database`: Analyzes project requirements and recommends a database.
    *   **Run command**: `python backend/agent/mcp_server.py`

### 📲 9. Progressive Web App (PWA) & 100/100 SEO Scaffolding
*   **Native PWA Experience:** Desktop installable with an custom-designed high-res logo. Features **Windows Taskbar right-click shortcuts** ("New Chat", "Settings") and borderless standalone window mode.
*   **SEO Scaffolding Defaults:** Any website scaffolded by the agent automatically ships with a perfect 100/100 Lighthouse SEO architecture, including:
    *   Dynamic Next.js `sitemap.js` generators (serving fresh XML sitemaps).
    *   Robots crawling guidelines (`robots.txt`).
    *   JSON-LD Schema Markup components for Google Rich Results.
    *   Clean, semantic HTML5 structure.

---

## 🛠️ Tech Stack & Architecture

*   **Frontend:** Next.js 15 (App Router), React, Glassmorphic Vanilla CSS.
*   **Backend:** FastAPI (Python), Async HTTPX Streaming, Cryptography (Fernet symmetric encryption at rest for API keys).
*   **Database:** SQLite (local persistence) / Neon PostgreSQL (serverless production).
*   **AI Orchestration:** Google Gemini 2.5 (Flash/Pro), OpenAI (GPT-4o), Anthropic (Claude 3.5), Groq (Llama 3).

---

## 🚀 Quick Start

### 1. Install System Dependencies
Ensure you have Python 3.10+ and Node.js 18+ installed on your machine.

### 2. Install Project Dependencies
```bash
# Install backend Python requirements
pip install -r requirements.txt

# (Optional) Enable Playwright for authenticated browser scraping & PDF parsing
pip install playwright pypdf
playwright install chromium

# Install frontend Node dependencies
cd frontend
npm install
cd ..
```

### 3. Run the Platform
Double-click **`start.bat`** (or run it in your terminal) to boot the Next.js dev server (port 3000), the main FastAPI agent backend (port 8000), and the KeyOptimus Scheduler microservice (port 8005) simultaneously.

```bash
.\start.bat
```

### 4. Setup Your Credentials
Open the platform in your browser, click the **Settings icon (⚙️)** in the top-right corner, and configure your keys:
*   `GEMINI_API_KEY` (Primary)
*   `VERCEL_TOKEN` & `GITHUB_TOKEN` (For automated deployments)
*   `NEON_API_KEY` (For automated serverless database linking)
*   `API_KEYS_QUEUE` (Backup keys for failover load-balancing)

### 5. Connect Built-in MCP Server to Claude Desktop
You can expose the DevOps Concierge tools directly to external clients like Claude Desktop. Add the following block to your Claude Desktop configuration file (located at `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "devops-concierge": {
      "command": "python",
      "args": ["c:/Users/HP/DevOps-Concierge-Agent/backend/agent/mcp_server.py"]
    }
  }
}
```
