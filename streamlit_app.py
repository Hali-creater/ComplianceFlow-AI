import streamlit as st
import pandas as pd
import os
import shutil
import json
import datetime
from typing import List, Dict
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from dotenv import load_dotenv

# Load local .env if it exists (for local testing)
load_dotenv()

st.set_page_config(page_title="ComplianceFlow Pro AI", layout="wide")

# App Title
st.title("🛡️ ComplianceFlow Pro AI")
st.subheader("Enterprise-Grade Compliance & RFP Automation")

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

TEMP_DIR = "temp_storage"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Initialize Session State
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []
if "compliance_rules" not in st.session_state:
    st.session_state.compliance_rules = [
        {"id": "R1", "rule": "All customer data must be encrypted at rest using AES-256.", "risk": "High"},
        {"id": "R2", "rule": "Multi-factor authentication (MFA) must be enforced for all employees.", "risk": "High"},
        {"id": "R3", "rule": "A SOC2 Type II report must be available for the previous 12 months.", "risk": "Medium"},
    ]
if "bulk_results" not in st.session_state:
    st.session_state.bulk_results = None
if "single_answer" not in st.session_state:
    st.session_state.single_answer = None

# --- Helper Functions ---

@st.cache_resource
def get_vectorstore():
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
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
            # Handle possible encoding issues
            try:
                content = uploaded_file.read().decode("utf-8")
            except:
                content = uploaded_file.read().decode("latin-1")
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
    st.session_state.audit_log = []

def log_audit_entry(question, answer, risk_score, rules_applied):
    st.session_state.audit_log.append({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": answer,
        "risk_score": risk_score,
        "rules_applied": rules_applied,
        "status": "Pending Review"
    })

# --- Sidebar: System Configuration & Rules ---
with st.sidebar:
    st.header("⚙️ System Management")

    with st.expander("📝 Compliance Rules Editor"):
        rules_df = pd.DataFrame(st.session_state.compliance_rules)
        edited_rules_df = st.data_editor(rules_df, num_rows="dynamic")
        if st.button("Save Rules"):
            st.session_state.compliance_rules = edited_rules_df.to_dict('records')
            st.success("Rules updated!")

    st.divider()
    st.header("🏢 My Company Data")
    uploaded_docs = st.file_uploader("Upload Documents (PDF, TXT)", accept_multiple_files=True, key="docs")

    if st.button("Train AI on these docs"):
        if uploaded_docs:
            with st.spinner("Ingesting documents..."):
                try:
                    num_chunks = process_documents(uploaded_docs)
                    st.success(f"Ingested {len(uploaded_docs)} files! Created {num_chunks} chunks.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please upload some files first.")

    st.divider()
    if st.button("Reset System (Zero Retention)"):
        clear_data()
        st.success("All system data has been purged.")

# --- Main App Tabs ---
tab_dashboard, tab_query, tab_bulk, tab_audit = st.tabs(["📊 Dashboard", "📄 Single Question", "📊 Bulk RFP Excel", "📑 Audit Trail"])

# Tab: Dashboard
with tab_dashboard:
    st.header("Compliance Risk Overview")
    if not st.session_state.audit_log:
        st.info("No documents analyzed yet. Start by asking a question or processing an RFP.")
    else:
        col1, col2, col3 = st.columns(3)
        total_checks = len(st.session_state.audit_log)
        high_risk = len([x for x in st.session_state.audit_log if x["risk_score"] == "High"])
        pending_review = len([x for x in st.session_state.audit_log if x["status"] == "Pending Review"])

        col1.metric("Total Analysis Requests", total_checks)
        col2.metric("High Risk Findings", high_risk, delta_color="inverse")
        col3.metric("Pending Human Reviews", pending_review)

        st.divider()
        st.subheader("Risk Distribution")
        risk_counts = pd.DataFrame(st.session_state.audit_log)["risk_score"].value_counts()
        st.bar_chart(risk_counts)

