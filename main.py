import os
import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import re

app = FastAPI(title="Credit Card BIN Lookup API", version="1.0.0")
# === BT Builds Standard Middleware (auto-injected) ===
from fastapi.middleware.cors import CORSMiddleware as _BTCors
app.add_middleware(_BTCors, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], expose_headers=["X-RateLimit-Limit","X-RateLimit-Remaining","X-RateLimit-Reset"])

@app.middleware("http")
async def _bt_add_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Powered-By"] = "btbuilds"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# Auth & rate limiting
API_KEYS = set(filter(None, os.environ.get("API_KEYS", "free-demo-key").split(",")))
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MIN", "60"))
_req_counts: dict = defaultdict(list)

def auth(x_api_key: str = Header(default="free-demo-key")):
    if x_api_key not in API_KEYS:
        raise HTTPException(401, "Invalid API key")
    now = time.time()
    window = [t for t in _req_counts[x_api_key] if now - t < 60]
    window.append(now)
    _req_counts[x_api_key] = window
    if len(window) > RATE_LIMIT:
        raise HTTPException(429, f"Rate limit: {RATE_LIMIT} req/min")

# Static BIN database (major card ranges)
BIN_DATABASE = {
    # Visa
    "4532": {"brand": "Visa", "type": "Credit", "bank": "Chase Bank USA", "country": "USA", "country_code": "US"},
    "4556": {"brand": "Visa", "type": "Credit", "bank": "Bank of America", "country": "USA", "country_code": "US"},
    "4111": {"brand": "Visa", "type": "Credit", "bank": "Test Card Issuer", "country": "USA", "country_code": "US"},
    "4012": {"brand": "Visa", "type": "Debit", "bank": "Test Card Issuer", "country": "USA", "country_code": "US"},
    "4024": {"brand": "Visa", "type": "Credit", "bank": "Wells Fargo", "country": "USA", "country_code": "US"},
    # Mastercard - ranges
    "5105": {"brand": "Mastercard", "type": "Credit", "bank": "Barclays Bank", "country": "UK", "country_code": "GB"},
    "5555": {"brand": "Mastercard", "type": "Credit", "bank": "Test Card Issuer", "country": "USA", "country_code": "US"},
    "5490": {"brand": "Mastercard", "type": "Credit", "bank": "HSBC Bank", "country": "UK", "country_code": "GB"},
    "5199": {"brand": "Mastercard", "type": "Debit", "bank": "Deutsche Bank", "country": "Germany", "country_code": "DE"},
    # American Express
    "3782": {"brand": "American Express", "type": "Credit", "bank": "American Express", "country": "USA", "country_code": "US"},
    "3714": {"brand": "American Express", "type": "Credit", "bank": "American Express", "country": "USA", "country_code": "US"},
    # Discover
    "6011": {"brand": "Discover", "type": "Credit", "bank": "Discover Bank", "country": "USA", "country_code": "US"},
    "6012": {"brand": "Discover", "type": "Debit", "bank": "Discover Bank", "country": "USA", "country_code": "US"},
    # Diners Club
    "3000": {"brand": "Diners Club", "type": "Credit", "bank": "Diners Club International", "country": "USA", "country_code": "US"},
    # JCB
    "3566": {"brand": "JCB", "type": "Credit", "bank": "JCB International", "country": "Japan", "country_code": "JP"},
}

# Pattern matching for BIN ranges
BIN_PATTERNS = [
    (r"^4[0-9]{12}(?:[0-9]{3})?$", "Visa", "Credit", "Visa Inc.", "USA", "US"),
    (r"^5[1-5][0-9]{14}$", "Mastercard", "Credit", "Mastercard Inc.", "USA", "US"),
    (r"^3[47][0-9]{13}$", "American Express", "Credit", "American Express", "USA", "US"),
    (r"^6(?:011|5[0-9]{2})[0-9]{12}$", "Discover", "Credit", "Discover Bank", "USA", "US"),
    (r"^35(?:2[89]|[3-8][0-9])[0-9]{12}$", "JCB", "Credit", "JCB Co.", "Japan", "JP"),
    (r"^30[0-5][0-9]{11}$", "Diners Club", "Credit", "Diners Club", "USA", "US"),
]

class BINLookupRequest(BaseModel):
    bin: str

class BINLookupResponse(BaseModel):
    bin: str
    brand: str | None
    type: str | None
    bank: str | None
    country: str | None
    country_code: str | None
    valid: bool

