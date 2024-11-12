from assistant import BisonGPTAssistant
import chainlit as cl
from chainlit.config import config
from openai import AsyncOpenAI, AsyncAssistantEventHandler, OpenAI
from openai.types.beta.threads.runs import RunStep
from datetime import datetime

# Initialize OpenAI clients
client = OpenAI()
async_client = AsyncOpenAI()

# Retrieve assistant details
assistant = client.beta.assistants.retrieve(assistant_id="asst_CaLmP9XKfyDymTvAANcBt4AR")
config.ui.name = assistant.name

# Utility function for current UTC time
def utc_now():
    return datetime.now().isoformat()

class EventHandler(AsyncAssistantEventHandler):
    def __init__(self, assistant_name) -> None:
        super().__init__()
        self.current_message = None
        self.current_step = None
        self.current_tool_call = None
        self.assistant_name = assistant_name

    async def on_run_step_created(self, run_step: RunStep) -> None:
        cl.user_session.set("run_step", run_step)

    async def on_text_created(self, text):
        self.current_message = await cl.Message(author=self.assistant_name, content="").send()

    async def on_text_delta(self, delta, snapshot):
        if delta.value:
            await self.current_message.stream_token(delta.value)

    async def on_text_done(self, text):
        await self.current_message.update()

    async def on_tool_call_created(self, tool_call):
        self.current_tool_call = tool_call.id
        self.current_step = cl.Step(
            name=tool_call.type,
            type="tool",
            parent_id=cl.context.current_run.id,
        )
        self.current_step.show_input = "python"
        await self.current_step.send()

    async def on_tool_call_delta(self, delta, snapshot): 
        if snapshot.id != self.current_tool_call:
            self.current_tool_call = snapshot.id
            self.current_step = cl.Step(name=delta.type, type="tool", parent_id=cl.context.current_run.id)
            self.current_step.start = utc_now()
            if snapshot.type == "code_interpreter":
                self.current_step.show_input = "python"
            if snapshot.type == "function":
                self.current_step.name = snapshot.function.name
                self.current_step.language = "json"
            await self.current_step.send()

        if delta.type == "code_interpreter" and delta.code_interpreter.outputs:
            for output in delta.code_interpreter.outputs:
                if output.type == "logs":
                    self.current_step.output += output.logs
                    self.current_step.language = "markdown"
                    self.current_step.end = utc_now()
                    await self.current_step.update()
                elif output.type == "image":
                    self.current_step.language = "json"
                    self.current_step.output = output.image.model_dump_json()
        elif delta.code_interpreter.input:
            await self.current_step.stream_token(delta.code_interpreter.input, is_input=True)

    async def on_event(self, event) -> None:
        if event.event == "error":
            await cl.ErrorMessage(content=str(event.data.message)).send()

    async def on_exception(self, exception: Exception) -> None:
        await cl.ErrorMessage(content=str(exception)).send()

    async def on_tool_call_done(self, tool_call):       
        self.current_step.end = utc_now()
        await self.current_step.update()

@cl.on_chat_start
async def start_chat():
    thread = await async_client.beta.threads.create()
    message = await async_client.beta.threads.messages.create(
        thread_id=thread.id,
        role="assistant",
        content="Hello, Welcome to BisonGPT. How may I help you today?"
    )

    cl.user_session.set("thread_id", thread.id)

    await cl.Message(content="Hello, Welcome to BisonGPT. How may I help you today?").send()

@cl.on_stop
async def stop_chat():
    current_run_step = cl.user_session.get("run_step")
    if current_run_step:
        await async_client.beta.threads.runs.cancel(thread_id=current_run_step.thread_id, run_id=current_run_step.run_id)

@cl.on_message
async def main(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")

    # Add a Message to the Thread
    new_message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message.content
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant.id,
    )

    m = list(client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id))

    message_content = m[0].content[0].text
    await cl.Message(content=message_content.value).send()

    # Create and Stream a Run
    # async with async_client.beta.threads.runs.stream(
    #     thread_id=thread_id,
    #     assistant_id=assistant.id,
    #     event_handler=EventHandler(assistant_name=assistant.name),
    # ) as stream:
    #     await stream.until_done()
