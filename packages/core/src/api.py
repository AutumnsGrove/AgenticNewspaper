"""HTTP API for the Intelligent News Aggregator.

Exposes the orchestrator via HTTP for integration with Cloudflare Workers.
Can be deployed to Modal, Railway, or any Python hosting platform.
"""

import asyncio
import os
import json
from typing import Optional
from dataclasses import asdict
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.orchestrator.main_orchestrator import MainOrchestrator
from src.models.article import DigestMetadata

app = FastAPI(
    title="The Daily Clearing - Core API",
    description="AI-powered news digest generation service",
    version="1.0.0",
)

# CORS for worker access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracking (use Redis/DB in production)
active_jobs: dict = {}


class DigestRequest(BaseModel):
    """Request to generate a digest."""

    user_id: str
    job_id: str
    preferences: dict
    webhook_url: Optional[str] = None


class DigestProgress(BaseModel):
    """Progress update for digest generation."""

    job_id: str
    status: str
    progress: int
    current_step: str
    articles_found: int = 0
    articles_parsed: int = 0
    articles_included: int = 0
    error: Optional[str] = None


class DigestResult(BaseModel):
    """Result of digest generation."""

    job_id: str
    success: bool
    digest_id: Optional[str] = None
    markdown: Optional[str] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


@app.post("/api/digest/generate")
async def generate_digest(request: DigestRequest, background_tasks: BackgroundTasks):
    """
    Start digest generation.

    This runs in the background and returns immediately.
    Poll /api/digest/{job_id}/progress for updates.
    """
    if request.job_id in active_jobs:
        raise HTTPException(status_code=409, detail="Job already exists")

    # Initialize job tracking
    active_jobs[request.job_id] = {
        "status": "pending",
        "progress": 0,
        "current_step": "Initializing...",
        "articles_found": 0,
        "articles_parsed": 0,
        "articles_included": 0,
        "error": None,
        "result": None,
    }

    # Start generation in background
    background_tasks.add_task(
        run_digest_generation,
        request.job_id,
        request.user_id,
        request.preferences,
        request.webhook_url,
    )

    return {
        "success": True,
        "job_id": request.job_id,
        "status": "pending",
    }


@app.get("/api/digest/{job_id}/progress")
async def get_progress(job_id: str) -> DigestProgress:
    """Get progress of digest generation."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]
    return DigestProgress(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        current_step=job["current_step"],
        articles_found=job["articles_found"],
        articles_parsed=job["articles_parsed"],
        articles_included=job["articles_included"],
        error=job["error"],
    )


@app.get("/api/digest/{job_id}/result")
async def get_result(job_id: str) -> DigestResult:
    """Get result of completed digest generation."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = active_jobs[job_id]

    if job["status"] not in ("complete", "failed"):
        raise HTTPException(status_code=400, detail="Job not yet complete")

    if job["status"] == "failed":
        return DigestResult(
            job_id=job_id,
            success=False,
            error=job["error"],
        )

    result = job.get("result", {})
    return DigestResult(
        job_id=job_id,
        success=True,
        digest_id=result.get("digest_id"),
        markdown=result.get("markdown"),
        metadata=result.get("metadata"),
    )


@app.delete("/api/digest/{job_id}")
async def cancel_job(job_id: str):
    """Cancel and remove a job."""
    if job_id in active_jobs:
        del active_jobs[job_id]
        return {"success": True, "message": "Job cancelled"}
    return {"success": False, "message": "Job not found"}


