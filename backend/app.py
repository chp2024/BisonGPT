from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from chainlit.auth import create_jwt
from chainlit.user import User
from chainlit.utils import mount_chainlit
from PyPDF2 import PdfReader
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/custom-auth")
async def custom_auth():
    token = create_jwt(User(identifier="Test User"))
    return JSONResponse({"token": token})

@app.post("/api/upload-message")
async def upload_message(file: UploadFile = File(None), message: str = Form("")):
    file_content = ""
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Extract content if it's a PDF file
        if file.filename.endswith(".pdf"):
            try:
                pdf_reader = PdfReader(file_path)
                file_content = " ".join([page.extract_text() for page in pdf_reader.pages])
            except Exception as e:
                return JSONResponse({"message": "Failed to process PDF file", "error": str(e)})

    # Combine the file content and message for chatbot processing
    combined_input = f"{message}\n\n{file_content}" if file_content else message

    # Mock response for now (replace with actual chatbot logic)
    response = "I could not find an answer." if not file_content else f"File content received: {file_content[:200]}..."

    return JSONResponse({
        "message": combined_input,
        "file": {"filename": file.filename, "content": file_content} if file else None,
        "response": response,
    })

mount_chainlit(app=app, target="cl_app.py", path="/chainlit")
