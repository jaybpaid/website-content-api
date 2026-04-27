"""
Website Content API - Reliable web scraping using Exa
Simple, fast, affordable - LLM-ready output for AI applications.
"""
import os
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Website Content API",
    description="Fast, reliable web scraping with LLM-ready output",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ScrapeRequest(BaseModel):
    url: str = Field(..., description="URL to scrape")
    highlights: bool = Field(default=True, description="Return highlights")
    text: bool = Field(default=True, description="Return full text")

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    num_results: int = Field(default=10, description="Number of results")

# Storage for jobs
jobs = {}

def get_exa():
    """Get Exa client with API key."""
    exa_key = os.getenv("EXA_API_KEY", "")
    if not exa_key:
        raise HTTPException(status_code=500, detail="EXA_API_KEY not configured")
    from exa_py import Exa
    return Exa(exa_key)

@app.get("/")
async def root():
    return {
        "service": "Website Content API",
        "version": "2.0.0",
        "status": "active",
        "docs": "/docs",
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    """Scrape a URL and return clean, LLM-ready content."""
    try:
        exa = get_exa()
        
        # Build contents options
        contents = {"text": {"maxCharacters": 50000}}
        if request.highlights:
            contents["highlights"] = True
        
        # Search for this specific URL
        result = exa.search(
            f"site:{request.url.replace('https://', '').replace('http://', '')}",
            num_results=1,
            contents=contents,
        )
        
        if not result or not result.results:
            raise HTTPException(status_code=404, detail="No content found")
        
        r = result.results[0]
        
        return {
            "success": True,
            "url": request.url,
            "title": r.title if hasattr(r, 'title') else "",
            "text": r.text if hasattr(r, 'text') else "",
            "highlights": getattr(r, 'highlights', []) or [],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/urls")
async def scrape_urls(urls: List[str], highlights: bool = True):
    """Scrape multiple URLs at once."""
    try:
        exa = get_exa()
        
        contents = {"text": {"maxCharacters": 50000}}
        if highlights:
            contents["highlights"] = True
        
        # Build OR query for all URLs
        queries = [f"site:{u.replace('https://', '').replace('http://', '')}" for u in urls]
        query = " OR ".join(queries)
        
        result = exa.search(query, num_results=len(urls), contents=contents)
        
        results = []
        for r in (result.results or []):
            results.append({
                "url": r.url,
                "title": r.title if hasattr(r, 'title') else "",
                "text": r.text[:2000] if hasattr(r, 'text') else "",  # Truncate for batch
                "highlights": getattr(r, 'highlights', []) or [],
            })
        
        return {
            "count": len(results),
            "results": results,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search(request: SearchRequest):
    """Search the web and return results with content."""
    try:
        exa = get_exa()
        
        result = exa.search(
            request.query,
            num_results=request.num_results,
            contents={"text": True, "highlights": True},
        )
        
        results = []
        for r in (result.results or []):
            results.append({
                "title": r.title if hasattr(r, 'title') else "",
                "url": r.url if hasattr(r, 'url') else "",
                "text": r.text[:1000] if hasattr(r, 'text') else "",
                "published": getattr(r, 'published', None),
            })
        
        return {
            "query": request.query,
            "count": len(results),
            "results": results,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))