"""
FastAPI application for the AI-First CRM HCP Module.

Provides REST endpoints for managing Healthcare Professionals (HCPs),
their interactions, and a conversational AI agent powered by LangGraph.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import json

from config import settings
from database import SessionLocal, HCP, Interaction, init_db
from agent import process_chat, get_tool_metadata


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class InteractionCreate(BaseModel):
    """Schema for creating a new interaction via the structured form endpoint."""
    hcp_id: int
    type: str = "Meeting"
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    materials_shared: Optional[list[str]] = Field(default_factory=list)
    samples_distributed: Optional[list[str]] = Field(default_factory=list)


class InteractionUpdate(BaseModel):
    """Schema for updating an existing interaction (all fields optional)."""
    type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    materials_shared: Optional[list[str]] = None
    samples_distributed: Optional[list[str]] = None


class ChatRequest(BaseModel):
    """Schema for the AI chat endpoint."""
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    """Schema for the AI chat response."""
    response: str
    tool_calls: list = Field(default_factory=list)
    extracted_data: dict = Field(default_factory=dict)


class HCPResponse(BaseModel):
    """Schema for HCP data in responses."""
    id: int
    name: str
    specialty: str
    clinic: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class InteractionResponse(BaseModel):
    """Schema for Interaction data in responses."""
    id: int
    hcp_id: int
    hcp_name: str
    type: str
    date: str
    time: str
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    materials_shared: list = Field(default_factory=list)
    samples_distributed: list = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database (create tables + seed data) on startup."""
    init_db()
    print(f"🚀 {settings.PROJECT_NAME} — database initialised")
    print(f"   Mock AI mode: {settings.MOCK_AI_MODE}")
    yield


# ---------------------------------------------------------------------------
# FastAPI app creation
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the AI-First CRM HCP Module with LangGraph-powered conversational agent.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: database session dependency
# ---------------------------------------------------------------------------

def get_db():
    """Yield a database session and ensure it's closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# HCP endpoints
# ---------------------------------------------------------------------------

@app.get("/api/hcps", response_model=list[HCPResponse])
def list_hcps(search: Optional[str] = Query(None, description="Filter by name or specialty")):
    """List all HCPs. Optionally filter by name or specialty substring."""
    db = SessionLocal()
    try:
        query = db.query(HCP)
        if search:
            query = query.filter(
                (HCP.name.ilike(f"%{search}%")) | (HCP.specialty.ilike(f"%{search}%"))
            )
        hcps = query.all()
        return [hcp.to_dict() for hcp in hcps]
    finally:
        db.close()


@app.get("/api/hcps/{hcp_id}", response_model=HCPResponse)
def get_hcp(hcp_id: int):
    """Get a single HCP by ID."""
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            raise HTTPException(status_code=404, detail=f"HCP with id {hcp_id} not found")
        return hcp.to_dict()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Interaction endpoints
# ---------------------------------------------------------------------------

@app.get("/api/interactions", response_model=list[InteractionResponse])
def list_interactions(hcp_id: Optional[int] = Query(None, description="Filter by HCP ID")):
    """List all interactions. Optionally filter by hcp_id."""
    db = SessionLocal()
    try:
        query = db.query(Interaction)
        if hcp_id is not None:
            query = query.filter(Interaction.hcp_id == hcp_id)
        interactions = query.order_by(Interaction.date.desc()).all()
        return [i.to_dict() for i in interactions]
    finally:
        db.close()


@app.post("/api/interactions", response_model=InteractionResponse, status_code=201)
def create_interaction(data: InteractionCreate):
    """Create a new interaction (structured form submission)."""
    db = SessionLocal()
    try:
        # Verify HCP exists
        hcp = db.query(HCP).filter(HCP.id == data.hcp_id).first()
        if not hcp:
            raise HTTPException(status_code=404, detail=f"HCP with id {data.hcp_id} not found")

        interaction = Interaction(
            hcp_id=data.hcp_id,
            type=data.type,
            date=data.date,
            time=data.time,
            attendees=data.attendees,
            topics_discussed=data.topics_discussed,
            sentiment=data.sentiment,
            outcomes=data.outcomes,
            follow_up_actions=data.follow_up_actions,
            materials_shared=json.dumps(data.materials_shared or []),
            samples_distributed=json.dumps(data.samples_distributed or []),
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction.to_dict()
    finally:
        db.close()


@app.put("/api/interactions/{interaction_id}", response_model=InteractionResponse)
def update_interaction(interaction_id: int, data: InteractionUpdate):
    """Update an existing interaction by ID. Only provided fields are updated."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            raise HTTPException(status_code=404, detail=f"Interaction {interaction_id} not found")

        # Apply updates for each provided field
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key in ("materials_shared", "samples_distributed"):
                setattr(interaction, key, json.dumps(value or []))
            else:
                setattr(interaction, key, value)

        db.commit()
        db.refresh(interaction)
        return interaction.to_dict()
    finally:
        db.close()


@app.delete("/api/interactions/{interaction_id}")
def delete_interaction(interaction_id: int):
    """Delete an interaction by ID."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            raise HTTPException(status_code=404, detail=f"Interaction {interaction_id} not found")
        db.delete(interaction)
        db.commit()
        return {"message": f"Interaction {interaction_id} deleted successfully"}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# AI Chat endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the LangGraph AI agent.
    The agent processes the message, potentially calls tools, and returns
    a structured response.
    """
    try:
        result = await process_chat(request.message, request.session_id)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


# ---------------------------------------------------------------------------
# Agent metadata endpoint
# ---------------------------------------------------------------------------

@app.get("/api/agent/tools")
def list_agent_tools():
    """Return metadata about the 5 available agent tools."""
    return {"tools": get_tool_metadata()}
