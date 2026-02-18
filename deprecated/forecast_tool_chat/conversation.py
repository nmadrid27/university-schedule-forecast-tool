"""
Conversation state management for the chat interface.
Handles message history, context tracking, and session state.
"""

import streamlit as st
from typing import List, Dict, Any
from datetime import datetime


class ConversationManager:
    """Manage chat conversation state and history."""

    def __init__(self):
        """Initialize conversation manager with session state."""
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'context' not in st.session_state:
            st.session_state.context = {}

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """
        Add a message to the conversation history.

        Args:
            role: 'user' or 'assistant'
            content: Message text
            metadata: Optional metadata (intent, parameters, etc.)
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        st.session_state.messages.append(message)

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages in the conversation."""
        return st.session_state.messages

    def get_last_user_message(self) -> Dict[str, Any]:
        """Get the most recent user message."""
        for message in reversed(st.session_state.messages):
            if message['role'] == 'user':
                return message
        return None

    def clear_history(self):
        """Clear conversation history."""
        st.session_state.messages = []

    def update_context(self, key: str, value: Any):
        """
        Update conversation context.

        Args:
            key: Context key (e.g., 'uploaded_files', 'current_forecast')
            value: Context value
        """
        st.session_state.context[key] = value

    def get_context(self, key: str = None) -> Any:
        """
        Get conversation context.

        Args:
            key: Optional specific key to retrieve

        Returns:
            Context value if key provided, otherwise entire context dict
        """
        if key:
            return st.session_state.context.get(key)
        return st.session_state.context

    def has_data(self) -> bool:
        """Check if user has uploaded data."""
        return bool(st.session_state.context.get('uploaded_files') or
                   st.session_state.context.get('historical_data_loaded'))

    def has_forecast(self) -> bool:
        """Check if a forecast has been generated."""
        return bool(st.session_state.context.get('current_forecast'))

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation for context."""
        messages = self.get_messages()
        if not messages:
            return "No conversation history."

        summary_parts = []
        for msg in messages[-5:]:  # Last 5 messages
            role = "User" if msg['role'] == 'user' else "Assistant"
            summary_parts.append(f"{role}: {msg['content'][:100]}...")

        return "\n".join(summary_parts)
