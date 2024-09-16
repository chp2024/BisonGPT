import tiktoken
import os
import dotenv
import asyncio
import hashlib
import pandas as pd
from openai import AsyncOpenAI
from pinecone import Pinecone, ServerlessSpec

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 10
INDEX_NAME = "bisongpt-index"

dotenv.load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

if not pc.has_index(INDEX_NAME):
    pc.create_index(
        INDEX_NAME, dimension=1536, spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(INDEX_NAME)

EMBEDDING_MODEL = "text-embedding-3-small"


def num_tokens(text, model):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def generate_id(header, subheader, content):
    data = f"{header} {subheader} {content}".encode("utf-8")
    return hashlib.md5(data).hexdigest()


def split_by_size_recursive(
    header, subheader, content, max_tokens=1000, model=EMBEDDING_MODEL
):
    encoding = tiktoken.encoding_for_model(model)

    full_text = f"{header} {subheader} {content}".strip()
    # Stop infinite recursion: If the header and subheader alone exceed the max_token count return the whole text
    header_tokens = encoding.encode(f"{header} {subheader}".strip())
    if len(header_tokens) > max_tokens:
        return [(full_text, generate_id(header, subheader, content))]

    # Calculate tokens for the full text (header + subheader + content)
    full_text_tokens = encoding.encode(full_text)

    if len(full_text_tokens) <= max_tokens:
        return [(full_text, generate_id(header, subheader, content))]

    content_tokens = encoding.encode(content)

    midpoint = len(content_tokens) // 2
    first_half = encoding.decode(content_tokens[:midpoint])
    second_half = encoding.decode(content_tokens[midpoint:])

    # Recursively split the content, but keep header and subheader intact
    return split_by_size_recursive(
        header, subheader, first_half, max_tokens, model
    ) + split_by_size_recursive(header, subheader, second_half, max_tokens, model)


async def process_row(row):
    header = row["Header"]
    subheader = (
        "" if pd.isna(row["Sub-header"]) else row["Sub-header"]
    )  # Check if subheader exists
    content = row["Content"]

    return split_by_size_recursive(
        header, subheader, content, max_tokens=1000, model=EMBEDDING_MODEL
    )


async def generate_batch_embeddings(text_batch):
    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL, input=text_batch
        )
        return response.data
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return []


async def main():
    input_csv = "BisonGPT/Data/20232024-formatted-undergraduate-catalogue.csv"
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Gather text chunks from all rows
    all_text_chunks = []
    for _, row in df.iterrows():
        text_chunks = await process_row(row)
        all_text_chunks.extend(text_chunks)

    # Create batches of text chunks
    texts, ids = zip(*all_text_chunks)

    # Create batches of text chunks
    text_batches = [texts[i : i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]
    id_batches = [ids[i : i + BATCH_SIZE] for i in range(0, len(ids), BATCH_SIZE)]

    # Process each batch asynchronously
    for text_batch, id_batch in zip(text_batches, id_batches):
        batch_embeddings = await generate_batch_embeddings(text_batch)

        # Create a list of vectors with (id, embedding)
        vectors = [
            {
                "id": id_batch[i],
                "values": embedding.embedding,
                "metadata": {"text": text_batch[i]},
            }
            for i, embedding in enumerate(batch_embeddings)
        ]

        index.upsert(vectors=vectors, namespace="howard-catalogue")

        print(
            f"Batch {text_batches.index(text_batch) + 1} of {len(text_batches)} batches processed"
        )

    print("All embeddings saved to Pinecone")


if __name__ == "__main__":
    asyncio.run(main())
