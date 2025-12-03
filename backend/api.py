from fastapi import FastAPI,HTTPException,Depends,Request
import uvicorn
import hmac
import hashlib
import json
import os
from dotenv import load_dotenv




load_dotenv()
app = FastAPI()
@app.get("/")
async def main():
    return "AI-GIRL"

async def safe_get(req:Request):
    api = req.headers.get("X-API-KEY")
    api_main = os.getenv("API")
    if not api or not hmac.compare_digest(api,api_main):
        raise HTTPException(status_code = 401,detail = "Invalid api key")

