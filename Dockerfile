# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the ports for FastAPI and Streamlit
EXPOSE 8000
EXPOSE 8501

# Create a shell script to run both services
RUN echo "#!/bin/sh\npython -m backend.app.main & \nstreamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0" > /app/run.sh
RUN chmod +x /app/run.sh

# Run the shell script
CMD ["/app/run.sh"]