class BulkRequest(BaseModel):
    items: list[str]

def identify_card(card_number: str) -> dict:
    """Identify card brand and type from number using Luhn and BIN patterns."""
    clean_number = re.sub(r"\s|-", "", card_number)
    
    if len(clean_number) < 6:
        return {"brand": None, "type": None, "bank": None, "country": None, "country_code": None}
    
    bin_prefix = clean_number[:6]
    
    # Check exact BIN match first
    if bin_prefix in BIN_DATABASE:
        info = BIN_DATABASE[bin_prefix]
        return {"brand": info["brand"], "type": info["type"], "bank": info["bank"],
                "country": info["country"], "country_code": info["country_code"]}
    
    # Check patterns
    for pattern, brand, card_type, bank, country, country_code in BIN_PATTERNS:
        if re.match(pattern, clean_number):
            return {"brand": brand, "type": card_type, "bank": bank,
                    "country": country, "country_code": country_code}
    
    # Check by first digit
    first = clean_number[0]
    if first == "4":
        return {"brand": "Visa", "type": "Unknown", "bank": "Unknown", "country": "Unknown", "country_code": "UNK"}
    elif first in ["5", "2"]:
        return {"brand": "Mastercard", "type": "Unknown", "bank": "Unknown", "country": "Unknown", "country_code": "UNK"}
    elif first == "6":
        return {"brand": "Discover", "type": "Unknown", "bank": "Unknown", "country": "Unknown", "country_code": "UNK"}
    elif first == "3":
        if clean_number[1] in ["4", "7"]:
            return {"brand": "American Express", "type": "Unknown", "bank": "Unknown", "country": "Unknown", "country_code": "UNK"}
        return {"brand": "Diners Club", "type": "Unknown", "bank": "Unknown", "country": "Unknown", "country_code": "UNK"}
    
    return {"brand": None, "type": None, "bank": None, "country": None, "country_code": None}

def luhn_check(num: str) -> bool:
    """Luhn algorithm validation."""
    if not num.isdigit() or len(num) < 2:
        return False
    total = 0
    reverse_digits = num[::-1]
    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/lookup")
def bin_lookup(request: BINLookupRequest, _=Depends(auth)):
    result = identify_card(request.bin)
    valid = result["brand"] is not None
    return BINLookupResponse(bin=request.bin, **result, valid=valid)

@app.post("/api/v1/bulk/lookup")
def bulk_lookup(request: BulkRequest, _=Depends(auth)):
    if len(request.items) > 1000:
        raise HTTPException(400, "Max 1000 items per request")
    
    results = []
    for item in request.items:
        try:
            result = identify_card(item)
            valid = result["brand"] is not None
            output = {"bin": item, **result, "valid": valid}
            results.append({"input": item, "output": output, "error": None})
        except Exception as e:
            results.append({"input": item, "output": None, "error": str(e)})
    
    total = len(results)
    successful = sum(1 for r in results if r["error"] is None)
    return {"results": results, "total": total, "successful": successful}

@app.post("/api/v1/validate")
def bin_validate(request: BINLookupRequest, _=Depends(auth)):
    clean_number = re.sub(r"\s|-", "", request.bin)
    result = identify_card(request.bin)
    
    return {
        "bin": request.bin,
        "valid_format": bool(re.match(r"^[0-9]{6,}$", clean_number)),
        "luhn_valid": luhn_check(clean_number),
        "brand": result["brand"],
        "type": result["type"],
        "bank": result["bank"],
        "country": result["country"],
        "country_code": result["country_code"]
    }

@app.post("/api/v1/bulk/validate")
def bulk_validate(request: BulkRequest, _=Depends(auth)):
    if len(request.items) > 1000:
        raise HTTPException(400, "Max 1000 items per request")
    
    results = []
    for item in request.items:
        try:
            clean_number = re.sub(r"\s|-", "", item)
            result = identify_card(item)
            output = {
                "bin": item,
                "valid_format": bool(re.match(r"^[0-9]{6,}$", clean_number)),
                "luhn_valid": luhn_check(clean_number),
                "brand": result["brand"],
                "type": result["type"],
                "bank": result["bank"],
                "country": result["country"],
                "country_code": result["country_code"]
            }
            results.append({"input": item, "output": output, "error": None})
        except Exception as e:
            results.append({"input": item, "output": None, "error": str(e)})
    
    total = len(results)
    successful = sum(1 for r in results if r["error"] is None)
    return {"results": results, "total": total, "successful": successful}

try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    pass