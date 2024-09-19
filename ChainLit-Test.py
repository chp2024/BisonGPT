from openai import AsyncOpenAI
import os
import dotenv
import chainlit as cl
from pinecone import Pinecone
from generate_embeddings import num_tokens
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import logging

dotenv.load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS

# Set up logging
logging.basicConfig(level=logging.DEBUG)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Ensure instrument_openai is correctly used
cl.instrument_openai()

# Pinecone initialization
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "bisongpt-index"
index = pc.Index(INDEX_NAME)

SETTINGS = {
    "gpt-model": "gpt-3.5-turbo",
    "embedding-model": "text-embedding-ada-002",
    "temperature": 0,
    "namespace": "howard-catalogue",
}

UNANSWERED_LOG_FILE = "unanswered_questions.txt"

# Function to log unanswered questions
def log_unanswered_question(query):
    with open(UNANSWERED_LOG_FILE, "a") as log_file:
        log_file.write(f"{query}\n")

# Function to query Pinecone for the most relevant vectors
async def query_pinecone(query_embedding, top_n=10):
    response = index.query(
        vector=query_embedding,
        top_k=top_n,
        include_values=False,
        include_metadata=True,
        namespace=SETTINGS["namespace"],
    )
    return response

# Function to get query embedding
async def get_query_embedding(query):
    response = await client.embeddings.create(
        model=SETTINGS["embedding-model"],
        input=query
    )
    # Access the embedding data correctly
    embedding = response.data[0].embedding
    return embedding

# Function to process the query and get a response
async def process_query(query):
    query_embedding = await get_query_embedding(query)
    pinecone_response = await query_pinecone(query_embedding)
    # Process the Pinecone response to generate a meaningful answer
    # For simplicity, let's assume we just return the first result's metadata
    if pinecone_response['matches']:
        return pinecone_response['matches'][0]['metadata']['text']
    else:
        log_unanswered_question(query)
        return "I'm sorry, I don't have an answer for that."

@app.route('/api/chat', methods=['POST'])
async def chat():
    try:
        data = request.json
        query = data.get('query')
        logging.debug(f"Received query: {query}")
        response = await process_query(query)
        logging.debug(f"Response: {response}")
        return jsonify({'answer': response})
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)