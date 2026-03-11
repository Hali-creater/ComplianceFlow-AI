# ComplianceFlow AI

ComplianceFlow AI is a secure RFP automation tool that uses RAG (Retrieval-Augmented Generation) to answer security questionnaires based on your company's documents.

## Features

- **Document Ingestion**: Upload SOC2 reports, security policies, and previous RFPs.
- **AI-Powered Queries**: Ask single security questions and get context-aware answers.
- **Bulk RFP Processing**: Upload Excel sheets and get AI-suggested answers for all questions.
- **Human-in-the-loop**: Review and approve AI-generated answers.

## Architecture

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **AI Engine**: LangChain
- **Vector Database**: ChromaDB
- **LLM**: GPT-4o

## Setup

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```
4. Run the Backend:
   ```bash
   python -m backend.app.main
   ```
5. Run the Frontend:
   ```bash
   streamlit run frontend/app.py
   ```

## Usage

1. **Ingest Data**: Use the sidebar in the Streamlit app to upload your company's security documents.
2. **Single Question**: Go to the "Single Question" tab to test the AI's knowledge.
3. **Bulk RFP**: Upload an Excel sheet in the "Bulk RFP Excel" tab. The AI will process each row and provide suggested answers.
