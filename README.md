# 🧠 VaultMind — Enterprise Knowledge Copilot

**AI-powered enterprise knowledge assistant** that answers questions from your company's internal documents with source citations, role-based access control, and multi-agent orchestration.

> 🔒 **Privacy First**: Your data stays on your servers. VaultMind supports fully local LLM deployment via Ollama — no data ever leaves your network.

---

## ✨ Features

- 🤖 **Multi-Agent Architecture** — Powered by LangGraph with specialized agents (Router, Retrieval, Synthesizer, Critique)
- 📄 **Document Intelligence** — Upload PDF, DOCX, Markdown, TXT files and ask questions in natural language
- 🔗 **Source Citations** — Every answer includes clickable references to the exact document and page
- 🔐 **Role-Based Access Control (RBAC)** — Different roles see different documents (Admin, Manager, HR, Employee, Guest)
- 🔀 **Hybrid LLM Strategy** — Use local Ollama (privacy) or cloud APIs (OpenAI, Azure) — your choice
- 🗄️ **Text-to-SQL Agent** — Query structured databases with natural language
- ⚡ **Real-time Streaming** — Watch the AI think, step by step, via Server-Sent Events
- 🌙 **Premium Dark UI** — Modern, responsive interface built with Next.js and Shadcn UI

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│                    Next.js Frontend                     │
│           Chat UI │ Doc Manager │ Agent Trace           │
└─────────────────────────┬──────────────────────────────┘
                          │ SSE / REST
┌─────────────────────────┴──────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │              LangGraph Multi-Agent               │   │
│  │  Router → RBAC → Retrieval → Synthesizer → Critique │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌───────────┐ ┌────────────────────┐     │
│  │ ChromaDB │ │PostgreSQL │ │ Ollama / Cloud LLM │     │
│  │ (Vector) │ │ (Meta)    │ │ (Hybrid)           │     │
│  └──────────┘ └───────────┘ └────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- [Ollama](https://ollama.ai/) with `qwen3.5:4b` and `nomic-embed-text` models

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env  # Edit .env with your settings
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 📁 Project Structure

```
VaultMind/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── config.py        # Configuration management
│   │   ├── llm/             # Hybrid LLM provider layer
│   │   ├── agents/          # LangGraph multi-agent system
│   │   ├── rag/             # Document processing & retrieval
│   │   ├── db/              # Database operations
│   │   └── api/             # REST API endpoints
│   ├── tests/
│   └── requirements.txt
├── frontend/                # Next.js application
├── docs/                    # Architecture & learning reports
├── sample_docs/             # Test documents
└── README.md
```

---

## 🛡️ Security & Privacy

VaultMind is designed with **data privacy as a first-class citizen**:

| Deployment Model | Data Location | Best For |
|---|---|---|
| **Ollama (Local)** | 100% on-premise | Banks, Healthcare, Defense |
| **Azure OpenAI** | Customer's Azure tenant | Enterprise cloud users |
| **OpenAI API** | OpenAI servers | Startups, non-sensitive data |

---

## 📜 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 🧑‍💻 Tech Stack

| Layer | Technology |
|---|---|
| LLM Orchestration | LangGraph + LangChain |
| Local LLM | Ollama (qwen3.5:4b) |
| Embedding | nomic-embed-text |
| Vector Database | ChromaDB → Qdrant |
| Backend | FastAPI (Python) |
| Frontend | Next.js + Tailwind + Shadcn |
| Database | PostgreSQL |
| Auth | JWT |
