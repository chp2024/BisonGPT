import tiktoken
import os
import dotenv
import asyncio
import pandas as pd
from openai import AsyncOpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 10

dotenv.load_dotenv()

client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def num_tokens(text, model):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def split_by_size_recursive(text, max_tokens=1000, model=EMBEDDING_MODEL):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        return [text]
    
    midpoint = len(tokens) // 2
    first_half = encoding.decode(tokens[:midpoint])
    second_half = encoding.decode(tokens[midpoint:])

    return split_by_size_recursive(first_half, max_tokens, model) + split_by_size_recursive(second_half, max_tokens, model)

async def generate_batch_embeddings(text_batch):
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=text_batch)
    return response.data

async def process_row(row):
    # Format text with header, sub-header, and content
    header = row['Header']
    subheader = '' if row['Sub-header'] == 'nan' else row['Sub-header'] # Check if subheader exists
    content = row['Content']

    # Concatenate text components, checking for missing subheaders
    text = f"{header} {subheader} {content}".strip()
    return split_by_size_recursive(text, max_tokens=1000, model=EMBEDDING_MODEL)


async def main():
    input_csv = "BisonGPT/Data/20232024-formatted-undergraduate-catalogue.csv"
    output_csv = "BisonGPT/Data/20232024-embeddings.csv"
    df = pd.read_csv(input_csv)

    embeddings_list = []
    
    # Gather text chunks from all rows
    all_text_chunks = []
    for _, row in df.iterrows():
        text_chunks = await process_row(row)
        all_text_chunks.extend(text_chunks)
    
    # Create batches of text chunks
    text_batches = [all_text_chunks[i:i + BATCH_SIZE] for i in range(0, len(all_text_chunks), BATCH_SIZE)]
    
    # Process each batch asynchronously
    for batch in text_batches:
        batch_embeddings = await generate_batch_embeddings(batch)
        for i, embedding in enumerate(batch_embeddings):
            embeddings_list.append({'text': batch[i], 'embedding': embedding.embedding})
        print(f"Batch {text_batches.index(batch)} of {len(text_batches)-1} batches processed")

    
    # Convert the list of embeddings into a DataFrame
    embeddings_df = pd.DataFrame(embeddings_list)
    
    # Save the embeddings DataFrame to CSV
    embeddings_df.to_csv(output_csv, index=False)
    print(f"Embeddings saved to {output_csv}")

if __name__ == "__main__":
    asyncio.run(main())