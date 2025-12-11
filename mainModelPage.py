import streamlit as st
import json
import os
from datetime import datetime
from google import genai

# --- Configuration & Setup ---

# Mapping user-friendly names to actual API model IDs
MODEL_MAPPING = {
    "Gemini3 pro": "gemini-3-pro-preview", 
    # Add other models here when available
}

# Key for storing history in Streamlit Session State
HISTORY_KEY = "chat_history"

# --- Helper Functions ---

def initialize_history():
    """Initializes the history list in Streamlit's Session State."""
    if HISTORY_KEY not in st.session_state:
        # History is a list of interaction dictionaries
        st.session_state[HISTORY_KEY] = []

def save_interaction_to_session(model_name, prompt, response):
    """Appends a new interaction to the Session State history."""
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "prompt": prompt,
        "response": response
    }
    
    st.session_state[HISTORY_KEY].append(entry)
    
    # --- IMPORTANT NOTE ON PERSISTENCE ---
    # To truly save data across restarts and all users, 
    # the code below would replace the line above, connecting to a database:
    # 
    # try:
    #     save_to_database(entry) 
    #     st.success("Interaction saved to persistent DB.")
    # except Exception as e:
    #     st.error(f"Failed to save to persistent DB: {e}")


def get_ai_response(model_selection, user_prompt): 
    """Routes the prompt to the correct API based on selection."""

    # Ensure API keys are loaded from secrets.toml
    try:
        api_key = st.secrets["api_keys"]["google"]
    except KeyError:
        return "Error: Gemini API key not found in `st.secrets['api_keys']['google']`."

    try:
        if model_selection in MODEL_MAPPING:
            client = genai.Client(api_key=api_key)
            model_id = MODEL_MAPPING[model_selection]

            response = client.models.generate_content(
                model=model_id,
                contents=user_prompt
            )
            return response.text
        else:
            return "Error: Selected model not configured in backend."

    except Exception as e:
        return f"Error calling API: {str(e)}"

# --- Streamlit Interface ---

# Initialize the history when the app loads
initialize_history()

st.title("🤖 Gemini Interface")
st.markdown("---")

### 1. Model Configuration

col1, col2 = st.columns([1, 2])

with col1:
    selected_label = st.selectbox(
        "Select AI Model",
        options=list(MODEL_MAPPING.keys()),
        help="Choose the desired Gemini model for generation."
    )

### 2. User Input Area

user_prompt = st.text_area(
    "💬 Enter your prompt:", 
    height=150,
    placeholder="Ask Gemini anything..."
)

# 3. Generate Button
if st.button("🚀 Generate Response", type="primary"):
    if not user_prompt.strip():
        st.warning("Please enter a prompt before generating a response.")
    else:
        with st.spinner(f"Asking {selected_label}..."):
            # Get response from the actual API
            ai_reply = get_ai_response(selected_label, user_prompt)
            
            # Display response
            st.markdown("### ✨ Response")
            st.code(ai_reply, language="markdown") # Use code block for clean formatting
            
            # Save to Session State
            save_interaction_to_session(selected_label, user_prompt, ai_reply)
            st.success("Interaction saved to current session history.")

st.markdown("---")

### Optional: View History (Admin/Debugging)

with st.expander("View Current Session History"):
    history = st.session_state[HISTORY_KEY]
    
    if not history:
        st.info("No interactions recorded in this session yet.")
    else:
        # Display history in reverse chronological order
        for i, entry in enumerate(reversed(history)):
            st.markdown(f"**{len(history) - i}. Timestamp:** `{entry['timestamp'][:19]}` | **Model:** `{entry['model']}`")
            st.markdown(f"**Prompt:** *{entry['prompt'][:80]}...*")
            st.code(entry['response'][:150] + "...", language="markdown")
            st.markdown("---")