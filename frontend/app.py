import streamlit as st
import requests
import pandas as pd
import io
import os

st.set_page_config(page_title="ComplianceFlow AI", layout="wide")

st.title("🛡️ ComplianceFlow AI")
st.subheader("Automate your Security RFPs with AI")

API_URL = os.getenv("API_URL", "http://localhost:8000")

# Sidebar for Ingestion
with st.sidebar:
    st.header("🏢 My Company Data")
    st.info("Upload your SOC2, security policies, and previous RFP answers to train the AI.")
    uploaded_docs = st.file_uploader("Upload Documents (PDF, TXT)", accept_multiple_files=True)

    if st.button("Train AI on these docs"):
        if uploaded_docs:
            with st.spinner("Ingesting documents..."):
                files = [("files", (doc.name, doc.getvalue())) for doc in uploaded_docs]
                response = requests.post(f"{API_URL}/ingest", files=files)
                if response.status_code == 200:
                    st.success(f"Ingested {len(uploaded_docs)} files successfully!")
                else:
                    st.error(f"Error during ingestion: {response.text}")
        else:
            st.warning("Please upload some files first.")

    if st.button("Clear All Data (Zero Retention)"):
        response = requests.post(f"{API_URL}/clear-data")
        if response.status_code == 200:
            st.success("All data cleared successfully.")
        else:
            st.error("Error clearing data.")

# Main area for RFP Processing
tab1, tab2 = st.tabs(["📄 Single Question", "📊 Bulk RFP Excel"])

with tab1:
    st.header("Ask a Security Question")
    question = st.text_input("Enter a security question (e.g., 'Do you encrypt data at rest?')")
    if st.button("Get Answer"):
        if question:
            with st.spinner("Searching internal docs..."):
                response = requests.post(f"{API_URL}/query", data={"question": question})
                if response.status_code == 200:
                    result = response.json()
                    st.write("### AI Suggested Answer:")

                    # Human-in-the-loop review
                    answer_text = st.text_area("Review and Edit AI Answer", value=result["answer"], height=200)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Approve Answer"):
                            st.success("Answer approved and ready for RFP!")
                            st.code(answer_text)
                else:
                    st.error(f"Error fetching answer: {response.text}")
        else:
            st.warning("Please enter a question.")

with tab2:
    st.header("Bulk RFP Processing")
    uploaded_rfp = st.file_uploader("Upload RFP Excel sheet (Questions should be in the first column)", type=["xlsx", "xls"])

    if st.button("Process RFP"):
        if uploaded_rfp:
            with st.spinner("Processing entire RFP..."):
                files = {"file": (uploaded_rfp.name, uploaded_rfp.getvalue())}
                response = requests.post(f"{API_URL}/process-rfp-excel", files=files)

                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Processed {data['questions_count']} questions!")

                    # Display results with human review capability
                    results_df = pd.DataFrame(data["results"])
                    st.write("### AI Suggested Answers (Review Below)")

                    edited_df = st.data_editor(results_df)

                    # Download link for the reviewed/edited answers
                    csv = edited_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Approved RFP as CSV",
                        data=csv,
                        file_name="approved_rfp.csv",
                        mime="text/csv",
                    )
                else:
                    st.error(f"Error processing RFP: {response.text}")
        else:
            st.warning("Please upload an Excel file.")

# Footer
st.markdown("---")
st.caption("ComplianceFlow AI - Secure & Private RFP Automation | Zero Data Retention Policy Enabled")
