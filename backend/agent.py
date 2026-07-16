"""
LangGraph AI Agent for HCP CRM Module.

This module implements a conversational AI agent using LangGraph that can:
1. Search for Healthcare Professionals (HCPs) by name or specialty
2. Log new interactions with HCPs from natural language
3. Edit existing interaction records
4. Retrieve full interaction history for an HCP
5. Suggest contextual follow-up actions based on recent interactions

Supports both a real LLM backend (Groq / gemma2-9b-it) and a MockLLM
for offline development and testing.
"""

import re
import json
from datetime import datetime, timedelta
from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
    SystemMessage,
)

from database import SessionLocal, HCP, Interaction
from config import settings


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """State that flows through every node in the LangGraph workflow."""
    messages: list          # Chat history (HumanMessage / AIMessage / ToolMessage)
    extracted_data: dict    # Structured fields extracted from conversation
    tool_results: list      # Results from tool executions
    current_hcp_id: int | None  # Currently-focused HCP (set by search or log)


# ---------------------------------------------------------------------------
# Tool definitions — each tool is a plain function that operates on the DB
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "name": "search_hcps",
        "description": "Search Healthcare Professionals by name or specialty. Returns matching HCP records.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Name or specialty to search for"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "log_interaction",
        "description": "Log a new interaction with an HCP. Extracts structured fields from the provided data and creates an Interaction record.",
        "parameters": {
            "type": "object",
            "properties": {
                "hcp_id": {"type": "integer", "description": "ID of the HCP"},
                "type": {"type": "string", "description": "Interaction type: Meeting, Email, Call, etc."},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "string", "description": "Time in HH:MM format"},
                "topics_discussed": {"type": "string", "description": "Topics discussed during the interaction"},
                "sentiment": {"type": "string", "description": "Overall sentiment: Positive, Neutral, Negative"},
                "outcomes": {"type": "string", "description": "Key outcomes of the interaction"},
                "follow_up_actions": {"type": "string", "description": "Follow-up actions to take"},
                "materials_shared": {"type": "array", "items": {"type": "string"}, "description": "Materials shared during the interaction"},
                "samples_distributed": {"type": "array", "items": {"type": "string"}, "description": "Samples distributed during the interaction"}
            },
            "required": ["hcp_id", "type", "date", "time", "topics_discussed"]
        }
    },
    {
        "name": "edit_interaction",
        "description": "Edit an existing interaction record by ID. Accepts partial fields to update.",
        "parameters": {
            "type": "object",
            "properties": {
                "interaction_id": {"type": "integer", "description": "ID of the interaction to edit"},
                "type": {"type": "string"},
                "date": {"type": "string"},
                "time": {"type": "string"},
                "topics_discussed": {"type": "string"},
                "sentiment": {"type": "string"},
                "outcomes": {"type": "string"},
                "follow_up_actions": {"type": "string"},
                "materials_shared": {"type": "array", "items": {"type": "string"}},
                "samples_distributed": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["interaction_id"]
        }
    },
    {
        "name": "get_hcp_history",
        "description": "Retrieve all past interactions for a given HCP, ordered by date (most recent first).",
        "parameters": {
            "type": "object",
            "properties": {
                "hcp_id": {"type": "integer", "description": "ID of the HCP"}
            },
            "required": ["hcp_id"]
        }
    },
    {
        "name": "suggest_next_actions",
        "description": "Analyze recent interactions and suggest contextual follow-up actions such as sending brochures, scheduling follow-ups, or preparing clinical data summaries.",
        "parameters": {
            "type": "object",
            "properties": {
                "hcp_id": {"type": "integer", "description": "ID of the HCP to suggest actions for"}
            },
            "required": ["hcp_id"]
        }
    }
]


# ---------------------------------------------------------------------------
# Tool execution functions
# ---------------------------------------------------------------------------

