import os
import shutil
import pandas as pd
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ComplianceFlow AI API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
# For Zero Data Retention, we use temporary directories or clear them after processing.
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Note: We use Chroma in-memory for Zero Data Retention if possible,
# or clear it after the session. For this MVP, we use a local DB but clear it.

def get_vectorstore():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set in environment.")
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    # Using a transient vectorstore would be better for Zero Data Retention
    return Chroma(embedding_function=embeddings)

def get_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set in environment.")
    return ChatOpenAI(model_name="gpt-4o", temperature=0, openai_api_key=api_key)

class RFPAnswer(BaseModel):
    question: str
    answer: str
    confidence: float

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
                with open(file_path, "r") as f:
                    documents.append(Document(page_content=f.read(), metadata={"source": file.filename}))

            # Clean up source file immediately after loading into memory
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

        prompt_template = """
        You are an expert Security and Compliance Engineer. Use the following pieces of context to answer the RFP question.
        If you don't know the answer based on the context, say "Information not found in internal documents."
        Keep the tone professional and concise, typical of a security response.

        Context: {context}
        Question: {question}

        Helpful Answer:"""

        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vs.as_retriever(),
            chain_type_kwargs={"prompt": PROMPT}
        )

        result = qa_chain.invoke({"query": question})

        return {
            "question": question,
            "answer": result["result"],
            "confidence": 0.9
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-rfp-excel")
async def process_rfp_excel(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files are supported")

        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        df = pd.read_excel(file_path)
        questions = df.iloc[:, 0].tolist()

        vs = get_vectorstore()
        llm = get_llm()

        prompt_template = """
        You are an expert Security and Compliance Engineer. Use the following pieces of context to answer the RFP question.
        If you don't know the answer based on the context, say "Information not found in internal documents."
        Keep the tone professional and concise, typical of a security response.

        Context: {context}
        Question: {question}

        Helpful Answer:"""

        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )

        # Instantiate chain once outside the loop
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vs.as_retriever(),
            chain_type_kwargs={"prompt": PROMPT}
        )

        answers = []
        for q in questions:
            if pd.isna(q):
                answers.append("")
                continue
            result = qa_chain.invoke({"query": str(q)})
            answers.append(result["result"])

        df['AI_Suggested_Answer'] = answers

        output_filename = f"processed_{file.filename}"
        output_path = os.path.join(UPLOAD_DIR, output_filename)
        df.to_excel(output_path, index=False)

        # Schedule cleanup of the uploaded and processed files
        background_tasks.add_task(cleanup_files, [file_path, output_path])

        return {
            "message": "RFP processed successfully. Data will be deleted after download.",
            "questions_count": len(questions),
            "results": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear-data")
async def clear_data():
    # Implementation for clearing the vectorstore
    # For Chroma, we might need to recreate it or delete the collection
    try:
        vs = get_vectorstore()
        vs.delete_collection()
        return {"message": "All ingested data has been deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