# Tab: Single Question Query
with tab_query:
    st.header("Rule-Based Compliance Check")
    question = st.text_input("Enter a security question or requirement", key="q_input")

    if st.button("Analyze Compliance", key="single_q"):
        if question:
            with st.spinner("Retrieving relevant rules and documents..."):
                try:
                    vs = get_vectorstore()
                    llm = get_llm()

                    # Construct a rule-aware prompt
                    rules_context = json.dumps(st.session_state.compliance_rules, indent=2)

                    prompt_template = f"""
                    You are an expert Security and Compliance Engineer.

                    COMPLIANCE RULES:
                    {rules_context}

                    INSTRUCTIONS:
                    1. Use the provided context from internal documents to answer the question.
                    2. Evaluate the answer against the COMPLIANCE RULES.
                    3. Determine a RISK SCORE (High, Medium, Low).
                    4. Reference exact document names if found.
                    5. If no information is found, say "Information not found in internal documents."

                    INTERNAL CONTEXT:
                    {{context}}

                    QUESTION:
                    {{question}}

                    FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
                    AI SUGGESTED ANSWER: <answer with citations>
                    RISK SCORE: <Low|Medium|High>
                    RULES APPLIED: <rule IDs>
                    EXPLANATION: <brief reasoning>
                    """

                    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=llm, chain_type="stuff", retriever=vs.as_retriever(), chain_type_kwargs={"prompt": PROMPT}
                    )

                    result = qa_chain.invoke({"query": question})
                    raw_answer = result["result"]

                    # Simple parsing of the structured response (in a real app, use PydanticOutputParser)
                    st.session_state.single_answer = raw_answer

                    # Extraction for audit log
                    risk = "Low"
                    if "RISK SCORE: High" in raw_answer: risk = "High"
                    elif "RISK SCORE: Medium" in raw_answer: risk = "Medium"

                    log_audit_entry(question, raw_answer, risk, "Check Rules")

                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter a question.")

    if st.session_state.single_answer:
        st.write("### AI Compliance Analysis")
        # In a real app we'd split these out nicely
        st.info(st.session_state.single_answer)

        st.divider()
        st.subheader("Human-in-the-Loop Review")
        final_decision = st.radio("Decision", ["Approve", "Reject", "Request Changes"])
        human_notes = st.text_area("Compliance Officer Notes")

        if st.button("Finalize Decision"):
            if st.session_state.audit_log:
                st.session_state.audit_log[-1]["status"] = final_decision
                st.session_state.audit_log[-1]["notes"] = human_notes
                st.success("Analysis finalized and logged.")

# Tab: Bulk RFP Processing
with tab_bulk:
    st.header("Bulk RFP Audit")
    uploaded_rfp = st.file_uploader("Upload RFP Excel sheet", type=["xlsx", "xls"], key="rfp_excel")

    if st.button("Run Bulk Audit", key="bulk_proc"):
        if uploaded_rfp:
            with st.spinner("Analyzing entire RFP against policies and rules..."):
                try:
                    df = pd.read_excel(uploaded_rfp)
                    questions = df.iloc[:, 0].tolist()

                    vs = get_vectorstore()
                    llm = get_llm()
                    rules_context = json.dumps(st.session_state.compliance_rules, indent=2)

                    prompt_template = f"""
                    Expert Security Compliance Analysis.
                    RULES: {rules_context}
                    CONTEXT: {{context}}
                    QUESTION: {{question}}
                    Format: ANSWER: <text> | RISK: <Low|Medium|High>
                    """

                    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=llm, chain_type="stuff", retriever=vs.as_retriever(), chain_type_kwargs={"prompt": PROMPT}
                    )

                    answers = []
                    risks = []
                    for q in questions:
                        if pd.isna(q):
                            answers.append(""); risks.append("N/A")
                        else:
                            res = qa_chain.invoke({"query": str(q)})
                            parts = res["result"].split("|")
                            ans = parts[0].replace("ANSWER:", "").strip()
                            rsk = parts[1].replace("RISK:", "").strip() if len(parts) > 1 else "Unknown"
                            answers.append(ans)
                            risks.append(rsk)
                            log_audit_entry(str(q), ans, rsk, "Bulk Rule Check")

                    df['AI_Suggested_Answer'] = answers
                    df['Compliance_Risk'] = risks
                    st.session_state.bulk_results = df
                    st.success(f"Audit complete for {len(questions)} requirements.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please upload an Excel file.")

    if st.session_state.bulk_results is not None:
        st.write("### Audit Results (Review Below)")
        edited_df = st.data_editor(st.session_state.bulk_results)

        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Export Audit Report (CSV)",
            data=csv,
            file_name=f"compliance_audit_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

# Tab: Audit Trail
with tab_audit:
    st.header("Traceability & Audit Log")
    if not st.session_state.audit_log:
        st.info("Log is empty.")
    else:
        audit_df = pd.DataFrame(st.session_state.audit_log)
        st.dataframe(audit_df, use_container_width=True)

        log_csv = audit_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Full Audit Trail", log_csv, "audit_trail.csv", "text/csv")

# Footer
st.markdown("---")
st.caption("ComplianceFlow Pro AI - Enterprise Security Automation | Built for Traceability and Risk Management")