async def run_digest_generation(
    job_id: str,
    user_id: str,
    preferences: dict,
    webhook_url: Optional[str] = None,
):
    """Background task to run digest generation."""
    try:
        # Update status
        active_jobs[job_id]["status"] = "searching"
        active_jobs[job_id]["progress"] = 5
        active_jobs[job_id]["current_step"] = "Searching for articles..."

        # Create orchestrator with progress callbacks
        orchestrator = MainOrchestratorWithProgress(
            preferences,
            progress_callback=lambda p: update_job_progress(job_id, p),
        )

        # Generate digest
        digest_path, digest_content, metadata = await orchestrator.generate_digest_with_content()

        # Mark complete
        active_jobs[job_id]["status"] = "complete"
        active_jobs[job_id]["progress"] = 100
        active_jobs[job_id]["current_step"] = "Complete!"
        active_jobs[job_id]["result"] = {
            "digest_id": metadata.digest_id if metadata else datetime.now().strftime("%Y-%m-%d"),
            "markdown": digest_content,
            "metadata": asdict(metadata) if metadata else None,
        }

        # Webhook callback if configured
        if webhook_url:
            await send_webhook(webhook_url, job_id, active_jobs[job_id])

    except Exception as e:
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["error"] = str(e)
        active_jobs[job_id]["progress"] = 0
        active_jobs[job_id]["current_step"] = f"Failed: {e}"

        if webhook_url:
            await send_webhook(webhook_url, job_id, active_jobs[job_id])


def update_job_progress(job_id: str, progress: dict):
    """Update job progress from orchestrator callback."""
    if job_id not in active_jobs:
        return

    if "status" in progress:
        active_jobs[job_id]["status"] = progress["status"]
    if "progress" in progress:
        active_jobs[job_id]["progress"] = progress["progress"]
    if "current_step" in progress:
        active_jobs[job_id]["current_step"] = progress["current_step"]
    if "articles_found" in progress:
        active_jobs[job_id]["articles_found"] = progress["articles_found"]
    if "articles_parsed" in progress:
        active_jobs[job_id]["articles_parsed"] = progress["articles_parsed"]
    if "articles_included" in progress:
        active_jobs[job_id]["articles_included"] = progress["articles_included"]


async def send_webhook(url: str, job_id: str, job_data: dict):
    """Send webhook notification."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                url,
                json={
                    "job_id": job_id,
                    "status": job_data["status"],
                    "result": job_data.get("result"),
                    "error": job_data.get("error"),
                },
                timeout=10.0,
            )
    except Exception as e:
        print(f"Webhook failed: {e}")


class MainOrchestratorWithProgress(MainOrchestrator):
    """Extended orchestrator with progress callbacks."""

    def __init__(self, user_preferences: dict, progress_callback=None):
        super().__init__(user_preferences)
        self.progress_callback = progress_callback

    def _update_progress(self, progress: dict):
        """Call progress callback if set."""
        if self.progress_callback:
            self.progress_callback(progress)

    async def generate_digest_with_content(self):
        """Generate digest and return content along with path."""
        print("=" * 70)
        print("INTELLIGENT NEWS AGGREGATOR - Generating Digest")
        print("=" * 70)

        import time

        self.start_time = time.time()

        # Step 1: Search
        self._update_progress({
            "status": "searching",
            "progress": 10,
            "current_step": "Searching for articles...",
        })
        articles_by_topic = await self._search_all_topics()

        total_found = sum(len(a) for a in articles_by_topic.values())
        self._update_progress({
            "articles_found": total_found,
        })

        # Step 2: Parse
        self._update_progress({
            "status": "parsing",
            "progress": 30,
            "current_step": "Parsing articles...",
        })
        parsed_articles_by_topic = await self._parse_all_articles(articles_by_topic)

        total_parsed = sum(len(a) for a in parsed_articles_by_topic.values())
        self._update_progress({
            "articles_parsed": total_parsed,
            "progress": 55,
        })

        # Step 3: Synthesize
        self._update_progress({
            "status": "synthesizing",
            "progress": 70,
            "current_step": "Synthesizing digest...",
        })

        metadata = self._create_metadata(parsed_articles_by_topic)
        digest_content = await self.synthesis_agent.create_digest(
            parsed_articles_by_topic,
            self.preferences,
            metadata,
        )

        self._update_progress({
            "articles_included": metadata.total_articles_included,
            "progress": 90,
        })

        # Step 4: Save
        self._update_progress({
            "status": "saving",
            "progress": 95,
            "current_step": "Saving digest...",
        })
        digest_path = await self._save_digest(digest_content)

        self.end_time = time.time()
        self._print_summary(digest_path, metadata)

        return str(digest_path), digest_content, metadata


# Entry point for running with uvicorn
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
