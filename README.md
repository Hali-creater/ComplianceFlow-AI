---
title: ComplianceFlow Pro AI
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.55.0
app_file: app.py
pinned: false
---

# ComplianceFlow Pro AI

ComplianceFlow Pro AI is an enterprise-grade secure RFP automation and compliance auditing tool.

## Features

- **Unified Interface**: Optimized for Hugging Face Spaces and Streamlit Cloud.
- **Structured Rules Management**: Define and enforce specific compliance rules.
- **Audit Trail**: Full traceability of AI decisions for auditors.
- **Risk Dashboard**: High-level visualization of compliance findings.
- **Zero Data Retention**: Processes data in-memory and provides purging capabilities.

## Deployment to Hugging Face Spaces

1. Create a new Streamlit Space on [Hugging Face](https://huggingface.co/spaces).
2. Push this repository to your Space.
3. Add your `OPENAI_API_KEY` to the **Settings > Variables and Secrets** section of your Space.

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
   streamlit run app.py
   ```
