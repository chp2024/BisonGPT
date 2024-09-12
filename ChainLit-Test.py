from openai import AsyncOpenAI
from scipy import spatial
import pandas as pd
import numpy as np
import os
import dotenv
from generate_embeddings import num_tokens

dotenv.load_dotenv()

import chainlit as cl

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

cl.instrument_openai()

SETTINGS = {
    "gpt-model": "gpt-3.5-turbo",
    "embedding-model": "text-embedding-3-small",
    "temperature": 0,
    'df': pd.read_csv("BisonGPT/Data/20232024-embeddings.csv")
}

def strings_ranked_by_relatedness(query_embedding, df, top_n=10):
    # Convert all embeddings to numpy arrays
    df['embedding'] = df['embedding'].apply(lambda x: np.array(eval(x)))

    embeddings = np.vstack(df['embedding'].values)
    
    # Calculate cosine distance in a vectorized way for all rows
    relatedness_scores = 1 - spatial.distance.cdist([query_embedding], embeddings, 'cosine')[0]
    
    # Add relatedness scores to the DataFrame
    df['relatedness'] = relatedness_scores
    sorted_df = df.sort_values(by='relatedness', ascending=False).head(top_n)
    
    return sorted_df['text'].tolist(), sorted_df['relatedness'].tolist()

async def query_message(query, df, model, token_budget):
    # Get the query embedding
    query_embedding_response = await client.embeddings.create(
        model=SETTINGS['embedding-model'],
        input=query
    )
    query_embedding = query_embedding_response.data[0].embedding
    
    # Get the most relevant texts
    strings, relatedness = strings_ranked_by_relatedness(query_embedding, df)

    introduction = 'Use the below segments about Howard University to answer the subsequent question. If the answer could not be found in the segments then write "I could not find an answer."'
    question = f"\n\nQuestion: {query}"

    message = introduction
    for string in strings:
        next_segment = f'\n\nHoward Catalogue segment:\n"""{string}"""\n'
        if num_tokens(message + next_segment + question, model=model) > token_budget:
            break
        message += next_segment
    return message + question

async def ask(query, df, model=SETTINGS["gpt-model"], token_budget=4096-250):
    message = await query_message(query, df, model=model, token_budget=token_budget)

    messages = [
        {'role': 'system', 'content': 'You answer questions about Howard University.'},
        {'role': 'user', 'content': message},
    ]

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=SETTINGS['temperature']
    )
    return response.choices[0].message.content

conversation_history = []

@cl.on_chat_start
async def on_chat_start():
    global conversation_history
    conversation_history = []
    await cl.Message(content="Hello, welcome to BisonGPT! How can I help you today?").send()

@cl.on_message
async def on_message(message: cl.Message):
    global conversation_history
    response = await ask(message.content, df=SETTINGS['df'])
    await cl.Message(content=response).send()