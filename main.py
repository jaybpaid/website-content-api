"""
FastAPI wrapper around Exa Search API for website content extraction.
Provides LLM-ready chunks, highlights, and text content.
"""
import os
import json
import hashlib
import time
from typing import Optional

from exa_py import Exa
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, HttpUrl

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")  # Must be set in environment

app = FastAPI(
    title="Website Content API",
    description="LLM-ready content extraction API using Exa Search API",
    version="0.2.0",
)

# Initialize Exa client
exa = Exa(EXA_API_KEY) if EXA_API_KEY else None

# Simple in-memory cache (for production replace with Redis)
cache = {}


class ScrapeRequest(BaseModel):
    url: HttpUrl
    highlights: Optional[bool] = True
    max_chars: Optional[int] = 5000  # max characters per result


class ScrapeResponse(BaseModel):
    url: str
    text: str
    highlights: Optional[str] = None
    title: Optional[str] = None
    metadata: dict


def get_cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


async def scrape_with_exa(url: str, max_chars: int = 5000) -> dict:
    """Scrape website content using Exa API."""
    if not exa:
        raise HTTPException(status_code=500, detail="EXA_API_KEY not configured")
    
    # Get full text content from URL
    result = exa.get_contents(
        [str(url)],
        text=True,
        summary=False,
        highlights={"max_characters": max_chars} if max_chars else None,
    )
    
    if not result or not result.results:
        raise HTTPException(status_code=404, detail="No content found")
    
    item = result.results[0]
    return {
        "text": item.text or "",
        "url": item.url,
        "title": item.title,
        "highlights": item.highlights,
    }


def chunk_text(text: str, size: int = 1000) -> list[str]:
    """Split text into chunks of approx size."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end
    return chunks


@app.get("/")
async def root():
    return {"message": "Website Content API", "version": "0.2.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy", "provider": "exa"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(req: ScrapeRequest):
    url_str = str(req.url)
    
    # Check cache first
    cache_key = get_cache_key(url_str)
    if cache_key in cache:
        cached = cache[cache_key]
        # Simple 5-min TTL
        if time.time() - cached["ts"] < 300:
            return cached["data"]
    
    # Call Exa API
    try:
        data = await scrape_with_exa(url_str, req.max_chars)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Build response
    result = ScrapeResponse(
        url=url_str,
        text=data.get("text", ""),
        highlights=data.get("highlights"),
        title=data.get("title"),
        metadata={"provider": "exa"},
    )
    
    # Cache result
    cache[cache_key] = {"data": result.model_dump(), "ts": time.time()}
    
    return result


@app.post("/scrape/chunks")
async def scrape_chunks(req: ScrapeRequest, chunk_size: int = Query(1000, ge=100, le=10000)):
    """Scrape website and return as chunks for LLM consumption."""
    # First get full scrape
    scrape_result = await scrape(req)
    
    # Chunk the text
    chunks = chunk_text(scrape_result.text, chunk_size)
    
    return {
        "url": scrape_result.url,
        "title": scrape_result.title,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "metadata": scrape_result.metadata,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)