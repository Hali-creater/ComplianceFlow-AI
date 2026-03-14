# ComplianceFlow AI

ComplianceFlow AI is a secure RFP automation tool that uses RAG (Retrieval-Augmented Generation) to answer security questionnaires based on your company's documents.

## Features

- **Unified Interface**: One-click deployment to Streamlit Cloud.
- **Document Ingestion**: Upload SOC2 reports, security policies, and previous RFPs.
- **AI-Powered Queries**: Ask single security questions and get context-aware answers.
- **Bulk RFP Processing**: Upload Excel sheets and get AI-suggested answers for all questions.
- **Zero Data Retention**: Temporary storage is cleared upon request, and data is processed in-memory where possible.

## Deployment to Streamlit Cloud

1. Push this repository to GitHub.
2. Go to [Streamlit Cloud](https://share.streamlit.io/).
3. Connect your repository.
4. Add your `OPENAI_API_KEY` to the **Secrets** section in the Streamlit Cloud dashboard:
   ```toml
   OPENAI_API_KEY = "your_openai_api_key_here"
   ```
5. Deploy!

## Local Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up your environment variables in a `.env` file:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```
3. Run the application:
   ```bash
   streamlit run streamlit_app.py
   ```

## Usage

1. **Ingest Data**: Use the sidebar to upload your company's security documents and click "Train AI".
2. **Single Question**: Go to the "Single Question" tab to test the AI's knowledge.
3. **Bulk RFP**: Upload an Excel sheet in the "Bulk RFP Excel" tab and click "Process RFP".
4. **Human Review**: Edit the AI-suggested answers directly in the app before downloading the final result.
