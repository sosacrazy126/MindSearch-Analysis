"""
MindSearch FastAPI Application

A FastAPI-based web service for the MindSearch AI-powered information retrieval system.
"""

import asyncio
import json
import logging
import random
import os
from typing import Dict, List, Union, Optional

import janus
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from sse_starlette.sse import EventSourceResponse

from mindsearch.agent import init_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments for the FastAPI application."""
    import argparse

    parser = argparse.ArgumentParser(description="MindSearch API Server")
    parser.add_argument("--host", default="0.0.0.0", type=str, help="Service host")
    parser.add_argument("--port", default=8002, type=int, help="Service port")
    parser.add_argument("--lang", default="en", choices=["en", "cn"], help="Language")
    parser.add_argument("--model_format", default="gpt4", type=str, help="Model format")
    parser.add_argument("--search_engine", default="DuckDuckGoSearch", type=str, help="Search engine")
    parser.add_argument("--asy", default=False, action="store_true", help="Use async agent mode")
    parser.add_argument("--debug", default=False, action="store_true", help="Enable debug mode")
    return parser.parse_args()


# Parse arguments and configure application
args = parse_arguments()

# Set logging level based on debug flag
if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('mindsearch').setLevel(logging.DEBUG)

# Create FastAPI application
app = FastAPI(
    title="MindSearch API",
    description="AI-powered information retrieval and search system",
    version="1.0.0",
    docs_url="/docs" if args.debug else None,  # Only enable docs in debug mode
    redoc_url="/redoc" if args.debug else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerationParams(BaseModel):
    """Request parameters for the generation endpoint."""
    inputs: Union[str, List[Dict]]
    session_id: int = Field(default_factory=lambda: random.randint(0, 999999))
    agent_cfg: Dict = Field(default_factory=dict)
    
    @validator('inputs')
    def validate_inputs(cls, v):
        """Validate inputs parameter."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Input string cannot be empty")
        elif isinstance(v, list):
            if not v:
                raise ValueError("Input list cannot be empty")
        else:
            raise ValueError("Inputs must be a string or list")
        return v


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    configuration: Dict[str, str]


# Global agent instance (initialized on startup)
agent = None


@app.on_event("startup")
async def startup_event():
    """Initialize the agent on application startup."""
    global agent
    try:
        logger.info("Initializing MindSearch agent...")
        agent = init_agent(
            lang=args.lang,
            model_format=args.model_format,
            search_engine=args.search_engine,
            use_async=args.asy
        )
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise RuntimeError(f"Application startup failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down MindSearch API")


def _postprocess_agent_message(message: dict) -> dict:
    """
    Post-process agent messages for consistent formatting.
    
    Args:
        message: Raw agent message
        
    Returns:
        Processed message dict
    """
    try:
        content = message.get("content", {})
        formatted = message.get("formatted", {})
        
        current_node = None
        if isinstance(content, dict):
            current_node = content.get("current_node")
        
        if current_node:
            return {
                "response": formatted.get("node", {}).get(current_node, {}),
                "current_node": current_node,
                "adjacency_list": formatted.get("adjacency_list", {}),
                "all_nodes": formatted.get("node", {})
            }
        
        return {
            "response": content,
            "current_node": "unknown",
            "adjacency_list": {},
            "all_nodes": {}
        }
    except Exception as e:
        logger.error(f"Error post-processing message: {e}")
        return {
            "response": message,
            "current_node": "error",
            "adjacency_list": {},
            "all_nodes": {}
        }


async def _generate_stream_response(agent_instance, inputs: str, session_id: int):
    """
    Generate streaming responses from the agent.
    
    Args:
        agent_instance: The MindSearch agent
        inputs: Input query string
        session_id: Session identifier
        
    Yields:
        Formatted SSE messages
    """
    try:
        logger.info(f"Starting search for session {session_id}: {inputs[:100]}...")
        
        message_count = 0
        for agent_message in agent_instance(inputs, session_id=session_id):
            message_count += 1
            
            # Convert agent message to dict format
            if hasattr(agent_message, '__dict__'):
                message_dict = {
                    "content": getattr(agent_message, 'content', {}),
                    "formatted": getattr(agent_message, 'formatted', {}),
                    "sender": getattr(agent_message, 'sender', 'unknown'),
                    "stream_state": getattr(agent_message, 'stream_state', None)
                }
            else:
                message_dict = {"content": agent_message, "formatted": {}}
            
            # Post-process the message
            processed_message = _postprocess_agent_message(message_dict)
            
            # Format as SSE event
            event_data = {
                "response": processed_message,
                "session_id": session_id,
                "message_count": message_count
            }
            
            yield f"data: {json.dumps(event_data)}\n\n"
            
            # Add periodic ping to keep connection alive
            if message_count % 10 == 0:
                yield f": ping - {message_count}\n\n"
        
        logger.info(f"Search completed for session {session_id}, sent {message_count} messages")
        
    except Exception as e:
        logger.error(f"Error in stream generation for session {session_id}: {e}")
        error_event = {
            "error": str(e),
            "session_id": session_id,
            "type": "error"
        }
        yield f"data: {json.dumps(error_event)}\n\n"


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if agent is not None else "unhealthy",
        version="1.0.0",
        configuration={
            "language": args.lang,
            "model_format": args.model_format,
            "search_engine": args.search_engine,
            "async_mode": str(args.asy)
        }
    )


@app.post("/solve")
async def solve(params: GenerationParams, request: Request):
    """
    Main endpoint for processing search queries.
    
    Args:
        params: Generation parameters including the query
        request: FastAPI request object
        
    Returns:
        Streaming response with search results
    """
    if agent is None:
        logger.error("Agent not initialized")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: Agent not initialized"
        )
    
    try:
        # Extract query from inputs
        if isinstance(params.inputs, str):
            query = params.inputs
        elif isinstance(params.inputs, list) and params.inputs:
            # Handle list format - take first string element
            query = str(params.inputs[0])
        else:
            raise ValueError("Invalid inputs format")
        
        if not query.strip():
            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty"
            )
        
        logger.info(f"Processing query for session {params.session_id}: {query[:100]}...")
        
        # Return streaming response
        return EventSourceResponse(
            _generate_stream_response(agent, query, params.session_id),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except ValueError as e:
        logger.warning(f"Invalid request for session {params.session_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error for session {params.session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "name": "MindSearch API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "solve": "/solve",
            "docs": "/docs" if args.debug else "disabled"
        }
    }


# For running with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting MindSearch API server on {args.host}:{args.port}")
    logger.info(f"Configuration: lang={args.lang}, model={args.model_format}, search={args.search_engine}")
    
    uvicorn.run(
        "mindsearch.app:app",
        host=args.host,
        port=args.port,
        reload=args.debug,
        log_level="debug" if args.debug else "info"
    )