def _execute_search_hcps(query: str) -> list[dict]:
    """Search HCPs by name or specialty (case-insensitive partial match)."""
    db = SessionLocal()
    try:
        results = (
            db.query(HCP)
            .filter(
                (HCP.name.ilike(f"%{query}%")) | (HCP.specialty.ilike(f"%{query}%"))
            )
            .all()
        )
        return [hcp.to_dict() for hcp in results]
    finally:
        db.close()


def _execute_log_interaction(
    hcp_id: int,
    type: str = "Meeting",
    date: str | None = None,
    time: str | None = None,
    topics_discussed: str = "",
    sentiment: str = "Neutral",
    outcomes: str = "",
    follow_up_actions: str = "",
    materials_shared: list[str] | None = None,
    samples_distributed: list[str] | None = None,
    **_extra,
) -> dict:
    """Create a new Interaction record in the database."""
    db = SessionLocal()
    try:
        # Default date/time to now if not provided
        now = datetime.utcnow()
        interaction = Interaction(
            hcp_id=hcp_id,
            type=type,
            date=date or now.strftime("%Y-%m-%d"),
            time=time or now.strftime("%H:%M"),
            topics_discussed=topics_discussed,
            sentiment=sentiment,
            outcomes=outcomes,
            follow_up_actions=follow_up_actions,
            materials_shared=json.dumps(materials_shared or []),
            samples_distributed=json.dumps(samples_distributed or []),
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction.to_dict()
    finally:
        db.close()


def _execute_edit_interaction(interaction_id: int, **fields) -> dict:
    """Update an existing Interaction record with the provided fields."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return {"error": f"Interaction {interaction_id} not found"}

        # Apply each provided field
        updatable = [
            "type", "date", "time", "topics_discussed", "sentiment",
            "outcomes", "follow_up_actions",
        ]
        for key in updatable:
            if key in fields and fields[key] is not None:
                setattr(interaction, key, fields[key])

        # JSON-encoded list fields
        if "materials_shared" in fields and fields["materials_shared"] is not None:
            interaction.materials_shared = json.dumps(fields["materials_shared"])
        if "samples_distributed" in fields and fields["samples_distributed"] is not None:
            interaction.samples_distributed = json.dumps(fields["samples_distributed"])

        db.commit()
        db.refresh(interaction)
        return interaction.to_dict()
    finally:
        db.close()


def _execute_get_hcp_history(hcp_id: int) -> list[dict]:
    """Return all interactions for an HCP, most recent first."""
    db = SessionLocal()
    try:
        interactions = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == hcp_id)
            .order_by(Interaction.date.desc())
            .all()
        )
        return [i.to_dict() for i in interactions]
    finally:
        db.close()


def _execute_suggest_next_actions(hcp_id: int) -> dict:
    """Analyze the most recent interaction and generate follow-up suggestions."""
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return {"error": f"HCP with id {hcp_id} not found"}

        latest = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == hcp_id)
            .order_by(Interaction.date.desc())
            .first()
        )

        suggestions: list[str] = []
        if latest:
            topics = (latest.topics_discussed or "").lower()
            sentiment = (latest.sentiment or "").lower()
            follow_ups = (latest.follow_up_actions or "").lower()

            # Context-aware suggestions
            if "phase iii" in topics or "clinical" in topics or "trial" in topics:
                suggestions.append(
                    "Send the latest Phase III clinical trial results and peer-reviewed publications."
                )
            if "efficacy" in topics or "oncoboost" in topics:
                suggestions.append(
                    "Prepare a detailed efficacy comparison deck (OncoBoost vs. standard of care)."
                )
            if "safety" in topics or "adverse" in topics:
                suggestions.append(
                    "Share the updated safety profile and adverse event monitoring data."
                )
            if "dosing" in topics or "dose" in topics:
                suggestions.append(
                    "Provide the dosing guide and titration schedule brochure."
                )
            if sentiment == "positive":
                suggestions.append(
                    f"Schedule a follow-up meeting with {hcp.name} within the next 2 weeks to maintain momentum."
                )
            elif sentiment == "negative":
                suggestions.append(
                    f"Escalate concerns raised by {hcp.name} to the medical affairs team and prepare a point-by-point response."
                )
            if "sample" in follow_ups or "sample" in topics:
                suggestions.append(
                    "Arrange delivery of additional product samples."
                )

            # Generic suggestions if nothing specific matched
            if not suggestions:
                suggestions = [
                    f"Send a thank-you email to {hcp.name} summarizing key discussion points.",
                    "Schedule a follow-up meeting in 2–3 weeks.",
                    "Share relevant product literature and clinical data.",
                ]
        else:
            suggestions = [
                f"No prior interactions found. Consider scheduling an introductory meeting with {hcp.name}.",
                f"Research {hcp.name}'s recent publications and areas of interest before the first meeting.",
            ]

        return {
            "hcp_id": hcp_id,
            "hcp_name": hcp.name,
            "latest_interaction_date": latest.date if latest else None,
            "suggestions": suggestions,
        }
    finally:
        db.close()


# Dispatcher — maps tool names to their implementation
TOOL_DISPATCH = {
    "search_hcps": lambda args: _execute_search_hcps(**args),
    "log_interaction": lambda args: _execute_log_interaction(**args),
    "edit_interaction": lambda args: _execute_edit_interaction(**args),
    "get_hcp_history": lambda args: _execute_get_hcp_history(**args),
    "suggest_next_actions": lambda args: _execute_suggest_next_actions(**args),
}


# ---------------------------------------------------------------------------
# MockLLM — keyword-based intent detection + field extraction
# ---------------------------------------------------------------------------

class MockLLM:
    """
    Regex / keyword-based mock that simulates an LLM for offline development.
    Detects user intent, extracts structured data, and produces realistic
    tool-call responses without requiring a real API key.
    """

    # Pre-compiled patterns for field extraction
    # Match "Dr. Firstname Lastname" or "Dr Firstname Lastname" explicitly
    _DR_NAME_PATTERN = re.compile(
        r"Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
    )
    # Fallback: two consecutive capitalized words (FirstName LastName)
    _PLAIN_NAME_PATTERN = re.compile(
        r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b"
    )
    _SENTIMENT_KEYWORDS = {
        "positive": ["positive", "enthusiastic", "excited", "impressed", "happy", "great", "very positive", "interested"],
        "negative": ["negative", "concerned", "frustrated", "disappointed", "unhappy", "skeptical"],
        "neutral": ["neutral", "indifferent", "okay"],
    }
    _TOPIC_KEYWORDS = [
        "oncoboost", "efficacy", "safety", "dosing", "clinical", "trial",
        "phase iii", "phase 3", "phase ii", "phase 2", "brochure",
        "patient", "adverse", "response rate", "survival",
    ]

    def detect_intent(self, message: str) -> str:
        """Classify the user's intent from the message text."""
        msg = message.lower()

        if any(kw in msg for kw in ["search", "find", "look up", "who is", "list"]):
            return "search_hcps"
        if any(kw in msg for kw in ["history", "past interactions", "previous meetings", "all interactions"]):
            return "get_hcp_history"
        if any(kw in msg for kw in ["edit", "update", "modify", "change", "correct"]):
            return "edit_interaction"
        if any(kw in msg for kw in ["suggest", "recommend", "next steps", "follow-up", "what should"]):
            return "suggest_next_actions"
        if any(kw in msg for kw in ["met", "met with", "discussed", "meeting", "spoke", "called", "visited", "interaction", "log"]):
            return "log_interaction"

        return "general_chat"

    def extract_name(self, message: str) -> str | None:
        """Extract the first HCP name from the message.
        
        Prioritises 'Dr. Firstname Lastname' patterns, then falls back to
        any two consecutive capitalised words, filtering out common
        false-positive phrases.
        """
        # Priority 1: "Dr. Firstname Lastname"
        match = self._DR_NAME_PATTERN.search(message)
        if match:
            return f"Dr. {match.group(1).strip()}"

        # Priority 2: two consecutive capitalised words, but skip noise words
        noise = {
            "Phase III", "Phase II", "Phase IV", "Phase I",
            "Starter Kit", "Next Week", "Follow Up", "General Discussion",
        }
        for m in self._PLAIN_NAME_PATTERN.finditer(message):
            candidate = m.group(1).strip()
            if candidate not in noise:
                # Verify it looks like a person name (not a common English phrase)
                return candidate

        return None

    def extract_sentiment(self, message: str) -> str:
        """Detect sentiment from keywords."""
        msg = message.lower()
        for sentiment, keywords in self._SENTIMENT_KEYWORDS.items():
            if any(kw in msg for kw in keywords):
                return sentiment.capitalize()
        return "Neutral"

    def extract_topics(self, message: str) -> str:
        """Extract discussed topics from the message."""
        msg = message.lower()
        found = [kw.title() for kw in self._TOPIC_KEYWORDS if kw in msg]
        return ", ".join(found) if found else "General discussion"

    def extract_follow_ups(self, message: str) -> str:
        """Extract follow-up actions mentioned in the message."""
        msg = message.lower()
        actions = []
        if any(kw in msg for kw in ["send", "share", "provide", "deliver"]):
            # Try to extract what to send
            match = re.search(r"(?:send|share|provide|deliver)\s+(?:her|him|them)?\s*(?:the\s+)?(.+?)(?:\.|,|$)", msg)
            if match:
                actions.append(f"Send: {match.group(1).strip().title()}")
        if any(kw in msg for kw in ["schedule", "follow-up", "follow up", "next week", "next month"]):
            actions.append("Schedule follow-up meeting")
        if any(kw in msg for kw in ["prepare", "create", "draft"]):
            match = re.search(r"(?:prepare|create|draft)\s+(?:a\s+)?(.+?)(?:\.|,|$)", msg)
            if match:
                actions.append(f"Prepare: {match.group(1).strip().title()}")
        return "; ".join(actions) if actions else ""

    def resolve_hcp(self, name: str | None) -> dict | None:
        """Try to find an HCP by name in the database."""
        if not name:
            return None
        results = _execute_search_hcps(name)
        return results[0] if results else None

    def generate_response(self, message: str, state: AgentState) -> dict:
        """
        Process a user message and return a structured response with optional
        tool calls, mimicking what a real LLM would produce.
        """
        intent = self.detect_intent(message)
        name = self.extract_name(message)
        tool_calls = []
        extracted = {}
        response_text = ""

        if intent == "search_hcps":
            # Use extracted name if found, otherwise parse the query from the message
            if name:
                query = name
            else:
                # Strip common leading verbs to get the actual search term
                stripped = re.sub(
                    r"^(?:search|find|look\s+up|who\s+is|list)\s+(?:for\s+)?(?:me\s+)?",
                    "", message, flags=re.IGNORECASE,
                ).strip(" .?!")
                query = stripped or message
            results = _execute_search_hcps(query)
            tool_calls.append({"tool": "search_hcps", "args": {"query": query}, "result": results})
            if results:
                names = ", ".join(r["name"] for r in results)
                response_text = f"I found {len(results)} matching HCP(s): {names}."
            else:
                response_text = f"No HCPs found matching '{query}'."
            extracted = {"query": query, "results_count": len(results)}

        elif intent == "log_interaction":
            hcp = self.resolve_hcp(name)
            sentiment = self.extract_sentiment(message)
            topics = self.extract_topics(message)
            follow_ups = self.extract_follow_ups(message)
            today = datetime.utcnow().strftime("%Y-%m-%d")
            now_time = datetime.utcnow().strftime("%H:%M")

            extracted = {
                "hcp_name": name,
                "sentiment": sentiment,
                "topics_discussed": topics,
                "follow_up_actions": follow_ups,
                "date": today,
                "time": now_time,
            }

            if hcp:
                log_args = {
                    "hcp_id": hcp["id"],
                    "type": "Meeting",
                    "date": today,
                    "time": now_time,
                    "topics_discussed": topics,
                    "sentiment": sentiment,
                    "outcomes": f"Discussion with {hcp['name']} about {topics}.",
                    "follow_up_actions": follow_ups,
                    "materials_shared": [],
                    "samples_distributed": [],
                }
                result = _execute_log_interaction(**log_args)
                tool_calls.append({"tool": "log_interaction", "args": log_args, "result": result})
                response_text = (
                    f"✅ Interaction logged successfully for **{hcp['name']}**!\n\n"
                    f"• **Type:** Meeting\n"
                    f"• **Date:** {today}\n"
                    f"• **Topics:** {topics}\n"
                    f"• **Sentiment:** {sentiment}\n"
                )
                if follow_ups:
                    response_text += f"• **Follow-ups:** {follow_ups}\n"
            else:
                response_text = (
                    f"I couldn't find an HCP named '{name}' in the database. "
                    "Please check the name or search for the HCP first."
                )

        elif intent == "get_hcp_history":
            hcp = self.resolve_hcp(name)
            if hcp:
                history = _execute_get_hcp_history(hcp["id"])
                tool_calls.append({"tool": "get_hcp_history", "args": {"hcp_id": hcp["id"]}, "result": history})
                if history:
                    response_text = f"Found {len(history)} interaction(s) for **{hcp['name']}**:\n\n"
                    for idx, h in enumerate(history, 1):
                        response_text += (
                            f"{idx}. **{h['type']}** on {h['date']} — "
                            f"Topics: {h['topics_discussed'] or 'N/A'} | "
                            f"Sentiment: {h['sentiment'] or 'N/A'}\n"
                        )
                else:
                    response_text = f"No interactions found for **{hcp['name']}**."
                extracted = {"hcp_id": hcp["id"], "hcp_name": hcp["name"], "interaction_count": len(history)}
            else:
                response_text = f"Could not find an HCP named '{name}'. Try searching first."

        elif intent == "edit_interaction":
            # Extract interaction ID from message
            id_match = re.search(r"interaction\s*#?\s*(\d+)|id\s*:?\s*(\d+)", message, re.IGNORECASE)
            if id_match:
                interaction_id = int(id_match.group(1) or id_match.group(2))
                fields_to_update = {}
                sentiment = self.extract_sentiment(message)
                if sentiment != "Neutral":
                    fields_to_update["sentiment"] = sentiment
                topics = self.extract_topics(message)
                if topics != "General discussion":
                    fields_to_update["topics_discussed"] = topics

                if fields_to_update:
                    result = _execute_edit_interaction(interaction_id, **fields_to_update)
                    tool_calls.append({"tool": "edit_interaction", "args": {"interaction_id": interaction_id, **fields_to_update}, "result": result})
                    if "error" in result:
                        response_text = result["error"]
                    else:
                        response_text = f"✅ Interaction #{interaction_id} updated successfully."
                else:
                    response_text = "I detected an edit intent but couldn't determine which fields to update. Please specify what to change."
                extracted = {"interaction_id": interaction_id, "updates": fields_to_update}
            else:
                response_text = "Please specify which interaction to edit (e.g., 'edit interaction #1')."

        elif intent == "suggest_next_actions":
            hcp = self.resolve_hcp(name)
            if hcp:
                suggestions = _execute_suggest_next_actions(hcp["id"])
                tool_calls.append({"tool": "suggest_next_actions", "args": {"hcp_id": hcp["id"]}, "result": suggestions})
                response_text = f"📋 Suggested next actions for **{hcp['name']}**:\n\n"
                for idx, s in enumerate(suggestions.get("suggestions", []), 1):
                    response_text += f"{idx}. {s}\n"
                extracted = {"hcp_id": hcp["id"], "hcp_name": hcp["name"]}
            else:
                response_text = f"Could not find an HCP named '{name}'. Please search first."

        else:
            # General chat — provide a helpful response
            response_text = (
                "I'm your AI CRM assistant! I can help you with:\n\n"
                "• **Search HCPs** — e.g., *'Find Dr. Amanda Smith'*\n"
                "• **Log interactions** — e.g., *'I just met Dr. Smith. We discussed OncoBoost efficacy. She was very positive.'*\n"
                "• **View history** — e.g., *'Show history for Dr. Sharma'*\n"
                "• **Edit interactions** — e.g., *'Edit interaction #1, change sentiment to Negative'*\n"
                "• **Get suggestions** — e.g., *'Suggest next actions for Dr. Smith'*\n\n"
                "How can I help you today?"
            )

        return {
            "response": response_text,
            "tool_calls": tool_calls,
            "extracted_data": extracted,
        }


# ---------------------------------------------------------------------------
# Real LLM integration (Groq / gemma2-9b-it)
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    """System prompt that instructs the LLM on its role and available tools."""
    return """You are an AI assistant for a pharmaceutical CRM system that manages Healthcare Professional (HCP) interactions.

You have access to these tools:
1. search_hcps(query) - Search HCPs by name or specialty
2. log_interaction(hcp_id, type, date, time, topics_discussed, sentiment, outcomes, follow_up_actions, materials_shared, samples_distributed) - Log a new interaction
3. edit_interaction(interaction_id, ...fields) - Edit an existing interaction
4. get_hcp_history(hcp_id) - Get all interactions for an HCP
5. suggest_next_actions(hcp_id) - Get AI-suggested follow-up actions

When users describe meetings or interactions in natural language:
1. First search for the HCP to get their ID
2. Extract structured fields (type, date, topics, sentiment, outcomes, follow-ups)
3. Log the interaction with the extracted data
4. Offer to suggest next actions

Always respond in a professional, helpful manner. Format responses with markdown for readability.
If you need to call a tool, respond with a JSON block in this format:
```tool_call
{"tool": "tool_name", "args": {"param1": "value1"}}
```

Today's date is """ + datetime.utcnow().strftime("%Y-%m-%d")


class RealLLM:
    """Wrapper around ChatGroq for production use."""

    def __init__(self):
        from langchain_groq import ChatGroq
        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name="gemma2-9b-it",
            temperature=0.3,
            max_tokens=2048,
        )

    def generate_response(self, message: str, state: AgentState) -> dict:
        """Call the real LLM and parse tool calls from the response."""
        system = SystemMessage(content=_build_system_prompt())
        history = state.get("messages", [])

        # Build message list from state
        messages = [system] + history + [HumanMessage(content=message)]

        try:
            response = self.llm.invoke(messages)
            response_text = response.content

            # Parse tool calls from response (```tool_call ... ```)
            tool_calls = []
            extracted_data = {}
            tool_call_pattern = re.compile(
                r"```tool_call\s*\n?(.+?)\n?```", re.DOTALL
            )
            matches = tool_call_pattern.findall(response_text)

            for match in matches:
                try:
                    call = json.loads(match.strip())
                    tool_name = call.get("tool", "")
                    tool_args = call.get("args", {})

                    if tool_name in TOOL_DISPATCH:
                        result = TOOL_DISPATCH[tool_name](tool_args)
                        tool_calls.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result,
                        })
                        extracted_data.update(tool_args)
                except json.JSONDecodeError:
                    continue

            # Clean tool call blocks from the displayed response
            clean_response = tool_call_pattern.sub("", response_text).strip()
            if not clean_response and tool_calls:
                # If the LLM only produced tool calls, summarize the results
                summaries = []
                for tc in tool_calls:
                    summaries.append(f"Executed **{tc['tool']}** successfully.")
                clean_response = "\n".join(summaries)

            return {
                "response": clean_response or response_text,
                "tool_calls": tool_calls,
                "extracted_data": extracted_data,
            }
        except Exception as e:
            return {
                "response": f"I encountered an error processing your request: {str(e)}",
                "tool_calls": [],
                "extracted_data": {},
            }


