# 📚 RAG PDF Assistant

A robust, local-first Retrieval-Augmented Generation (RAG) application that allows you to chat with your PDF documents. The app provides a sleek, dark-mode Streamlit interface for uploading PDFs, managing your document library, and running targeted vector-search queries powered by AI.

## ✨ Features

- **Document Ingestion**: Seamlessly upload and parse PDF documents.
- **Local Vector Database**: Utilizes [Qdrant](https://qdrant.tech/) to store high-dimensional text embeddings locally for lightning-fast retrieval.
- **Query Isolation**: Filter your queries to run across *all* uploaded documents, or target a specific PDF for highly context-aware answers.
- **Background Processing**: Uses [Inngest](https://www.inngest.com/) for reliable event-driven orchestration (background parsing, embedding generation, and LLM querying).
- **Source Tracing**: Every AI answer explicitly links back to the exact chunk of text retrieved from your documents.
- **Professional UI**: A custom, monochromatic dark-mode interface built on Streamlit.

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **Vector Database**: [Qdrant](https://qdrant.tech/)
- **Orchestration**: [Inngest](https://www.inngest.com/)
- **Backend API**: [FastAPI](https://fastapi.tiangolo.com/)
- **Package Manager**: [uv](https://github.com/astral-sh/uv)

## 🚀 Getting Started

### Prerequisites

Ensure you have Python 3.10+ and `uv` installed.

### 1. Clone the repository

```bash
git clone https://github.com/karankumar187/RAG-PDF-Assistant.git
cd RAG-PDF-Assistant
```

### 2. Install dependencies

```bash
uv venv
source .venv/bin/activate
uv sync
```

### 3. Set up Environment Variables

Create a `.env` file in the root directory and add your API keys (e.g., OpenRouter or OpenAI keys depending on your embedding/LLM configuration):

```env
# Example .env configuration
OPENAI_API_KEY="your_api_key_here"
```

### 4. Run the Inngest Dev Server

In a new terminal window, start the local Inngest development server:
```bash
npx inngest-cli@latest dev
```

### 5. Start the FastAPI Backend

In your main terminal, start the Inngest API handlers:
```bash
fastapi dev main.py --port 8288
```

### 6. Launch the Streamlit App

In a third terminal window, run the frontend:
```bash
streamlit run streamlit_app.py
```

Navigate to `http://localhost:8502` in your browser to start chatting with your PDFs!

## 📁 Project Structure

- `streamlit_app.py` - The Streamlit frontend UI.
- `main.py` - FastAPI app and Inngest function definitions (ingestion & querying logic).
- `vector_db.py` - Qdrant integration and vector search logic.
- `data_loader.py` - PDF parsing and text chunking utilities.
- `uploads/` - Temporary storage for uploaded PDFs.
- `qdrant_storage/` - Local persistent storage for Qdrant vector database.

## 📄 License

MIT License
