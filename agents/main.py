from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, Union
import aiofiles
import tempfile
import os
from Sage.sage import SageOrchestrator

app = FastAPI(title="Sage Log Analysis API", version="1.0.0")

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the SageOrchestrator
sage_orchestrator = SageOrchestrator()


@app.post("/analyze")
async def analyze_content(
    request: Request,
    file: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    message: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
):
    """
    Unified endpoint for analyzing different types of content:
    - Text messages
    - File uploads
    - Audio recordings
    """
    try:
        query = ""
        context = {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "content_type": type or "unknown",
        }

        # Handle different input types
        if type == "text" and message:
            query = f"Analyze this user message for insights: {message}"
            context["user_message"] = message

        elif type == "file" and file:
            # Save uploaded file temporarily
            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=f"_{file.filename}"
                ) as temp_file:
                    content = await file.read()
                    temp_file.write(content)
                    temp_file_path = temp_file.name

                # Read file content based on type
                if file.filename.endswith((".txt", ".log")):
                    with open(temp_file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                    query = f"Analyze this uploaded file content for patterns and insights: {file_content[:2000]}..."  # Limit content
                else:
                    query = f"Process uploaded file: {file.filename}"

                context.update(
                    {
                        "file_name": file.filename,
                        "file_size": len(content),
                        "file_type": file.content_type,
                    }
                )

            finally:
                # Clean up temp file
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        elif type == "audio" and audio:
            context.update(
                {
                    "audio_filename": audio.filename,
                    "audio_size": audio.size if hasattr(audio, "size") else 0,
                }
            )
            query = f"Process audio recording: {audio.filename}"

        else:
            # Fallback for direct JSON requests
            try:
                data = await request.json()
                if "logs" in data:
                    # Legacy format support
                    logs = data.get("logs", [])
                    query = (
                        f"Analyze {len(logs)} log entries for patterns and anomalies"
                    )
                    context["logs"] = logs
                elif "message" in data:
                    query = f"Analyze this message: {data['message']}"
                    context["user_message"] = data["message"]
                else:
                    query = "General system analysis request"
                    context.update(data)
            except:
                raise HTTPException(status_code=400, detail="Invalid request format")

        # Run the Sage orchestration
        print(f"Processing query: {query}")
        analysis_result = sage_orchestrator.orchestrate_analysis(query, context)

        # Format response for the frontend
        response = {
            "success": True,
            "request_id": context["request_id"],
            "timestamp": analysis_result["timestamp"],
            "response": analysis_result["final_insight"],
            "analysis": {
                "confidence_score": analysis_result["confidence_score"],
                "contributing_agents": analysis_result["contributing_agents"],
                "agent_outputs": analysis_result["agent_outputs"],
            },
            "metadata": {"query": query, "content_type": context["content_type"]},
        }

        print(
            f"Analysis completed with confidence: {analysis_result['confidence_score']}"
        )
        return response

    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "response": "I encountered an error while processing your request. Please try again or contact support if the issue persists.",
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/upload")
async def upload_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    message: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
):
    """
    Upload endpoint that redirects to analyze for backward compatibility
    """
    return await analyze_content(request, file, audio, message, type)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agents": {
            agent: reliability
            for agent, reliability in sage_orchestrator.agent_reliability.items()
        },
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Sage Log Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "/analyze": "Main analysis endpoint",
            "/upload": "Upload endpoint (redirects to analyze)",
            "/health": "Health check",
        },
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
