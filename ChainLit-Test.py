from openai import AsyncOpenAI

import chainlit as cl

client = AsyncOpenAI()

cl.instrument_openai()

settings = {
    "model": "gpt-3.5-turbo",
    "temperature": 0,
}

conversation_history = []

@cl.on_chat_start
async def on_chat_start():
    global conversation_history
    conversation_history = []
    await cl.Message(content="Hello, welcome to BisonGPT! How can I help you today?").send()


@cl.on_message
async def on_message(message: cl.Message):
    global conversation_history
    
    # Add the user's message to the conversation history
    conversation_history.append({"content": message.content, "role": "user"})
    
    # Request a response from OpenAI, including the conversation history
    response = await client.chat.completions.create(
        messages=[
            {
                "content": "You are a helpful and concise bot, you respond to any message in 200 characters or less.",
                "role": "system"
            }
        ] + conversation_history,
        **settings
    )
    
    conversation_history.append({"content": response.choices[0].message.content, "role": "user"})
    
    await cl.Message(content=response.choices[0].message.content).send()
