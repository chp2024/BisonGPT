from openai import OpenAI

class BisonGPTAssistant:
    def __init__(self):
        self.client = OpenAI()
        self.assistant_id = "asst_vYCjSoAiA4M4CdDnLHYzGH0b"

    def on_chat_start(self):
        welcome_thread = self.client.beta.threads.create()
        welcome_message = self.client.beta.threads.messages.create(
            thread_id=welcome_thread.id,
            role="assistant",
            content="Hello, Welcome to BisonGPT. How may I help you today?"
        )
        return welcome_thread, welcome_message

    def create_conversation(self, message=None):
        new_thread = self.client.beta.threads.create()
        new_message, run = None, None
        if message:
            new_message = self.client.beta.threads.messages.create(
                thread_id=new_thread.id,
                role="user",
                content=message
            )
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=new_thread.id,
                assistant_id=self.assistant_id
            )
        else:
            new_thread, new_message = self.on_chat_start()
        return new_thread, new_message, run
