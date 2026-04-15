#!/bin/bash
set -e

# cd backend/src/chatbot_service

poetry init --no-interaction --python "^3.11" --name "chatbot-service" --description "Chatbot service"
poetry add \
  fastapi==0.115.6 \
  uvicorn==0.34.0 \
  gunicorn==23.0.0 \
  pydantic==2.10.4 \
  pydantic-settings==2.7.0 \
  loguru==0.7.3 \
  "sentence-transformers==3.0.0" \
  "faiss-cpu==1.8.0.post1" \
  networkx==3.2.1 \
  "numpy==1.26.4" \
  "openai==1.12.0" \
  pandas==2.2.0 \
  requests==2.31.0 \
  beautifulsoup4==4.12.3 \
  "lxml==5.1.1" \
  trafilatura==1.9.0 \