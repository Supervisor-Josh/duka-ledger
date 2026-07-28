import asyncio
import json
import re
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env
load_dotenv()

app = FastAPI()

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else genai.Client()

# Payload Schema for SMS Endpoint
class SMSPayload(BaseModel):
    raw_text: str

# Schema for structured Gemini OCR output
class ReceiptData(BaseModel):
    merchant_name: str
    total_amount: float
    items_count: int


@app.get("/api/health")
def health():
    return {"status": "Ledger backend online"}


# ENGINE 1: M-PESA SMS PARSER (UNTOUCHED)
@app.post("/api/parse-sms")
async def parse_sms(payload: SMSPayload):
    text = payload.raw_text

    match = re.search(
        r"([A-Z0-9]+)\s+Confirmed\.\s+Ksh([\d,]+\.?\d*)\s+(sent to|received from)\s+([^on]+)",
        text,
        re.IGNORECASE
    )

    if not match:
        return {
            "status": "error",
            "message": "Unrecognized or unsupported M-Pesa SMS format",
            "data": None
        }

    tx_code, amount_str, direction, party = match.groups()
    is_income = "received" in direction.lower()

    parsed_data = {
        "transaction_id": tx_code.strip(),
        "amount": float(amount_str.replace(",", "")),
        "sender": party.strip(),
        "type": "INCOME" if is_income else "EXPENSE",
        "raw": text
    }

    return {"status": "success", "data": parsed_data}


# ENGINE 2: RECEIPT OCR SCANNER (WITH AUTOMATED RETRY / WAIT TIME)
@app.post("/api/scan-receipt")
async def scan_receipt(file: UploadFile = File(...)):
    image_bytes = await file.read()

    prompt = """
    Analyze this receipt image. 
    Extract the merchant or shop name, the total amount spent, and the total count of distinct items purchased.
    Respond STRICTLY with valid JSON following the schema.
    """

    max_retries = 3
    base_delay = 5  # Default wait time in seconds if no retryDelay is given by Gemini

    for attempt in range(1, max_retries + 1):
        try:
            print(f"--> [Attempt {attempt}/{max_retries}] Processing receipt OCR request...")

            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=file.content_type),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ReceiptData,
                ),
            )

            receipt_json = json.loads(response.text)

            parsed_expense = {
                "transaction_id": f"REC-{receipt_json.get('merchant_name', 'UNKNOWN')[:8].upper()}",
                "amount": receipt_json.get("total_amount", 0.0),
                "sender": receipt_json.get("merchant_name", "Scanned Receipt"),
                "type": "EXPENSE",
                "raw": f"OCR Scan ({receipt_json.get('items_count', 0)} items)"
            }

            return {
                "status": "success",
                "filename": file.filename,
                "parsed_expense": parsed_expense
            }

        except Exception as e:
            error_str = str(e)
            print(f"Attempt {attempt} failed: {error_str}")

            # Check for Rate Limit / Quota limits
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt == max_retries:
                    raise HTTPException(
                        status_code=429,
                        detail="Gemini API rate limit reached after retries. Please wait 1 minute."
                    )

                # Parse the exact retry delay from Google's error string if available
                delay_match = re.search(r"retryDelay':\s*'(\d+)s'", error_str)
                wait_seconds = int(delay_match.group(1)) + 1 if delay_match else (base_delay * attempt)

                print(f"[Rate Limit 429] Waiting {wait_seconds} seconds before attempt #{attempt + 1}...")
                await asyncio.sleep(wait_seconds)
            else:
                # Raise other server/parsing errors immediately
                raise HTTPException(status_code=500, detail=f"OCR Processing failed: {error_str}")