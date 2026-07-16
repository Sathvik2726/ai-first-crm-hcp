import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { fetchInteractions, loadInteractionToForm, deleteInteraction } from '../store/interactionSlice';

export default function PastInteractions() {
  const dispatch = useDispatch();
  const { interactions, isLoading } = useSelector((state) => state.interaction);

  useEffect(() => {
    dispatch(fetchInteractions());
  }, [dispatch]);

  const handleEdit = (interaction) => {
    dispatch(loadInteractionToForm(interaction));
    // Smooth scroll back to form
    const formElement = document.getElementById('log-interaction-form');
    if (formElement) {
      formElement.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleDelete = (id) => {
    if (window.confirm("Are you sure you want to delete this logged interaction?")) {
      dispatch(deleteInteraction(id));
    }
  };

  return (
    <div className="panel history-panel" id="past-interactions-panel">
      <div className="panel-header">
        <h2>
          <span>📜</span> Past Logged Interactions
          <span
            className="chip"
            style={{
              background: 'var(--accent-primary)',
              color: 'white',
              fontSize: '0.8rem',
              padding: '0.1rem 0.5rem',
              borderRadius: '12px',
              border: 'none',
            }}
          >
            {interactions.length} Total
          </span>
        </h2>
      </div>

      {isLoading && interactions.length === 0 ? (
        <div className="loading-container" id="history-loading">
          <span className="spinner spinner-large"></span>
          <p>Loading interaction history...</p>
        </div>
      ) : interactions.length === 0 ? (
        <div className="empty-state" id="history-empty">
          <p>No interactions logged yet. Log one via the form or describe it to the AI Assistant!</p>
        </div>
      ) : (
        <div className="interactions-list" id="interactions-grid">
          {interactions.map((item) => (
            <div key={item.id} className="interaction-card" id={`interaction-card-${item.id}`}>
              <div className="card-header">
                <div>
                  <h3 className="hcp-name">{item.hcp_name}</h3>
                  <span className="hcp-specialty">Type: {item.type}</span>
                </div>
                <span className={`sentiment-badge ${item.sentiment.toLowerCase()}`}>
                  {item.sentiment}
                </span>
              </div>

              <div className="card-metadata">
                <span>📅 {item.date}</span>
                <span>⏰ {item.time}</span>
              </div>

              <div className="card-body">
                <strong>Discussed:</strong> {item.topics_discussed || 'No details provided.'}
              </div>

              <div className="card-sections">
                {item.outcomes && (
                  <div>
                    <span className="card-section-title">Outcomes</span>
                    <p style={{ color: 'var(--text-primary)' }}>{item.outcomes}</p>
                  </div>
                )}
                {item.follow_up_actions && (
                  <div>
                    <span className="card-section-title">Follow-up Actions</span>
                    <p style={{ color: 'var(--accent-secondary)' }}>{item.follow_up_actions}</p>
                  </div>
                )}
                {item.materials_shared && item.materials_shared.length > 0 && (
                  <div style={{ marginTop: '0.2rem' }}>
                    <span className="card-section-title">Materials</span>
                    <div className="chips-list">
                      {item.materials_shared.map((m, idx) => (
                        <span key={idx} className="chip" style={{ fontSize: '0.7rem' }}>
                          📄 {m}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {item.samples_distributed && item.samples_distributed.length > 0 && (
                  <div style={{ marginTop: '0.2rem' }}>
                    <span className="card-section-title">Samples</span>
                    <div className="chips-list">
                      {item.samples_distributed.map((s, idx) => (
                        <span key={idx} className="chip" style={{ fontSize: '0.7rem' }}>
                          📦 {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="card-actions">
                <button
                  type="button"
                  onClick={() => handleEdit(item)}
                  className="btn btn-secondary"
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                  id={`edit-btn-${item.id}`}
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(item.id)}
                  className="btn btn-danger"
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                  id={`delete-btn-${item.id}`}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
