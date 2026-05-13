import logging
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import os
import uuid
import httpx
from pydantic import BaseModel
from typing import Optional, Union
from fastapi import UploadFile, File
import tempfile
import shutil
from data_loader import load_and_chunk_pdf, embded_texts
from vector_db import QdrantStorage
from custom_types import RAGChunkAndSrc, RAGUpsertResult, RAGSearchResult, RAGQueryResult


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    source_id: Optional[Union[str, list[str]]] = None   # single file OR list of files
    user_id: Optional[str] = None                # user email — used to scope "All Documents" searches


load_dotenv()

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=os.getenv("INNGEST_SIGNING_KEY") is not None,
    serializer=inngest.PydanticSerializer()
)


@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def rag_ingest_pdf(ctx: inngest.Context):
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        vecs = embded_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}_{i}")) for i in range(len(chunks))]
        payloads = [{"text": chunks[i], "source": source_id} for i in range(len(chunks))]
        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    chunks_and_src = await ctx.step.run("load_pdf", lambda: _load(ctx), output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)
    return ingested.model_dump()


@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf_ai(ctx: inngest.Context) -> RAGQueryResult:
    def _search(question: str, top_k: int = 5, source_id: str = None):
        query_vec = embded_texts([question])[0]
        store = QdrantStorage()
        found = store.search(query_vec, top_k, source_id=source_id)
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))
    source_id = ctx.event.data.get("source_id", None)

    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k, source_id), output_type=RAGSearchResult)

    context_block = "\n\n".join(f"- {c}" for c in found.contexts)
    user_content = (
        "Use the following context to answer the question. \n\n"
        f"Context: \n{context_block}\n\n"
        f"Question: {question} \n"
        "Answer concisely using the context above."
    )

    async def _infer_openrouter():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://rag-pdf-assistant-1jkt.onrender.com",
                    "X-Title": "RAG PDF Assistant"
                },
                json={
                    "model": "openai/gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant for answering questions based on provided context."},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500
                },
                timeout=90.0
            )
            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
            return response.json()

    res = await ctx.step.run("llm-answer", _infer_openrouter)
    answer = res["choices"][0]["message"]["content"].strip()
    return {"answer": answer, "sources": found.sources, "num_contexts": len(found.contexts)}


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the HTML frontend from /static
app.mount("/static", StaticFiles(directory="static"), name="static")


class OAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


@app.post("/api/auth/callback")
async def oauth_callback(req: OAuthCallbackRequest):
    """Exchange OAuth authorization code for user info (server-side, keeps client_secret safe)."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": req.code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": req.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Token exchange failed")
        tokens = token_resp.json()
        access_token = tokens.get("access_token")
        # Fetch user info
        userinfo_resp = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to fetch user info")
        return userinfo_resp.json()


@app.get("/")
def serve_app():
    return FileResponse("static/index.html")


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running!"}


@app.get("/api/config")
def get_config():
    return {
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
    }


@app.post("/api/ingest")
async def sync_ingest(file: UploadFile = File(...), user_id: str = Form(default="")):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            chunks = load_and_chunk_pdf(tmp_path)
            if not chunks:
                raise HTTPException(status_code=400, detail="No extractable text found in this PDF. It might be an image-only scanned document, or completely blank.")
            
            # Scope source_id to user if user_id provided
            source_id = f"{user_id}/{file.filename}" if user_id else file.filename
            vecs = embded_texts(chunks)
            ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}_{i}")) for i in range(len(chunks))]
            payloads = [{"text": chunks[i], "source": source_id, "user_id": user_id} for i in range(len(chunks))]
            QdrantStorage().upsert(ids, vecs, payloads)
            return {"ingested": len(chunks), "source_id": source_id}
        finally:
            os.remove(tmp_path)
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=str(e) + "\n" + traceback.format_exc())


@app.get("/api/list_sources")
def list_sources(user_id: str = ""):
    store = QdrantStorage()
    if user_id:
        sources = store.list_sources(user_prefix=user_id)
    else:
        sources = []
    return {"sources": sources}


@app.post("/api/query")
async def sync_query(req: QueryRequest):
    query_vec = embded_texts([req.question])[0]
    store = QdrantStorage()

    if req.source_id:
        # Query a specific document
        found_raw = store.search(query_vec, req.top_k, source_id=req.source_id)
    elif req.user_id:
        # Query all documents belonging to this user
        found_raw = store.search(query_vec, req.top_k, user_prefix=req.user_id)
    else:
        found_raw = store.search(query_vec, req.top_k)

    contexts = found_raw["contexts"]
    sources = found_raw["sources"]

    context_block = "\n\n".join(f"- {c}" for c in contexts)
    user_content = (
        "Use the following context to answer the question. \n\n"
        f"Context: \n{context_block}\n\n"
        f"Question: {req.question} \n"
        "Answer concisely using the context above."
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://rag-pdf-assistant-1jkt.onrender.com",
                "X-Title": "RAG PDF Assistant"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant for answering questions based on provided context."},
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.2,
                "max_tokens": 500
            },
            timeout=90.0
        )
        if response.status_code != 200:
            raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

        res = response.json()
        answer = res["choices"][0]["message"]["content"].strip()
        return {"answer": answer, "sources": sources, "num_contexts": len(contexts)}


class DeleteRequest(BaseModel):
    source_id: str
    user_id: str


@app.post("/api/delete_source")
def delete_source(req: DeleteRequest):
    store = QdrantStorage()
    # Basic security check
    if not req.source_id.startswith(req.user_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    store.delete_by_source(req.source_id)
    return {"status": "ok"}


inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])