FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies including MySQL client and pkg-config
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first to leverage Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Specifically upgrade google-cloud-aiplatform to the latest version
RUN pip install --no-cache-dir --upgrade google-cloud-aiplatform

# Copy project files
COPY . .

# Create wrapper file to handle import error
RUN echo 'try:\n    from vertexai.generative_models import *\nexcept ImportError:\n    print("Warning: vertexai.generative_models tidak tersedia")\n    # Mock classes disini jika diperlukan' > /app/utils/gemini_wrapper.py

# Expose port
EXPOSE 8080

# Run application with debug log level
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "debug"]
