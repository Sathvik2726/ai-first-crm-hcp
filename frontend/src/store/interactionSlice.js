import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const API_BASE = 'http://localhost:8000/api';

const initialFormState = {
  hcp_id: '',
  type: 'Meeting',
  date: new Date().toISOString().split('T')[0],
  time: new Date().toTimeString().slice(0, 5),
  attendees: '',
  topics_discussed: '',
  sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: '',
  materials_shared: [],
  samples_distributed: [],
};

const initialState = {
  form: initialFormState,
  editingInteractionId: null, // Track if we're editing an existing interaction
  chatMessages: [
    {
      role: 'ai',
      content: "Hello! I'm your CRM AI Assistant. You can describe your HCP interactions in natural language, and I will help you log them.\n\nTry saying:\n*\"I just met Dr. Amanda Smith. Discussed efficacy of OncoBoost. She was positive and requested the Phase III trial PDF.\"*",
      timestamp: new Date().toLocaleTimeString().slice(0, 5),
    }
  ],
  hcps: [],
  interactions: [],
  tools: [],
  isLoading: false,
  chatLoading: false,
  error: null,
  sessionId: Math.random().toString(36).substring(2, 15),
};

// Async Thunks
export const fetchHcps = createAsyncThunk(
  'interaction/fetchHcps',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/hcps`);
      if (!response.ok) throw new Error('Failed to fetch HCPs');
      return await response.json();
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const fetchInteractions = createAsyncThunk(
  'interaction/fetchInteractions',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/interactions`);
      if (!response.ok) throw new Error('Failed to fetch interactions');
      return await response.json();
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const fetchToolsMetadata = createAsyncThunk(
  'interaction/fetchToolsMetadata',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/agent/tools`);
      if (!response.ok) throw new Error('Failed to fetch agent tools');
      const data = await response.json();
      return data.tools || [];
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const createInteraction = createAsyncThunk(
  'interaction/createInteraction',
  async (interactionData, { dispatch, rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/interactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(interactionData),
      });
      if (!response.ok) throw new Error('Failed to log interaction');
      const newInteraction = await response.json();
      dispatch(fetchInteractions());
      return newInteraction;
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const updateInteraction = createAsyncThunk(
  'interaction/updateInteraction',
  async ({ id, data }, { dispatch, rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/interactions/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error('Failed to update interaction');
      const updated = await response.json();
      dispatch(fetchInteractions());
      return updated;
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const deleteInteraction = createAsyncThunk(
  'interaction/deleteInteraction',
  async (id, { dispatch, rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/interactions/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete interaction');
      dispatch(fetchInteractions());
      return id;
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const sendChatMessage = createAsyncThunk(
  'interaction/sendChatMessage',
  async ({ message, sessionId }, { dispatch, rejectWithValue }) => {
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId }),
      });
      if (!response.ok) throw new Error('Chat request failed');
      const data = await response.json();
      
      // If the backend has logged an interaction or returned extracted fields,
      // update the form state in the UI.
      if (data.extracted_data && Object.keys(data.extracted_data).length > 0) {
        dispatch(autoFillForm(data.extracted_data));
      }
      
      // Refresh interactions list as a tool call might have updated the DB
      dispatch(fetchInteractions());
      
      return data;
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

// Slice Definition
const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    updateFormField: (state, action) => {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    resetForm: (state) => {
      state.form = {
        ...initialFormState,
        date: new Date().toISOString().split('T')[0],
        time: new Date().toTimeString().slice(0, 5),
      };
      state.editingInteractionId = null;
    },
    loadInteractionToForm: (state, action) => {
      const interaction = action.payload;
      state.form = {
        hcp_id: interaction.hcp_id,
        type: interaction.type,
        date: interaction.date,
        time: interaction.time,
        attendees: interaction.attendees || '',
        topics_discussed: interaction.topics_discussed || '',
        sentiment: interaction.sentiment || 'Neutral',
        outcomes: interaction.outcomes || '',
        follow_up_actions: interaction.follow_up_actions || '',
        materials_shared: interaction.materials_shared || [],
        samples_distributed: interaction.samples_distributed || [],
      };
      state.editingInteractionId = interaction.id;
    },
    autoFillForm: (state, action) => {
      const data = action.payload;
      
      // Map extracted variables to form fields
      if (data.hcp_id !== undefined) state.form.hcp_id = data.hcp_id;
      if (data.type !== undefined) state.form.type = data.type;
      if (data.date !== undefined) state.form.date = data.date;
      if (data.time !== undefined) state.form.time = data.time;
      if (data.sentiment !== undefined) state.form.sentiment = data.sentiment;
      if (data.topics_discussed !== undefined) state.form.topics_discussed = data.topics_discussed;
      if (data.outcomes !== undefined) state.form.outcomes = data.outcomes;
      if (data.follow_up_actions !== undefined) state.form.follow_up_actions = data.follow_up_actions;
      if (data.materials_shared !== undefined) state.form.materials_shared = data.materials_shared;
      if (data.samples_distributed !== undefined) state.form.samples_distributed = data.samples_distributed;
    },
    addMaterialShared: (state, action) => {
      const value = action.payload.trim();
      if (value && !state.form.materials_shared.includes(value)) {
        state.form.materials_shared.push(value);
      }
    },
    removeMaterialShared: (state, action) => {
      state.form.materials_shared.splice(action.payload, 1);
    },
    addSampleDistributed: (state, action) => {
      const value = action.payload.trim();
      if (value && !state.form.samples_distributed.includes(value)) {
        state.form.samples_distributed.push(value);
      }
    },
    removeSampleDistributed: (state, action) => {
      state.form.samples_distributed.splice(action.payload, 1);
    },
    addUserChatMessage: (state, action) => {
      state.chatMessages.push({
        role: 'user',
        content: action.payload,
        timestamp: new Date().toLocaleTimeString().slice(0, 5),
      });
    },
  },
  extraReducers: (builder) => {
    // HCPs
    builder.addCase(fetchHcps.pending, (state) => {
      state.isLoading = true;
    });
    builder.addCase(fetchHcps.fulfilled, (state, action) => {
      state.isLoading = false;
      state.hcps = action.payload;
    });
    builder.addCase(fetchHcps.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload;
    });

    // Interactions
    builder.addCase(fetchInteractions.pending, (state) => {
      // Let it load silently or handle loading
    });
    builder.addCase(fetchInteractions.fulfilled, (state, action) => {
      state.interactions = action.payload;
    });

    // Tools metadata
    builder.addCase(fetchToolsMetadata.fulfilled, (state, action) => {
      state.tools = action.payload;
    });

    // Submit / Update Interaction
    builder.addCase(createInteraction.pending, (state) => {
      state.isLoading = true;
    });
    builder.addCase(createInteraction.fulfilled, (state) => {
      state.isLoading = false;
      // Reset form on success
      state.form = {
        ...initialFormState,
        date: new Date().toISOString().split('T')[0],
        time: new Date().toTimeString().slice(0, 5),
      };
    });
    builder.addCase(createInteraction.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload;
    });

    builder.addCase(updateInteraction.pending, (state) => {
      state.isLoading = true;
    });
    builder.addCase(updateInteraction.fulfilled, (state) => {
      state.isLoading = false;
      state.form = {
        ...initialFormState,
        date: new Date().toISOString().split('T')[0],
        time: new Date().toTimeString().slice(0, 5),
      };
      state.editingInteractionId = null;
    });
    builder.addCase(updateInteraction.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload;
    });

    // Chat Message
    builder.addCase(sendChatMessage.pending, (state) => {
      state.chatLoading = true;
    });
    builder.addCase(sendChatMessage.fulfilled, (state, action) => {
      state.chatLoading = false;
      const { response, tool_calls } = action.payload;
      state.chatMessages.push({
        role: 'ai',
        content: response,
        tool_calls: tool_calls || [],
        timestamp: new Date().toLocaleTimeString().slice(0, 5),
      });
    });
    builder.addCase(sendChatMessage.rejected, (state, action) => {
      state.chatLoading = false;
      state.chatMessages.push({
        role: 'ai',
        content: `Error: ${action.payload || 'Failed to connect to the agent.'}`,
        timestamp: new Date().toLocaleTimeString().slice(0, 5),
      });
    });
  },
});

export const {
  updateFormField,
  resetForm,
  loadInteractionToForm,
  autoFillForm,
  addMaterialShared,
  removeMaterialShared,
  addSampleDistributed,
  removeSampleDistributed,
  addUserChatMessage,
} = interactionSlice.actions;

export default interactionSlice.reducer;
