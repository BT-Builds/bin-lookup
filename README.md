# Credit Card BIN Lookup API

Identify credit card brand, type, bank, and country from BIN numbers.

## Endpoints

### GET /health
Health check endpoint. No authentication required.

```bash
curl https://bin-lookup.vercel.app/health
```

### POST /api/v1/lookup
Look up card information from a BIN (Bank Identification Number).

```bash
curl -X POST https://bin-lookup.vercel.app/api/v1/lookup \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"bin": "411111"}'
```

**Response:**
```json
{
  "bin": "411111",
  "brand": "Visa",
  "type": "Credit",
  "bank": "Test Card Issuer",
  "country": "USA",
  "country_code": "US",
  "valid": true
}
```

### POST /api/v1/validate
Validate card number and check Luhn algorithm.

```bash
curl -X POST https://bin-lookup.vercel.app/api/v1/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"bin": "4111111111111111"}'
```

**Response:**
```json
{
  "bin": "4111111111111111",
  "valid_format": true,
  "luhn_valid": true,
  "brand": "Visa",
  "type": "Credit",
  "bank": "Test Card Issuer",
  "country": "USA",
  "country_code": "US"
}
```

## Authentication

All endpoints except `/health` require an API key in the `X-API-Key` header.

## Pricing (for RapidAPI)

- Free: 50 requests/month
- Basic: $9.99/month - 10,000 requests/month
- Pro: $29.99/month - 100,000 requests/month

## Features

- Identify Visa, Mastercard, American Express, Discover, JCB, Diners Club
- Luhn algorithm validation
- BIN-based bank and country lookup
- Supports card numbers with spaces and hyphens

## Postman
[![Run in Postman](https://run.pstmn.io/button.svg)](https://raw.githubusercontent.com/BT-Builds/bin-lookup/main/postman_collection.json)