# ---------------------------------------------------------------------------
# LangGraph workflow construction
# ---------------------------------------------------------------------------

# Session storage for conversation state
_sessions: dict[str, AgentState] = {}


def _get_llm():
    """Factory: return MockLLM or RealLLM based on configuration."""
    if settings.MOCK_AI_MODE or not settings.GROQ_API_KEY:
        return MockLLM()
    return RealLLM()


def _agent_node(state: AgentState) -> AgentState:
    """
    Agent node — invokes the LLM (or mock) to process the latest user message
    and decide whether to call tools.
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    # Get the last user message
    last_message = messages[-1]
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    llm = _get_llm()
    result = llm.generate_response(user_text, state)

    # Append AI response to messages
    new_messages = list(messages) + [AIMessage(content=result["response"])]

    return {
        "messages": new_messages,
        "extracted_data": result.get("extracted_data", {}),
        "tool_results": result.get("tool_calls", []),
        "current_hcp_id": state.get("current_hcp_id"),
    }


def _tool_node(state: AgentState) -> AgentState:
    """
    Tool node — executes any pending tool calls that weren't already
    executed inline by the LLM handler. In our architecture, tools are
    executed eagerly inside the LLM handler, so this node primarily
    updates the state with results and determines the next HCP context.
    """
    tool_results = state.get("tool_results", [])
    current_hcp_id = state.get("current_hcp_id")

    # Update current_hcp_id based on tool results
    for tc in tool_results:
        if tc["tool"] == "search_hcps" and tc.get("result"):
            results = tc["result"]
            if isinstance(results, list) and len(results) == 1:
                current_hcp_id = results[0]["id"]
        elif tc["tool"] == "log_interaction" and tc.get("result"):
            result = tc["result"]
            if isinstance(result, dict) and "hcp_id" in result:
                current_hcp_id = result["hcp_id"]

    return {
        **state,
        "current_hcp_id": current_hcp_id,
    }


def _should_use_tools(state: AgentState) -> Literal["tool_node", "__end__"]:
    """Conditional edge: route to tool_node if there are tool calls, else END."""
    tool_results = state.get("tool_results", [])
    if tool_results:
        return "tool_node"
    return "__end__"


def _build_graph() -> StateGraph:
    """Construct the LangGraph StateGraph with agent and tool nodes."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("agent_node", _agent_node)
    graph.add_node("tool_node", _tool_node)

    # Set entry point
    graph.set_entry_point("agent_node")

    # Conditional edges: agent_node → tool_node or END
    graph.add_conditional_edges(
        "agent_node",
        _should_use_tools,
        {
            "tool_node": "tool_node",
            "__end__": END,
        },
    )

    # tool_node always goes to END
    graph.add_edge("tool_node", END)

    return graph


# Compile the graph once at module level
_workflow = _build_graph().compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def process_chat(message: str, session_id: str) -> dict:
    """
    Process a user chat message through the LangGraph agent workflow.

    Args:
        message: The user's natural language message.
        session_id: Unique session identifier for conversation continuity.

    Returns:
        dict with keys: response (str), tool_calls (list), extracted_data (dict)
    """
    # Retrieve or initialise session state
    if session_id not in _sessions:
        _sessions[session_id] = AgentState(
            messages=[],
            extracted_data={},
            tool_results=[],
            current_hcp_id=None,
        )

    session = _sessions[session_id]

    # Append the new user message
    session["messages"].append(HumanMessage(content=message))

    # Run the LangGraph workflow
    result = _workflow.invoke(session)

    # Update session with the new state
    _sessions[session_id] = result

    # Extract the AI response (last AIMessage)
    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
    response_text = ai_messages[-1].content if ai_messages else "I'm sorry, I couldn't process that."

    return {
        "response": response_text,
        "tool_calls": result.get("tool_results", []),
        "extracted_data": result.get("extracted_data", {}),
    }


def get_tool_metadata() -> list[dict]:
    """Return metadata for all 5 available tools."""
    return TOOL_SCHEMAS
