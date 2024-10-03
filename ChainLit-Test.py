from openai import AsyncOpenAI
import os
import dotenv
import chainlit as cl
from pinecone import Pinecone
from generate_embeddings import num_tokens

dotenv.load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

cl.instrument_openai()

# Pinecone initialization
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "bisongpt-index"
index = pc.Index(INDEX_NAME)

SETTINGS = {
    "gpt-model": "gpt-3.5-turbo",
    "embedding-model": "text-embedding-3-small",
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

    # Extract the relevant texts from the metadata of the query results
    strings = [match["metadata"]["text"] for match in response["matches"]]
    relatedness_scores = [match["score"] for match in response["matches"]]

    return strings, relatedness_scores


# Function to generate the query message
async def query_message(query, model, token_budget):
    # Get the query embedding from OpenAI API
    query_embedding_response = await client.embeddings.create(
        model=SETTINGS["embedding-model"], input=query
    )
    query_embedding = query_embedding_response.data[0].embedding

    # Query Pinecone for the most relevant texts
    strings, relatedness = await query_pinecone(query_embedding)
    print(strings)

    # Construct the message with the most relevant texts
    introduction = 'Use the below information about Howard University to answer the subsequent question. If the answer could not be found in the information then write "I could not find an answer."'
    question = f"\n\nQuestion: {query}"

    message = introduction
    for string in strings:
        next_segment = f'\n\nHoward Catalogue segment:\n"""{string}"""\n'
        if num_tokens(message + next_segment + question, model=model) > token_budget:
            break
        message += next_segment
    return message + question


# Main function to ask a question
async def ask(query, model=SETTINGS["gpt-model"], token_budget=4096 - 250):
    message = await query_message(query, model=model, token_budget=token_budget)

    # Chat completion request to OpenAI
    messages = [
        {"role": "system", "content": "You answer questions about Howard University."},
        {"role": "user", "content": message},
    ]

    response = await client.chat.completions.create(
        model=model, messages=messages, temperature=SETTINGS["temperature"]
    )
    response_content = response.choices[0].message.content

    # Check if the response contains "I could not find an answer"
    if "I could not find an answer" in response_content:
        log_unanswered_question(query)

    return response_content


@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content="Hello, welcome to BisonGPT! How can I help you today?"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    response = await ask(message.content)
    await cl.Message(content=response).send()