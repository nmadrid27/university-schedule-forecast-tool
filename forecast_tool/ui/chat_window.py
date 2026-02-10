"""
Chat window component for the Streamlit UI.
Left panel: natural language input and conversation history with shadcn styling.
"""

import streamlit as st
from datetime import datetime
from forecast_tool.chat.conversation import ConversationManager
from forecast_tool.chat.command_parser import CommandParser
from forecast_tool.chat.responses import format_welcome_message
from forecast_tool.ui.components import button, badge


def render_chat_window():
    """Render the enhanced chat interface in the left column."""

    # Header with badge
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 💬 Chat Assistant")
    with col2:
        st.markdown(
            badge("Online", variant="default"),
            unsafe_allow_html=True
        )

    st.markdown(
        '<p class="text-sm text-muted-foreground mb-4">Ask me anything about forecasting</p>',
        unsafe_allow_html=True
    )

    # Initialize conversation manager and parser
    conv = ConversationManager()
    parser = CommandParser()

    # Display welcome message if no history
    if not conv.get_messages():
        welcome = format_welcome_message()
        conv.add_message('assistant', welcome)

    # Chat message container with custom styling
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)

    # Display conversation history
    for idx, message in enumerate(conv.get_messages()):
        role = message['role']
        content = message['content']
        timestamp = message.get('timestamp', '')

        # Format timestamp
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%I:%M %p")
            else:
                time_str = ""
        except (ValueError, TypeError):
            time_str = ""

        with st.chat_message(role):
            # Message content
            st.markdown(content)

            # Timestamp and metadata
            if time_str:
                st.markdown(
                    f'<div class="text-xs opacity-70 mt-2">{time_str}</div>',
                    unsafe_allow_html=True
                )

            # Show intent badge for parsed commands
            if role == 'assistant' and message.get('metadata', {}).get('parsed_command'):
                parsed = message['metadata']['parsed_command']
                intent = parsed.get('intent', '')
                if intent and intent != 'unknown':
                    st.markdown(
                        f'<div class="mt-2">{badge(intent.title(), variant="outline")}</div>',
                        unsafe_allow_html=True
                    )

    st.markdown('</div>', unsafe_allow_html=True)

    # Chat input with placeholder
    prompt = st.chat_input(
        "Type your message...",
        key="chat_input"
    )

    if prompt:
        # Add user message with timestamp
        conv.add_message('user', prompt)

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
            st.markdown(
                f'<div class="text-xs opacity-70 mt-2">{datetime.now().strftime("%I:%M %p")}</div>',
                unsafe_allow_html=True
            )

        # Parse command
        context = conv.get_context()
        parsed = parser.parse(prompt, context)

        # Store parsed command in session state for processing
        st.session_state.last_command = parsed

        # Generate and display response
        response = parser.get_suggested_response(parsed)

        conv.add_message('assistant', response, metadata={'parsed_command': parsed})

        with st.chat_message("assistant"):
            st.markdown(response)
            st.markdown(
                f'<div class="text-xs opacity-70 mt-2">{datetime.now().strftime("%I:%M %p")}</div>',
                unsafe_allow_html=True
            )

            # Show intent badge
            intent = parsed.get('intent', '')
            if intent and intent != 'unknown':
                st.markdown(
                    f'<div class="mt-2">{badge(intent.title(), variant="outline")}</div>',
                    unsafe_allow_html=True
                )

        # Trigger rerun to update UI
        st.rerun()

    # Chat controls in sidebar (enhanced with shadcn buttons)
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Chat Controls")

        # Message count
        msg_count = len(conv.get_messages())
        st.markdown(
            f'<p class="text-sm text-muted-foreground mb-3">{msg_count} messages in history</p>',
            unsafe_allow_html=True
        )

        # Clear chat button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear", use_container_width=True, key="clear_chat"):
                conv.clear_history()
                st.rerun()

        with col2:
            if st.button("❓ Help", use_container_width=True, key="show_help"):
                help_msg = parser._get_help_message()
                conv.add_message('user', 'help')
                conv.add_message('assistant', help_msg)
                st.rerun()

        # Quick actions section
        st.markdown("---")
        st.markdown("### Quick Actions")

        quick_actions = [
            ("📊 Forecast Spring 2026", "Forecast Spring 2026 for all courses"),
            ("⚙️ Show Settings", "What settings can I configure?"),
            ("📁 Upload Data", "How do I upload enrollment data?"),
        ]

        for label, command in quick_actions:
            if st.button(label, use_container_width=True, key=f"qa_{command}"):
                conv.add_message('user', command)
                context = conv.get_context()
                parsed = parser.parse(command, context)
                st.session_state.last_command = parsed
                response = parser.get_suggested_response(parsed)
                conv.add_message('assistant', response, metadata={'parsed_command': parsed})
                st.rerun()


def get_last_command():
    """
    Get the last parsed command from session state.

    Returns:
        Dictionary with parsed command or None
    """
    return st.session_state.get('last_command')


def clear_last_command():
    """Clear the last command from session state."""
    if 'last_command' in st.session_state:
        del st.session_state.last_command
