import chainlit as cl
from chainlit.config import config
from openai import AsyncOpenAI, AsyncAssistantEventHandler, OpenAI
from urllib.parse import quote
from pathlib import Path
from typing import List
from chainlit.element import Element

# Initialize OpenAI clients
client = OpenAI()
async_client = AsyncOpenAI()

# Retrieve assistant details
assistant = client.beta.assistants.retrieve(assistant_id="asst_TIwxYMA4iJar5MbFxOs9o3zy")
config.ui.name = assistant.name

class EventHandler(AsyncAssistantEventHandler):
    def __init__(self, assistant_name: str) -> None:
        super().__init__()
        self.current_message: cl.Message = None
        self.current_step: cl.Step = None
        self.assistant_name = assistant_name

    async def on_text_created(self, text) -> None:
        self.current_message = await cl.Message(author=self.assistant_name, content="").send()

    async def on_text_delta(self, delta, snapshot):
        if delta.value:
            await self.current_message.stream_token(delta.value)

    async def on_text_done(self, text):
        await self.current_message.update()

        if text.annotations:
            citations = []
            for index, annotation in enumerate(text.annotations):
                if annotation.type == "file_citation":
                    if annotation.text in self.current_message.content:
                        self.current_message.content = self.current_message.content.replace(annotation.text, f"[{index + 1}]")

                    if file_citation := getattr(annotation, "file_citation", None):
                        cited_file = await async_client.files.retrieve(file_citation.file_id)
                        citations.append(f"[{index + 1}]: {cited_file.filename}")

            if citations:
                self.current_message.content += "\n\nCitations:\n" + "\n".join(citations)
                await self.current_message.update()

    async def on_event(self, event) -> None:
        if event.event == "thread.run.requires_action":
            run_id = event.data.id
            await self.handle_requires_action(event.data, run_id)
        if event.event == "error":
            await cl.ErrorMessage(content=str(event.data.message)).send()

    async def handle_requires_action(self, data, run_id):
        import json
        tool_outputs = []
        for tool_call in data.required_action.submit_tool_outputs.tool_calls:
            if tool_call.function.name == "get_directions":
                arguments = json.loads(tool_call.function.arguments)
                address = arguments.get("address")
                google_maps_link = await self.get_directions(address)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": f"Directions: {google_maps_link}"
                })

        await self.submit_tool_outputs(tool_outputs, run_id)

    async def submit_tool_outputs(self, tool_outputs, run_id):
        thread_id = cl.user_session.get("thread_id")
        async with async_client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs,
            event_handler=EventHandler(self.assistant_name),
        ) as stream:
            await stream.until_done()


    async def on_exception(self, exception: Exception) -> None:
        await cl.ErrorMessage(content=str(exception)).send()

    async def get_directions(self, address: str) -> str:
        from urllib.parse import quote

        base_url = "https://www.google.com/maps/dir/?api=1"
        encoded_address = quote(address)
        return f"{base_url}&origin=current+location&destination={encoded_address}"
    
async def upload_files(files: List[Element]):
    file_ids = []
    for file in files:
        uploaded_file = await async_client.files.create(
            file=Path(file.path), purpose="assistants"
        )
        file_ids.append(uploaded_file.id)
    return file_ids

async def process_files(files: List[Element]):
    file_ids = await upload_files(files) if files else []

    return [
        {
            "file_id": file_id,
            "tools": [{"type": "file_search"}] if file.mime in ["text/markdown", "application/pdf", "text/plain", "application/json"] else [{"type": "code_interpreter"}],
        }
        for file_id, file in zip(file_ids, files)
    ]

@cl.on_chat_start
async def start_chat():
    thread = await async_client.beta.threads.create()
    cl.user_session.set("thread_id", thread.id)

@cl.on_stop
async def stop_chat():
    current_run_step = cl.user_session.get("run_step")
    if current_run_step:
        await async_client.beta.threads.runs.cancel(thread_id=current_run_step.thread_id, run_id=current_run_step.run_id)

@cl.on_message
async def main(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")

    if message.author == "bot":
        print(message.content)
        return

    # Handle message content and optional file attachment
    attachments = await process_files(message.elements)

    # Add a Message to the Thread
    new_message = await async_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message.content,
        attachments=attachments,
    )

    # Create and Stream a Run
    async with async_client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant.id,
        event_handler=EventHandler(assistant_name=assistant.name),
    ) as stream:
        await stream.until_done()
