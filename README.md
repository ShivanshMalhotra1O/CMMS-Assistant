# 🛠️ CMMS Assistant

An AI-powered assistant for **Computerized Maintenance Management Systems (CMMS)**, built with Python and a RAG (Retrieval-Augmented Generation) pipeline using ChromaDB as the vector store.

---

## 📖 Overview

CMMS Assistant is a conversational AI tool designed to help maintenance teams query, understand, and interact with CMMS data using natural language. It leverages a vector database to retrieve relevant maintenance records, work orders, or asset information and generates accurate, context-aware responses.

---

## ✨ Features

- 💬 **Natural Language Queries** — Ask questions about assets, work orders, or maintenance schedules in plain English
- 🔍 **RAG Pipeline** — Combines document retrieval from ChromaDB with LLM generation for accurate, grounded responses
- 🌐 **Web Interface** — HTML-based frontend for easy interaction
- ⚡ **Fast Semantic Search** — ChromaDB powers efficient similarity search over embedded CMMS data

---

## 🗂️ Project Structure

```
CMMS-Assistant/
├── app/                        # Core application logic (Python backend + HTML frontend)
├── chroma_store/               # Persisted ChromaDB vector store
│   └── 86063db4-f9ba-47d2-94a4-03aabfd1f862/
├── requirements.txt            # Python dependencies
└── .gitignore
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ShivanshMalhotra1O/CMMS-Assistant.git
   cd CMMS-Assistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   # Navigate to the app directory and run the main script
   cd app
   python main.py   # or the entry point file in the app/ folder
   ```

4. **Open the web interface**
   Open your browser and navigate to `http://localhost:5000` (or the configured port).

---

## 🧠 How It Works

1. **Ingestion** — CMMS data (work orders, assets, maintenance logs, etc.) is embedded and stored in a ChromaDB vector store.
2. **Retrieval** — When a user submits a query, the system performs a semantic search to find the most relevant records.
3. **Generation** — The retrieved context is passed to a language model to generate a helpful, accurate response.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python |
| Frontend | HTML |
| Vector Store | ChromaDB |
| AI/LLM | LLM via API (configured in app) |

---

## 📋 Requirements

Install all dependencies with:

```bash
pip install -r requirements.txt
```

Key libraries likely include:
- `chromadb` — vector database for semantic search
- `langchain` or similar — LLM orchestration
- `flask` / `fastapi` — web server
- `openai` / `anthropic` — LLM provider SDK

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests for bug fixes, new features, or improvements.

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source. See the repository for license details.

---

## 👤 Author

**Shivansh Malhotra**
- GitHub: [@ShivanshMalhotra1O](https://github.com/ShivanshMalhotra1O)
