import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { fetchToolsMetadata } from '../store/interactionSlice';

export default function ToolsPanel() {
  const dispatch = useDispatch();
  const { tools } = useSelector((state) => state.interaction);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    dispatch(fetchToolsMetadata());
  }, [dispatch]);

  // Fallback metadata if API is offline or hasn't loaded
  const fallbackTools = [
    {
      name: "search_hcps",
      description: "Search Healthcare Professionals by name or specialty. Returns matching HCP records."
    },
    {
      name: "log_interaction",
      description: "Log a new interaction with an HCP. Extracts structured fields (sentiment, topics, materials, follow-ups) from raw text and creates an Interaction record."
    },
    {
      name: "edit_interaction",
      description: "Edit an existing interaction record by ID. Accepts partial fields to update."
    },
    {
      name: "get_hcp_history",
      description: "Retrieve all past interactions for a given HCP, ordered by date (most recent first)."
    },
    {
      name: "suggest_next_actions",
      description: "Analyze recent interactions and suggest contextual follow-up actions such as sending brochures, scheduling follow-ups, or preparing clinical summaries."
    }
  ];

  const toolsList = tools && tools.length > 0 ? tools : fallbackTools;

  return (
    <div className="panel tools-panel" id="tools-panel" style={{ marginTop: '1.5rem' }}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="btn btn-secondary"
        style={{
          width: '100%',
          justifyContent: 'space-between',
          background: 'none',
          border: 'none',
          padding: 0,
        }}
        id="toggle-tools-panel-btn"
      >
        <span style={{ fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)' }}>
          🔧 LangGraph Agent Tools & Capabilities ({toolsList.length} Active)
        </span>
        <span style={{ color: 'var(--text-muted)' }}>{isOpen ? '▲ Collapse' : '▼ Expand'}</span>
      </button>

      {isOpen && (
        <div className="tools-grid" id="tools-grid">
          {toolsList.map((tool, idx) => (
            <div key={idx} className="tool-info-card" id={`tool-card-${tool.name}`}>
              <h4>
                ⚙️ {tool.name}
              </h4>
              <p>{tool.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
