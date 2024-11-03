import os
import tiktoken
from openai import AsyncOpenAI
from pinecone import Pinecone

import chainlit as cl


client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
INDEX_NAME = "bisongpt-index"
index = pc.Index(INDEX_NAME)

settings = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 500,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
}

pinecone_settings = {
    "gpt-model": "gpt-3.5-turbo",
    "embedding-model": "text-embedding-3-small",
    "namespace": "howard-catalogue",
}


def num_tokens(text, model):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


async def query_pinecone(query_embedding, top_n=10):
    response = index.query(
        vector=query_embedding,
        top_k=top_n,
        include_values=False,
        include_metadata=True,
        namespace=pinecone_settings["namespace"],
    )

    # Extract the relevant texts from the metadata of the query results
    strings = [match["metadata"]["text"] for match in response["matches"]]
    relatedness_scores = [match["score"] for match in response["matches"]]

    return strings, relatedness_scores


async def query_message(query, model, token_budget):
    # Get the query embedding from OpenAI API
    query_embedding_response = await client.embeddings.create(
        model=pinecone_settings["embedding-model"], input=query
    )
    query_embedding = query_embedding_response.data[0].embedding

    # Query Pinecone for the most relevant texts
    strings, relatedness = await query_pinecone(query_embedding)

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


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": "You are a helpful assistant that answers questions about Howard University."}],
    )
    # await cl.Message(content="Welcome to BisonGPT!").send()


@cl.on_message
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history")

    # Query Pinecone for related information
    pinecone_response = await query_message(message.content, settings["model"], settings["max_tokens"])

    # Update message history with the Pinecone response
    message_history.append({"role": "user", "content": pinecone_response})

    msg = cl.Message(content="")
    await msg.send()

    # Send message history to OpenAI model with Pinecone-enhanced context
    stream = await client.chat.completions.create(
        messages=message_history, stream=True, **settings
    )

    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await msg.stream_token(token)

    message_history.append({"role": "assistant", "content": msg.content})
    await msg.update()
