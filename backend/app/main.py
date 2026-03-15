import os
import shutil
import pandas as pd
import json
import datetime
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ComplianceFlow Pro AI API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
DB_DIR = os.path.join(UPLOAD_DIR, "chroma_db")

# Global state (for MVP simplicity, in production use a DB)
_vectorstore = None
_embeddings = None
compliance_rules = [
    {"id": "R1", "rule": "All customer data must be encrypted at rest using AES-256.", "risk": "High"},
    {"id": "R2", "rule": "Multi-factor authentication (MFA) must be enforced for all employees.", "risk": "High"},
    {"id": "R3", "rule": "A SOC2 Type II report must be available for the previous 12 months.", "risk": "Medium"},
]
audit_log = []

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set in environment.")
        _embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    return _embeddings

def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(embedding_function=get_embeddings(), persist_directory=DB_DIR)
    return _vectorstore

def get_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set in environment.")
    return ChatOpenAI(model_name="gpt-4o", temperature=0, openai_api_key=api_key)

class RFPAnswer(BaseModel):
    question: str
    answer: str
    risk_score: str
    status: str

def cleanup_files(paths: List[str]):
    for path in paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

@app.post("/ingest")
async def ingest_documents(files: List[UploadFile] = File(...)):
    try:
        documents = []
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            if file.filename.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
                documents.extend(loader.load())
            else:
                try:
                    content = file.file.read().decode("utf-8")
                except:
                    content = file.file.read().decode("latin-1")
                documents.append(Document(page_content=content, metadata={"source": file.filename}))

            os.remove(file_path)

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        texts = text_splitter.split_documents(documents)

        vs = get_vectorstore()
        vs.add_documents(texts)

        return {"message": f"Successfully ingested {len(files)} files", "chunks": len(texts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=RFPAnswer)
async def query_rfp(question: str = Form(...)):
    try:
        vs = get_vectorstore()
        llm = get_llm()

        rules_context = json.dumps(compliance_rules, indent=2)

        prompt_template = f"""
        Expert Security Compliance Analysis.
        RULES: {rules_context}
        CONTEXT: {{context}}
        QUESTION: {{question}}
        Format: AI SUGGESTED ANSWER: <text> | RISK SCORE: <Low|Medium|High>
        """

        PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff", retriever=vs.as_retriever(), chain_type_kwargs={"prompt": PROMPT}
        )

        result = qa_chain.invoke({"query": question})
        raw = result["result"]

        risk = "Low"
        if "RISK SCORE: High" in raw: risk = "High"
        elif "RISK SCORE: Medium" in raw: risk = "Medium"

        entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "answer": raw,
            "risk_score": risk,
            "status": "Pending Review"
        }
        audit_log.append(entry)

        return {
            "question": question,
            "answer": raw,
            "risk_score": risk,
            "status": "Pending Review"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit-log")
async def get_audit_log():
    return audit_log

@app.post("/clear-data")
async def clear_data():
    global _vectorstore
    global audit_log
    try:
        if _vectorstore:
            _vectorstore.delete_collection()
            _vectorstore = None
        if os.path.exists(DB_DIR):
            shutil.rmtree(DB_DIR)
        audit_log = []
        return {"message": "All ingested data has been deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
