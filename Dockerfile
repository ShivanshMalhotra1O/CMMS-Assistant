FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create chroma_store directory (persisted via volume)
RUN mkdir -p /app/chroma_store

# Expose the FastAPI port
EXPOSE 5000

# Run the FastAPI app via uvicorn
CMD ["uvicorn", "app.agents.app:api", "--host", "0.0.0.0", "--port", "5000"]
