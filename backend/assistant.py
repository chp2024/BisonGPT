from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override

class BisonGPTEventHandler(AssistantEventHandler):  
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    #Need to fix
    # @override
    # def on_message_done(self, message) -> None:
    #     # print a citation to the file searched
    #     message_content = message.content[0].text
    #     annotations = message_content.annotations
    #     citations = []
    #     for index, annotation in enumerate(annotations):
    #         message_content.value = message_content.value.replace(
    #             annotation.text, f"[{index}]"
    #         )
    #         if file_citation := getattr(annotation, "file_citation", None):
    #             cited_file = client.files.retrieve(file_citation.file_id)
    #             citations.append(f"[{index}] {cited_file.filename}")

    #     print(message_content.value)
    #     print("\n".join(citations))

class BisonGPTAssistant:
    def __init__(self):
        self.client = OpenAI()
        self.assistant_id = ""
        self.instructions = ""
        self.event_handler = BisonGPTEventHandler()

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
    
    # Experimental for now
    def stream_message(self, thread_id, message, file=None):
        if file:
            file_response = self.client.files.create(
                file=open(file, 'rb'),
                purpose="assistants"
            )
            file_id = file_response.id
            updated_thread = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message,
                attachments=[
                    {
                        "file_id": file_id,
                        "tools": [{"type": "file_search"}] 
                    }
                ]
            )
        else:
            updated_thread = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )

        with self.client.beta.threads.runs.stream(
            assistant_id=self.assistant_id,
            thread_id=updated_thread.id,
            instructions=self.instructions,
            event_handler=BisonGPTEventHandler()
        ) as stream:
            return stream
        
    def send_message(self, thread_id, message, file=None):
        if file:
            file_response = self.client.files.create(
                file=open(file, 'rb'),
                purpose="assistants"
            )
            file_id = file_response.id
            updated_thread = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message,
                attachments=[
                    {
                        "file_id": file_id,
                        "tools": [{"type": "file_search"}] 
                    }
                ]
            )
        else:
            updated_thread = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=updated_thread.id,
            assistant_id=self.assistant_id
        )

        messages = list(self.client.beta.threads.messages.list(thread_id=updated_thread.id, run_id=run.id))

        message_content = messages[0].content[0].text
        return message_content.value

        


