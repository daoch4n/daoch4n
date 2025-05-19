FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    swig \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create MeCab configuration
RUN mkdir -p /usr/local/etc && \
    echo "dicdir = /var/lib/mecab/dic/ipadic-utf8" > /usr/local/etc/mecabrc

# Set up working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p output

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
