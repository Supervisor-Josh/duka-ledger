import os
import re
from datetime import datetime
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai import types
from PIL import Image
import io

app = FastAPI()

# Initialize the Gemini Client (it automatically looks for the GEMINI_API_KEY env variable)
client = genai.Client()

# --- Unified Data Schema ---
class LedgerEntry(BaseModel):
    transaction_id: str = Field(description="Extracted unique serial/receipt number or reference code")
    source: str = Field(description="Must explicitly be 'receipt_ocr'")
    timestamp: str = Field(description="ISO format timestamp found on receipt, or current time if missing")
    flow_type: str = Field(description="Must explicitly be 'expense'")
    amount: float = Field(description="The final total numeric amount paid, stripped of symbols and commas")
    party_name: str = Field(description="The business header or vendor name at the top of the receipt")
    items_detected: List[str] = Field(default=[], description="List of raw inventory items discovered (e.g., Tomatoes, Onions)")

# Schema for incoming SMS requests
class SMSResponse(BaseModel):
    transaction_id: str
    source: str
    timestamp: str
    flow_type: str
    amount: float
    party_name: str
    items_detected: List[str] = []

@app.get("/api/health")
def health():
    return {"status": "Ledger backend online"}

# --- ENGINE 1: M-PESA SMS PARSER ---
@app.post("/api/parse-sms", response_model=SMSResponse)
def parse_sms(raw_text: str = Form(...)):
    text = raw_text.strip()
    tx_match = re.match(r"^([A-Z0-9]{10})", text)
    if not tx_match:
        raise HTTPException(status_code=400, detail="Invalid statement format: Missing Transaction ID")
    tx_id = tx_match.group(1)
    
    if "received" in text.lower():
        flow_type = "income"
        amt_match = re.search(r"received\s+Ksh([\d,]+\.\d{2})", text, re.IGNORECASE)
        party_match = re.search(r"from\s+([A-Z\s]+?)\s+on", text, re.IGNORECASE)
    elif "paid to" in text.lower() or "sent to" in text.lower():
        flow_type = "expense"
        amt_match = re.search(r"Ksh([\d,]+\.\d{2})\s+(?:paid|sent)\s+to", text, re.IGNORECASE)
        party_match = re.search(r"(?:paid|sent)\s+to\s+([A-Z0-9\s\.]+?)\s+on", text, re.IGNORECASE)
    else:
        raise HTTPException(status_code=400, detail="Unable to determine financial flow direction")

    amount = float(amt_match.group(1).replace(",", "")) if amt_match else 0.0
    party_name = party_match.group(1).strip() if party_match else "Unknown Counterparty"
    
    return SMSResponse(
        transaction_id=tx_id,
        source="sms_parsing",
        timestamp=datetime.now().isoformat(),
        flow_type=flow_type,
        amount=amount,
        party_name=party_name,
        items_detected=[]
    )

# --- ENGINE 2: REAL PHOTO-TO-TEXT RECEIPT OCR ---
@app.post("/api/scan-receipt", response_model=LedgerEntry)
async def scan_receipt(file: UploadFile = File(...)):
    try:
        # 1. Read the uploaded raw binary file bytes into memory
        file_bytes = await file.read()
        
        # 2. Convert bytes into a valid PIL Image object for the Gemini SDK
        image = Image.open(io.BytesIO(file_bytes))
        
        # 3. Formulate a crisp prompt detailing exactly how to clean the data
        prompt = (
            "Analyze this business purchase receipt image. Extract the business name, total cost, "
            "items, and receipt/serial numbers. Return the structured mapping following the provided schema constraint."
        )
        
        # 4. Call the multimodal flash model with strict structured JSON output definitions
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LedgerEntry,
                temperature=0.1,  # Kept low for high data extraction accuracy
            ),
        )
        
        # 5. Parse out the string JSON payload directly into our Pydantic response format
        return LedgerEntry.model_validate_json(response.text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini processing engine failure: {str(e)}")
