import streamlit as st
import pandas as pd
import os
import shutil
from typing import List
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from dotenv import load_dotenv

# Load local .env if it exists (for local testing)
load_dotenv()

st.set_page_config(page_title="ComplianceFlow AI", layout="wide")

# App Title
st.title("🛡️ ComplianceFlow AI")
st.subheader("Automate your Security RFPs with AI")

# --- Configuration & State ---
def get_api_key():
    try:
        return st.secrets["OPENAI_API_KEY"]
    except:
        return os.getenv("OPENAI_API_KEY")

openai_api_key = get_api_key()

if not openai_api_key:
    st.warning("⚠️ OpenAI API Key not found. Please add it to your Streamlit Secrets or .env file.")
    st.stop()

# Persistent Directory for Chroma (Local session storage)
TEMP_DIR = "temp_storage"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "bulk_results" not in st.session_state:
    st.session_state.bulk_results = None
if "single_answer" not in st.session_state:
    st.session_state.single_answer = None

# --- Helper Functions ---

@st.cache_resource
def get_vectorstore():
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    # Persist directory is important for keeping data between runs in the same session
    return Chroma(embedding_function=embeddings, persist_directory=os.path.join(TEMP_DIR, "chroma_db"))

def get_llm():
    return ChatOpenAI(model_name="gpt-4o", temperature=0, openai_api_key=openai_api_key)

def process_documents(uploaded_files):
    documents = []
    for uploaded_file in uploaded_files:
        file_path = os.path.join(TEMP_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        if uploaded_file.name.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
            documents.extend(loader.load())
        else:
            content = uploaded_file.read().decode("utf-8")
            documents.append(Document(page_content=content, metadata={"source": uploaded_file.name}))

        os.remove(file_path)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.split_documents(documents)

    vs = get_vectorstore()
    vs.add_documents(texts)
    return len(texts)

def clear_data():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR)
    st.cache_resource.clear()
    st.session_state.bulk_results = None
    st.session_state.single_answer = None

# --- Sidebar: Data Ingestion ---
with st.sidebar:
    st.header("🏢 My Company Data")
    st.info("Upload your SOC2, security policies, and previous RFP answers to train the AI.")
    uploaded_docs = st.file_uploader("Upload Documents (PDF, TXT)", accept_multiple_files=True, key="docs")

    if st.button("Train AI on these docs"):
        if uploaded_docs:
            with st.spinner("Ingesting documents..."):
                try:
                    num_chunks = process_documents(uploaded_docs)
                    st.success(f"Successfully ingested data! Created {num_chunks} searchable chunks.")
                except Exception as e:
                    st.error(f"Error during ingestion: {str(e)}")
        else:
            st.warning("Please upload some files first.")

    st.divider()
    if st.button("Clear All Data (Zero Retention)"):
        clear_data()
        st.success("All temporary data has been purged.")

# --- Main App Tabs ---
tab1, tab2 = st.tabs(["📄 Single Question", "📊 Bulk RFP Excel"])

# Tab 1: Single Question Query
with tab1:
    st.header("Ask a Security Question")
    question = st.text_input("Enter a security question (e.g., 'Do you encrypt data at rest?')", key="q_input")

    if st.button("Get Answer", key="single_q"):
        if question:
            with st.spinner("Searching internal docs..."):
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

                    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=llm, chain_type="stuff", retriever=vs.as_retriever(), chain_type_kwargs={"prompt": PROMPT}
                    )

                    result = qa_chain.invoke({"query": question})
                    st.session_state.single_answer = result["result"]
                except Exception as e:
                    st.error(f"Error fetching answer: {str(e)}")
        else:
            st.warning("Please enter a question.")

    if st.session_state.single_answer:
        st.write("### AI Suggested Answer:")
        edited_answer = st.text_area("Review and Edit AI Answer", value=st.session_state.single_answer, height=200)
        if st.button("Approve Answer"):
            st.success("Answer approved!")
            st.code(edited_answer)

# Tab 2: Bulk RFP Processing
with tab2:
    st.header("Bulk RFP Processing")
    uploaded_rfp = st.file_uploader("Upload RFP Excel sheet", type=["xlsx", "xls"], key="rfp_excel")

    if st.button("Process RFP", key="bulk_proc"):
        if uploaded_rfp:
            with st.spinner("Processing entire RFP..."):
                try:
                    df = pd.read_excel(uploaded_rfp)
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

                    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=llm, chain_type="stuff", retriever=vs.as_retriever(), chain_type_kwargs={"prompt": PROMPT}
                    )

                    answers = []
                    for q in questions:
                        if pd.isna(q):
                            answers.append("")
                        else:
                            res = qa_chain.invoke({"query": str(q)})
                            answers.append(res["result"])

                    df['AI_Suggested_Answer'] = answers
                    st.session_state.bulk_results = df
                    st.success(f"Processed {len(questions)} questions!")
                except Exception as e:
                    st.error(f"Error processing RFP: {str(e)}")
        else:
            st.warning("Please upload an Excel file.")

    if st.session_state.bulk_results is not None:
        st.write("### AI Suggested Answers (Review Below)")
        edited_df = st.data_editor(st.session_state.bulk_results)

        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Approved RFP as CSV",
            data=csv,
            file_name="approved_rfp.csv",
            mime="text/csv",
        )

# Footer
st.markdown("---")
st.caption("ComplianceFlow AI - Secure & Private RFP Automation | Zero Data Retention Policy Enabled")
