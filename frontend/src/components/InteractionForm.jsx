import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  updateFormField,
  resetForm,
  createInteraction,
  updateInteraction,
  addMaterialShared,
  removeMaterialShared,
  addSampleDistributed,
  removeSampleDistributed,
} from '../store/interactionSlice';

export default function InteractionForm() {
  const dispatch = useDispatch();
  const { form, hcps, editingInteractionId, isLoading } = useSelector((state) => state.interaction);
  
  const [materialInput, setMaterialInput] = useState('');
  const [sampleInput, setSampleInput] = useState('');
  const [isListening, setIsListening] = useState(false); // Voice note simulation state

  // Dynamic UI-level suggested follow-ups
  const getSuggestions = () => {
    const suggestions = [];
    if (form.sentiment === 'Positive') {
      suggestions.push('Schedule follow-up meeting in 2 weeks');
    }
    if (form.topics_discussed?.toLowerCase().includes('oncoboost')) {
      suggestions.push('Send OncoBoost Phase III PDF Brochure');
    }
    if (form.topics_discussed?.toLowerCase().includes('efficacy') || form.topics_discussed?.toLowerCase().includes('safety')) {
      suggestions.push('Add Dr. to advisory board invite list');
    }
    return suggestions.length > 0 ? suggestions : [
      'Schedule follow-up meeting in 2 weeks',
      'Send OncoBoost Phase III PDF Brochure',
      'Add Dr. to advisory board invite list'
    ];
  };

  const handleFieldChange = (field, value) => {
    dispatch(updateFormField({ field, value }));
  };

  const handleAddMaterial = (e) => {
    e.preventDefault();
    if (materialInput.trim()) {
      dispatch(addMaterialShared(materialInput));
      setMaterialInput('');
    }
  };

  const handleAddSample = (e) => {
    e.preventDefault();
    if (sampleInput.trim()) {
      dispatch(addSampleDistributed(sampleInput));
      setSampleInput('');
    }
  };

  const applySuggestion = (suggestion) => {
    const selectedHcp = hcps.find(h => h.id === parseInt(form.hcp_id));
    let finalSuggestion = suggestion;
    if (selectedHcp && suggestion.includes('Add Dr. to')) {
      finalSuggestion = suggestion.replace('Dr.', selectedHcp.name);
    }
    
    const currentActions = form.follow_up_actions ? form.follow_up_actions + '\n' : '';
    if (!currentActions.includes(finalSuggestion)) {
      handleFieldChange('follow_up_actions', currentActions + finalSuggestion);
    }
  };

  const handleVoiceNoteSimulation = () => {
    setIsListening(true);
    // Simulate recording for 2 seconds, then append topics
    setTimeout(() => {
      setIsListening(false);
      const voiceText = "Met with the doctor. Discussed efficacy trials of OncoBoost. Patient safety is a key priority. Doctor was positive.";
      handleFieldChange('topics_discussed', (form.topics_discussed ? form.topics_discussed + '\n' : '') + voiceText);
      handleFieldChange('sentiment', 'Positive');
      alert("🎙️ Voice Note transcribed!\nText: \"" + voiceText + "\"");
    }, 1800);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.hcp_id) {
      alert("Please select a Healthcare Professional.");
      return;
    }
    
    if (editingInteractionId) {
      dispatch(updateInteraction({ id: editingInteractionId, data: form }));
    } else {
      dispatch(createInteraction(form));
    }
  };

  return (
    <form className="panel form-panel" onSubmit={handleSubmit} id="log-interaction-form">
      <div className="panel-header">
        <h2>
          <span>📝</span> {editingInteractionId ? 'Edit HCP Interaction' : 'Interaction Details'}
        </h2>
        {editingInteractionId && (
          <span className="sentiment-badge neutral" style={{fontSize: '0.8rem'}}>
            Editing Mode (ID: {editingInteractionId})
          </span>
        )}
      </div>

      <div className="form-grid">
        {/* HCP Name */}
        <div className="form-group-full">
          <label htmlFor="form-hcp-id">HCP Name</label>
          <select
            id="form-hcp-id"
            value={form.hcp_id}
            onChange={(e) => handleFieldChange('hcp_id', e.target.value)}
            required
            className="form-select"
            style={{ width: '100%' }}
          >
            <option value="">Select or search HCP...</option>
            {hcps.map((hcp) => (
              <option key={hcp.id} value={hcp.id}>
                {hcp.name} ({hcp.specialty} — {hcp.clinic})
              </option>
            ))}
          </select>
        </div>

        {/* Interaction Type */}
        <div>
          <label htmlFor="form-type">Interaction Type</label>
          <select
            id="form-type"
            value={form.type}
            onChange={(e) => handleFieldChange('type', e.target.value)}
            className="form-select"
            style={{ width: '100%' }}
          >
            <option value="Meeting">Meeting</option>
            <option value="Call">Call</option>
            <option value="Email">Email</option>
            <option value="Lunch">Lunch</option>
            <option value="Video Conference">Video Conference</option>
            <option value="Conference">Conference</option>
          </select>
        </div>

        {/* Date */}
        <div>
          <label htmlFor="form-date">Date</label>
          <input
            type="date"
            id="form-date"
            value={form.date}
            onChange={(e) => handleFieldChange('date', e.target.value)}
            required
            className="form-input"
            style={{ width: '100%' }}
          />
        </div>

        {/* Time */}
        <div>
          <label htmlFor="form-time">Time</label>
          <input
            type="time"
            id="form-time"
            value={form.time}
            onChange={(e) => handleFieldChange('time', e.target.value)}
            required
            className="form-input"
            style={{ width: '100%' }}
          />
        </div>

        {/* Attendees */}
        <div>
          <label htmlFor="form-attendees">Attendees</label>
          <input
            type="text"
            id="form-attendees"
            placeholder="e.g. Dr. Smith, Rep John Doe"
            value={form.attendees}
            onChange={(e) => handleFieldChange('attendees', e.target.value)}
            className="form-input"
            style={{ width: '100%' }}
          />
        </div>

        {/* Topics Discussed */}
        <div className="form-group-full">
          <label htmlFor="form-topics">Topics Discussed</label>
          <textarea
            id="form-topics"
            placeholder="Enter discussion points, clinical trials details discussed, etc."
            rows={4}
            value={form.topics_discussed}
            onChange={(e) => handleFieldChange('topics_discussed', e.target.value)}
            className="form-textarea"
            style={{ width: '100%', resize: 'vertical' }}
          />
        </div>

        {/* Voice Note Simulation */}
        <div className="form-group-full">
          <button
            type="button"
            onClick={handleVoiceNoteSimulation}
            disabled={isListening}
            className="btn btn-secondary"
            style={{ width: '100%', justifyContent: 'center' }}
            id="voice-note-btn"
          >
            {isListening ? (
              <>
                <span className="spinner"></span> Transcribing Voice Note...
              </>
            ) : (
              '🎙️ Summarize from Voice Note (Requires Consent)'
            )}
          </button>
        </div>

        {/* Materials Shared */}
        <div className="form-group-full">
          <label>Materials Shared / Samples Distributed</label>
          <div className="chips-input-container">
            <input
              type="text"
              placeholder="Add shared materials (e.g. Brochure PDF)"
              value={materialInput}
              onChange={(e) => setMaterialInput(e.target.value)}
              className="form-input"
              id="material-input-field"
            />
            <button
              type="button"
              onClick={handleAddMaterial}
              className="btn btn-secondary"
              id="add-material-btn"
            >
              Add Material
            </button>
          </div>
          <div className="chips-list">
            {form.materials_shared.map((mat, idx) => (
              <span key={idx} className="chip">
                📄 {mat}
                <button
                  type="button"
                  onClick={() => dispatch(removeMaterialShared(idx))}
                  className="chip-remove"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Samples Distributed */}
        <div className="form-group-full">
          <div className="chips-input-container" style={{ marginTop: '0.5rem' }}>
            <input
              type="text"
              placeholder="Add distributed samples (e.g. Starter Kit)"
              value={sampleInput}
              onChange={(e) => setSampleInput(e.target.value)}
              className="form-input"
              id="sample-input-field"
            />
            <button
              type="button"
              onClick={handleAddSample}
              className="btn btn-secondary"
              id="add-sample-btn"
            >
              Add Sample
            </button>
          </div>
          <div className="chips-list">
            {form.samples_distributed.map((samp, idx) => (
              <span key={idx} className="chip">
                📦 {samp}
                <button
                  type="button"
                  onClick={() => dispatch(removeSampleDistributed(idx))}
                  className="chip-remove"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Observed HCP Sentiment */}
        <div className="form-group-full">
          <label>Observed/Inferred HCP Sentiment</label>
          <div className="sentiment-selector">
            {['Positive', 'Neutral', 'Negative'].map((sent) => (
              <button
                key={sent}
                type="button"
                className={`sentiment-btn ${form.sentiment === sent ? 'active' : ''} ${sent.toLowerCase()}`}
                onClick={() => handleFieldChange('sentiment', sent)}
                id={`sentiment-btn-${sent.toLowerCase()}`}
              >
                {sent === 'Positive' && '😊 '}
                {sent === 'Neutral' && '😐 '}
                {sent === 'Negative' && '😟 '}
                {sent}
              </button>
            ))}
          </div>
        </div>

        {/* Outcomes */}
        <div className="form-group-full">
          <label htmlFor="form-outcomes">Outcomes</label>
          <textarea
            id="form-outcomes"
            placeholder="Key outcomes, agreements, or objections..."
            rows={2}
            value={form.outcomes}
            onChange={(e) => handleFieldChange('outcomes', e.target.value)}
            className="form-textarea"
            style={{ width: '100%', resize: 'vertical' }}
          />
        </div>

        {/* Follow-up Actions */}
        <div className="form-group-full">
          <label htmlFor="form-followups">Follow-up Actions</label>
          <textarea
            id="form-followups"
            placeholder="Next steps, actions, or tasks..."
            rows={2}
            value={form.follow_up_actions}
            onChange={(e) => handleFieldChange('follow_up_actions', e.target.value)}
            className="form-textarea"
            style={{ width: '100%', resize: 'vertical' }}
          />
        </div>
      </div>

      {/* AI Suggested Follow-ups */}
      <div className="ai-suggestions-list">
        <h4>✨ AI Suggested Follow-ups (Click to Apply)</h4>
        <div className="ai-suggestions-container">
          {getSuggestions().map((sug, idx) => (
            <div
              key={idx}
              className="ai-suggestion-item"
              onClick={() => applySuggestion(sug)}
              id={`ai-suggestion-item-${idx}`}
            >
              {sug}
            </div>
          ))}
        </div>
      </div>

      {/* Form Submission Actions */}
      <div className="form-actions">
        <button
          type="button"
          onClick={() => dispatch(resetForm())}
          className="btn btn-secondary"
          id="form-reset-btn"
        >
          Reset
        </button>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading}
          id="form-submit-btn"
        >
          {isLoading ? (
            <>
              <span className="spinner"></span> Saving...
            </>
          ) : editingInteractionId ? (
            'Update Interaction'
          ) : (
            'Log Interaction'
          )}
        </button>
      </div>
    </form>
  );
}
