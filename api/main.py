import os
import asyncio
import io
import json
import uuid
import urllib.parse
import httpx

from google import genai
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from datetime import datetime
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any
from bson import ObjectId
from weasyprint import HTML, CSS



load_dotenv()
MONGO_DB = os.getenv("MONGO_DB")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_API_URL = os.getenv("MONGO_API_URL")
MONGO_URL = os.getenv("MONGO_URL")
gemini_client = genai.Client()
model_id = "gemini-2.5-flash"

mongo_client = AsyncIOMotorClient(MONGO_DB)
db = mongo_client.get_database()

app = FastAPI()

class LastRequestData(BaseModel):
    topic: str
    current_level: str
    target_level: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "topic": "Английский для бизнеса",
                "current_level": "A1",
                "target_level": "B1"
            }
        }
    }

class UserLanguageUpdate(BaseModel):
    language_code: str

class UserData(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None
    language_code: str | None = None
    last_request: LastRequestData | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "telegram_id": 123456789,
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
                "language_code": "en",
                "last_request":{
                    "topic": "English Bussines",
                    "current_level": "A1",
                    "target_level": "B1"                  
                }
            }
        }
    }

class UserUpdateData(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None

async def getUser(id, limit=0, skip=0):
    async with httpx.AsyncClient() as client:
        url = f"{MONGO_API_URL}?mongo_url={MONGO_URL}&db_name=Studiora&collection_name=users"
        mongo_filter = {"_id": id}

        filter_json_str = json.dumps(mongo_filter)
        encoded_filter = urllib.parse.quote_plus(filter_json_str)

        url += f"&filter_json={encoded_filter}"
        url += f"&limit={limit}&skip={skip}"
        try:
            response = await client.get(url)
            response.raise_for_status()
            user= (response.json())["data"][0] if (response.json())["count"] > 0 else None
        except Exception as e:
            print(f"Fetch error: {e}")
            raise HTTPException(status_code=500, detail="Fetch error.")
    
        return user
    
async def updateUser(telegram_id, update_data):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(MONGO_API_URL, json={
                "db_name": "Studiora",
                "collection_name": "users",
                "filter":{"_id": telegram_id},
                "update":update_data,
                "mongo_url": MONGO_URL
            })
            response.raise_for_status()
            print(response.json())
        except Exception as e:
            print(f"Fetch error: {e}")
            raise HTTPException(status_code=500, detail="Fetch error.")
    
    
@app.post("/users")
async def create_user(user: UserData):
    existing_user = await getUser(user.telegram_id)

    if not existing_user:
        user_data_dict = user.model_dump()
        user_data_dict["_id"] = user_data_dict["telegram_id"]
        del user_data_dict["telegram_id"]

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(MONGO_API_URL, json={
                    "db_name": "Studiora",
                    "collection_name": "users",
                    "data": user_data_dict,
                    "mongo_url": MONGO_URL
                })
                response.raise_for_status()
            except Exception as e:
                print(f"Fetch error: {e}")
                raise HTTPException(status_code=500, detail="Fetch error.")

    return {"message": "User created or already existed"}
    
@app.get("/users/{telegram_id}", response_model=UserData)
async def get_user_data(telegram_id: int):
    user = await getUser(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user['telegram_id'] = user['_id']
    return UserData(**user)

    
@app.patch("/users/{telegram_id}/language")
async def update_user_language(telegram_id: int, lang_update: UserLanguageUpdate):
    await updateUser(
        telegram_id,
        {"$set": {"language_code": lang_update.language_code}}
    )
    return {"message": "User language update attempted"}


@app.get("/users/{telegram_id}/lesson_details", response_class=Response)
async def get_user_lesson_details(telegram_id: int):
    user = await getUser(telegram_id)

    lesson_language = user.get('language_code', 'en')
    last_request_data = user.get("last_request")

    if isinstance(last_request_data, str):
        last_request_data = json.loads(last_request_data)

    topic = last_request_data.get('topic', 'General Knowledge')
    current_level = last_request_data.get('current_level', 'Beginner')
    target_level = last_request_data.get('target_level', 'Intermediate')

    prompt = f"""
        Create a detailed educational lesson as an HTML document.

        Topic: "{topic}"  
        Current level: {current_level}  
        Target level: {target_level}
        Lesson Language: {lesson_language}

        The lesson must include:
        1. Introduction
        2. Key concepts and theory
        3. Examples with explanations
        4. Practice exercises (at least 3)
        5. Summary and study tips
        6. Self-check questions (5 questions with answers)

        Requirements:
        - Use **HTML5** only.
        - Use tags like <h1>, <h2>, <p>, <ul>, <ol>, <li>, <strong>, <em>, <code>, <hr>.
        - Do not include CSS or JavaScript — pure HTML only.
        - Do not include <html>, <head>, or <body> tags — only the content inside.
        - Make sure formatting is clean and suitable for PDF conversion.

        Content must be understandable for a student at {current_level} and help reach {target_level}.
    """

    response = await gemini_client.aio.models.generate_content(
        model=model_id,
        contents=prompt,
    )

    lesson_html = response.text

    pdf_bytes = io.BytesIO()
    HTML(string=lesson_html).write_pdf(pdf_bytes)
    pdf_bytes.seek(0)

    unique_id = str(uuid.uuid4())
    sanitized_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).rstrip()
    filename = f"{sanitized_topic.replace(' ', '_').lower()}_{unique_id}.pdf"

    user_pdf_dir = os.path.join("db", str(telegram_id))
    os.makedirs(user_pdf_dir, exist_ok=True)
    file_path = os.path.join(user_pdf_dir, filename)

    with open(file_path, "wb") as f:
        f.write(pdf_bytes.getvalue())

    await updateUser(
        telegram_id,
        {"$push": {"pdf_files": filename}}
    )

    encoded_filename = urllib.parse.quote(filename)

    await updateUser(
        telegram_id,
        {"$unset": {"last_request": ""}}
    )

    return Response(
        content=pdf_bytes.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"file.pdf\"; filename*=UTF-8''{encoded_filename}"
        }
    )

@app.post("/users/{telegram_id}/last_request")
async def save_last_request(telegram_id: int, request: Request):
        data = await request.json()

        if not data or not any(data.values()):
            update_operation = {"$unset": {"last_request": ""}}
        else:
            update_operation = {"$set": {"last_request": {
                "topic": data.get("topic", ""),
                "current_level": data.get("current_level", ""),
                "target_level": data.get("target_level", "")
            }}}
        
        await updateUser(
            telegram_id,
            update_operation
        )

        return {"message": "Last request saved successfully"}


@app.get("/users/{user_id}/history")
async def get_user_history(user_id: int, skip: int = 0, limit: int = 5):
    user_dir = os.path.join("db", str(user_id))
    if not os.path.exists(user_dir):
        return {"pdf_files": [], "total_count": 0}
    
    all_files_with_timestamps = []
    for f in os.listdir(user_dir):
        if f.endswith(".pdf"):
            file_path = os.path.join(user_dir, f)
            timestamp = os.path.getmtime(file_path)
            all_files_with_timestamps.append((f, timestamp))

    all_files_with_timestamps.sort(key=lambda x: x[1], reverse=True)
    
    pdf_files = [f_name for f_name, _ in all_files_with_timestamps]

    total_count = len(pdf_files)
    paginated_files = pdf_files[skip:skip + limit]

    return {"pdf_files": paginated_files, "total_count": total_count}