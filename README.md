# AI-First CRM HCP Module — Log Interaction Screen

This project is a complete, production-ready implementation of an AI-first Customer Relationship Management (CRM) module focused on the Healthcare Professional (HCP) workflow. It features a dual-interface **Log Interaction Screen**:
1. **Structured Form Interface**: For manual logging, editing, and checking details.
2. **Conversational AI Assistant**: Powered by **LangGraph**, which parses raw interactions, searches HCP profiles, auto-fills form fields, and performs database actions.

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    subgraph Frontend (React + Redux)
        UI[Log Interaction UI] <--> Store[Redux Store]
        UI <--> Chat[AI Assistant Panel]
    end
    subgraph Backend (FastAPI + LangGraph)
        API[FastAPI Server] <--> Graph[LangGraph Workflow]
        Graph <--> Tools[Agent Tools]
        Tools <--> DB[(SQLite/PostgreSQL)]
        API <--> DB
    end
```

---

## 🤖 Role of the LangGraph Agent

The LangGraph Agent manages stateful, multi-turn conversations with the field representative. Instead of forcing representatives to fill out complex forms manually, the agent allows them to type or transcribe their meeting notes in raw text.

### The Agent Workflow
1. **State Definition**: The agent carries a session state containing the `messages` list (chat history), `extracted_data` (fields parsed from text), and `current_hcp_id` (contextual focus).
2. **LLM Node**: The agent processes the raw message using a state-of-the-art LLM (`gemma2-9b-it` or `llama-3.3-70b-versatile` via Groq).
3. **Eager Tool Execution**: The agent translates intent into tool calls. When the LLM decides to call a tool, the corresponding backend function executes immediately and returns data.
4. **Conditional Routing**: The agent decides if it needs to execute more actions or return the final answer.
5. **UI Synchronization**: The frontend intercepts the agent's response. Any extracted structured data (HCP name, topics discussed, sentiment, materials, follow-ups) is immediately dispatched to the Redux store to **auto-populate the form**.

---

## 🛠️ The 5 LangGraph Agent Tools

The agent utilizes 5 custom python tools to orchestrate sales activities:

1. **`search_hcps`**:
   - *Arguments*: `query` (string)
   - *Description*: Searches for HCPs by name or specialty in the database. Returns matching profiles.
2. **`log_interaction`** (Mandatory):
   - *Arguments*: `hcp_id`, `type`, `date`, `time`, `topics_discussed`, `sentiment`, `outcomes`, `follow_up_actions`, `materials_shared`, `samples_distributed`
   - *Description*: Logs a structured interaction record. The LLM automatically performs entity extraction and summarizes discussions if partial notes are provided.
3. **`edit_interaction`** (Mandatory):
   - *Arguments*: `interaction_id`, plus any fields to update (e.g. `sentiment`, `topics_discussed`, etc.)
   - *Description*: Allows modification of a logged interaction record.
4. **`get_hcp_history`**:
   - *Arguments*: `hcp_id`
   - *Description*: Retrieves all past logged interactions for a specific HCP.
5. **`suggest_next_actions`**:
   - *Arguments*: `hcp_id`
   - *Description*: Analyzes the most recent interaction details and suggests contextual next steps (e.g. send specific materials, schedule follow-ups).

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm

### Setup Database & Environment Variables
Copy `.env.example` to `.env` in the root folder:
```bash
cp .env.example .env
```
By default, `MOCK_AI_MODE=True` is enabled so you can run and evaluate all agent actions immediately without requiring a Groq API Key. To use a live LLM, set your key in `GROQ_API_KEY` and set `MOCK_AI_MODE=False`.

### Run the Backend (FastAPI)
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
The backend API documentation will be available at `http://localhost:8000/docs` and the database will automatically initialize and seed with default HCPs (such as Dr. Amanda Smith and Dr. Rajesh Sharma) on startup.

### Run the Frontend (Vite + React + Redux)
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
The frontend application will load at `http://localhost:3000`.

---

## 🎥 Video Demonstration Script (10–15 mins)

Use this script to record a professional walkthrough of all 5 tools:

### Step 1: Search HCPs Tool (`search_hcps`)
- **Action**: Type into the chat input: *"Who is Dr. Smith?"* or *"Search for oncologists"*.
- **Result**: The agent calls `search_hcps` and displays the matching records (Dr. Amanda Smith, Oncology, Metro Cancer Center).

### Step 2: Log Interaction Tool (`log_interaction`)
- **Action**: Type into the chat input:
  > *"I just met Dr. Amanda Smith. Discussed efficacy of OncoBoost. She was positive. We need to schedule a follow-up in 2 weeks and send the OncoBoost Phase III PDF."*
- **Result**: The agent calls `log_interaction` with extracted fields:
  - **HCP ID**: 1 (Dr. Amanda Smith)
  - **Topics**: OncoBoost, Efficacy
  - **Sentiment**: Positive
  - **Follow-ups**: Schedule follow-up meeting; Send Phase III PDF
  - The form on the left **instantly auto-populates** with all these details!
  - The interaction is added to the database and appears in the "Past Logged Interactions" list.

### Step 3: Suggest Next Actions Tool (`suggest_next_actions`)
- **Action**: Type into the chat: *"What should I do next for Dr. Amanda Smith?"*
- **Result**: The agent runs `suggest_next_actions` and recommends:
  - Scheduling a follow-up meeting within 2 weeks.
  - Sending the latest Phase III clinical trial results.
  - Preparing an efficacy comparison deck (OncoBoost vs. Standard of Care).

### Step 4: Edit Interaction Tool (`edit_interaction`)
- **Action**: Locate the interaction ID in the bottom list (e.g. ID `2`). Type in chat:
  > *"Update interaction 2, set sentiment to Negative and topics discussed to concerns about dosing side effects."*
- **Result**: The agent calls `edit_interaction` and modifies the record in the database. The bottom list updates instantly.

### Step 5: Get History Tool (`get_hcp_history`)
- **Action**: Type in chat: *"Show interaction history for Dr. Amanda Smith"*
- **Result**: The agent calls `get_hcp_history` and displays the formatted list of all past meetings, topics, and sentiments.

### Step 6: Form Features (Voice & Manual entry)
- **Action**: Click the **"🎙️ Summarize from Voice Note"** button on the form.
- **Result**: Simulates transcribing audio. The topics are transcribed, sentiment updates to Positive, and suggestions update.
- **Action**: Edit fields manually, add a Material Shared chip (e.g. "Dosing Brochure"), and click **"Log Interaction"** to log.
