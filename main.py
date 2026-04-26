"""
FastAPI wrapper around Apify Website Content Crawler.
Provides LLM‑ready chunks, schema.org extraction, and caching.
"""
import os
import json
import hashlib
import time
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, HttpUrl

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")  # Must be set in environment
ACTOR_ID = "apify~website-content-crawler"
BASE_URL = "https://api.apify.com/v2"

app = FastAPI(
    title="Website Content API",
    description="LLM‑ready content extraction API using Apify Website Content Crawler",
    version="0.1.0",
)

# Simple in‑memory cache (for production replace with Redis)
cache = {}


class ScrapeRequest(BaseModel):
    url: HttpUrl
    extract_schema: Optional[bool] = False
    chunk_size: Optional[int] = 1000  # characters per chunk


class ScrapeResponse(BaseModel):
    url: str
    chunks: list[str]
    metadata: dict


def get_cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


async def call_actor(url: str, extract_schema: bool) -> dict:
    """Call Apify Website Content Crawler actor."""
    payload = {
        "startUrls": [{"url": url}],
        "parser": {
            "type": "markdown",
            "maxTextLength": 0,  # no limit
        },
        "schemaOrg": extract_schema,
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Use the sync endpoint that waits for completion
        resp = await client.post(
            f"{BASE_URL}/acts/{ACTOR_ID}/run-sync-get-dataset-items",
            params={"token": APIFY_TOKEN},
            json={"startUrls": [{"url": url}]},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()[0]  # Return first item


def chunk_text(text: str, size: int = 1000) -> list[str]:
    """Split text into chunks of approx size."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end
    return chunks


@app.get("/")
async def root():
    return {"message": "Website Content API", "docs": "/docs"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest):
    url_str = str(req.url)
    
    # Check cache first
    cache_key = get_cache_key(url_str)
    if cache_key in cache:
        cached = cache[cache_key]
        # Simple 1‑min TTL for demo
        if time.time() - cached["ts"] < 60:
            return cached["data"]
    
    # Call Apify actor
    try:
        data = await call_actor(url_str, req.extract_schema)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    
    # Extract text and metadata
    text = data.get("text", "")
    metadata = {
        "title": data.get("metadata", {}).get("title", ""),
        "description": data.get("metadata", {}).get("description", ""),
        "language": data.get("metadata", {}).get("language", ""),
    }
    if req.extract_schema:
        metadata["schema"] = data.get("schemaOrg", [])
    
    # Chunk text
    chunks = chunk_text(text, req.chunk_size)
    
    result = ScrapeResponse(url=url_str, chunks=chunks, metadata=metadata)
    
    # Cache result
    cache[cache_key] = {"data": result.model_dump(), "ts": time.time()}
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)