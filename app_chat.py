"""
SCAD FOUN Enrollment Forecasting Tool - Chat Interface
AI-powered chatbot interface with shadcn/ui design system

This is the main entry point for the chat-based UI.
"""

import streamlit as st
import warnings
warnings.filterwarnings('ignore')

from forecast_tool.ui.chat_window import render_chat_window
from forecast_tool.ui.output_window import render_output_window
from forecast_tool.config.settings import APP_TITLE, APP_ICON, DEFAULT_LAYOUT


# Page configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=DEFAULT_LAYOUT,
    initial_sidebar_state="expanded"
)

# shadcn/ui Design System - Tailwind CSS + Custom Tokens
st.markdown("""
<style>
    /* ========================================
       shadcn/ui Design System for Streamlit
       Hybrid Approach: CDN + CSS Variables
       ======================================== */

    /* Import Google Fonts (system-ui fallback) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* CSS Variables - shadcn/ui Dark Mode */
    :root {
        /* Base Colors - Dark Theme */
        --background: 222.2 84% 4.9%;
        --foreground: 210 40% 98%;

        /* Card & Popover - Dark */
        --card: 222.2 84% 4.9%;
        --card-foreground: 210 40% 98%;
        --popover: 222.2 84% 4.9%;
        --popover-foreground: 210 40% 98%;

        /* Primary (Action color) - Brighter for dark mode */
        --primary: 210 40% 98%;
        --primary-foreground: 222.2 47.4% 11.2%;

        /* Secondary - Dark */
        --secondary: 217.2 32.6% 17.5%;
        --secondary-foreground: 210 40% 98%;

        /* Muted - Dark */
        --muted: 217.2 32.6% 17.5%;
        --muted-foreground: 215 20.2% 65.1%;

        /* Accent - Dark */
        --accent: 217.2 32.6% 17.5%;
        --accent-foreground: 210 40% 98%;

        /* Destructive - Adjusted for dark */
        --destructive: 0 62.8% 30.6%;
        --destructive-foreground: 210 40% 98%;

        /* Borders & Inputs - Dark */
        --border: 217.2 32.6% 17.5%;
        --input: 217.2 32.6% 17.5%;
        --ring: 212.7 26.8% 83.9%;

        /* Border Radius */
        --radius: 0.5rem;
    }

    /* Base Styles - Dark Mode */
    * {
        border-color: hsl(var(--border));
    }

    body {
        background-color: hsl(var(--background)) !important;
        color: hsl(var(--foreground)) !important;
    }

    .main {
        background-color: hsl(var(--background)) !important;
        color: hsl(var(--foreground)) !important;
        font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
        padding: 1.5rem;
    }

    /* Force dark mode on Streamlit container */
    [data-testid="stAppViewContainer"] {
        background-color: hsl(var(--background)) !important;
    }

    [data-testid="stHeader"] {
        background-color: hsl(var(--background)) !important;
    }

    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        color: hsl(var(--foreground));
        font-weight: 600;
        letter-spacing: -0.025em;
    }

    /* ========================================
       Streamlit Component Overrides
       ======================================== */

    /* Chat Messages */
    .stChatMessage {
        border-radius: var(--radius) !important;
        border: 1px solid hsl(var(--border)) !important;
        background: hsl(var(--card)) !important;
        color: hsl(var(--card-foreground)) !important;
        box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05) !important;
        padding: 1rem !important;
        margin-bottom: 0.75rem !important;
        transition: all 0.2s ease !important;
    }

    .stChatMessage:hover {
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1) !important;
    }

    /* User vs Assistant styling */
    .stChatMessage[data-testid*="user-message"] {
        background: hsl(var(--primary)) !important;
        color: hsl(var(--primary-foreground)) !important;
        border-color: hsl(var(--primary)) !important;
    }

    /* Chat Input */
    .stChatInputContainer {
        border-radius: var(--radius) !important;
        border: 1px solid hsl(var(--input)) !important;
        background: hsl(var(--background)) !important;
    }

    .stChatInputContainer:focus-within {
        outline: none !important;
        ring: 2px !important;
        ring-color: hsl(var(--ring)) !important;
        ring-offset: 2px !important;
        border-color: hsl(var(--ring)) !important;
    }

    /* Buttons - shadcn default variant */
    .stButton button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--radius) !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        background: hsl(var(--primary)) !important;
        color: hsl(var(--primary-foreground)) !important;
        padding: 0.5rem 1rem !important;
        height: 2.5rem !important;
        border: none !important;
        box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05) !important;
    }

    .stButton button:hover {
        background: hsl(var(--primary) / 0.9) !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important;
    }

    .stButton button:active {
        transform: scale(0.98);
    }

    /* Download Button - secondary variant */
    .stDownloadButton button {
        background: hsl(var(--secondary)) !important;
        color: hsl(var(--secondary-foreground)) !important;
        width: 100%;
    }

    .stDownloadButton button:hover {
        background: hsl(var(--secondary) / 0.8) !important;
    }

    /* Input Fields */
    .stTextInput input,
    .stNumberInput input,
    .stSelectbox select,
    .stTextArea textarea {
        border-radius: var(--radius) !important;
        border: 1px solid hsl(var(--input)) !important;
        background: hsl(var(--background)) !important;
        color: hsl(var(--foreground)) !important;
        padding: 0.5rem 0.75rem !important;
        font-size: 0.875rem !important;
        height: 2.5rem !important;
        transition: all 0.2s ease !important;
    }

    .stTextArea textarea {
        height: auto !important;
        min-height: 5rem !important;
    }

    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stSelectbox select:focus,
    .stTextArea textarea:focus {
        outline: none !important;
        ring: 2px !important;
        ring-color: hsl(var(--ring)) !important;
        ring-offset: 2px !important;
        border-color: hsl(var(--ring)) !important;
    }

    /* Sliders */
    .stSlider {
        padding: 1rem 0 !important;
    }

    /* Checkbox */
    .stCheckbox {
        padding: 0.5rem 0 !important;
    }

    .stCheckbox label {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: hsl(var(--foreground)) !important;
    }

    /* Cards / Expanders */
    div[data-testid="stExpander"] {
        border-radius: var(--radius) !important;
        border: 1px solid hsl(var(--border)) !important;
        background: hsl(var(--card)) !important;
        box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05) !important;
        margin-bottom: 1rem !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stExpander"]:hover {
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important;
    }

    div[data-testid="stExpander"] summary {
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: hsl(var(--foreground)) !important;
        padding: 1rem !important;
    }

    /* Data Tables - shadcn table styling */
    .stDataFrame {
        border-radius: var(--radius) !important;
        border: 1px solid hsl(var(--border)) !important;
        overflow: hidden !important;
        box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05) !important;
    }

    .stDataFrame table {
        width: 100% !important;
        font-size: 0.875rem !important;
    }

    .stDataFrame thead th {
        background: hsl(var(--muted)) !important;
        color: hsl(var(--muted-foreground)) !important;
        font-weight: 500 !important;
        text-align: left !important;
        padding: 0.75rem 1rem !important;
        border-bottom: 1px solid hsl(var(--border)) !important;
    }

    .stDataFrame tbody tr {
        border-bottom: 1px solid hsl(var(--border)) !important;
        transition: background 0.2s ease !important;
    }

    .stDataFrame tbody tr:last-child {
        border-bottom: none !important;
    }

    .stDataFrame tbody tr:hover {
        background: hsl(var(--muted) / 0.5) !important;
    }

    .stDataFrame tbody td {
        padding: 0.75rem 1rem !important;
        color: hsl(var(--foreground)) !important;
    }

    /* File Uploader */
    [data-testid="stFileUploader"] {
        border: 2px dashed hsl(var(--border)) !important;
        border-radius: var(--radius) !important;
        padding: 2rem !important;
        background: hsl(var(--muted) / 0.3) !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: hsl(var(--ring)) !important;
        background: hsl(var(--muted) / 0.5) !important;
    }

    /* Success/Info/Warning/Error Messages - Dark Mode */
    .stSuccess {
        background: hsl(142 76% 15%) !important;
        border-left: 4px solid hsl(142 76% 45%) !important;
        border-radius: var(--radius) !important;
        padding: 1rem !important;
        color: hsl(142 76% 85%) !important;
    }

    .stInfo {
        background: hsl(199 89% 15%) !important;
        border-left: 4px solid hsl(199 89% 48%) !important;
        border-radius: var(--radius) !important;
        padding: 1rem !important;
        color: hsl(199 89% 85%) !important;
    }

    .stWarning {
        background: hsl(48 96% 15%) !important;
        border-left: 4px solid hsl(48 96% 53%) !important;
        border-radius: var(--radius) !important;
        padding: 1rem !important;
        color: hsl(48 96% 85%) !important;
    }

    .stError {
        background: hsl(0 86% 15%) !important;
        border-left: 4px solid hsl(0 86% 60%) !important;
        border-radius: var(--radius) !important;
        padding: 1rem !important;
        color: hsl(0 86% 85%) !important;
    }

    /* Progress Bar */
    .stProgress > div > div {
        background: hsl(var(--primary)) !important;
        border-radius: var(--radius) !important;
        height: 0.5rem !important;
    }

    /* Sidebar - Dark */
    section[data-testid="stSidebar"] {
        background: hsl(var(--card)) !important;
        border-right: 1px solid hsl(var(--border)) !important;
        padding: 1.5rem 1rem !important;
    }

    section[data-testid="stSidebar"] > div {
        background-color: transparent !important;
    }

    section[data-testid="stSidebar"] h2 {
        font-size: 1.125rem !important;
        font-weight: 600 !important;
        color: hsl(var(--foreground)) !important;
        margin-bottom: 1.5rem !important;
        padding-bottom: 0.75rem !important;
        border-bottom: 1px solid hsl(var(--border)) !important;
    }

    section[data-testid="stSidebar"] label {
        color: hsl(var(--foreground)) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* Column Divider */
    [data-testid="column"] {
        padding: 0 0.75rem !important;
    }

    [data-testid="column"]:first-child {
        border-right: 1px solid hsl(var(--border));
        padding-right: 1.5rem !important;
    }

    /* Tabs (if used) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 1px solid hsl(var(--border));
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 500 !important;
        color: hsl(var(--muted-foreground)) !important;
        border-radius: var(--radius) var(--radius) 0 0;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
    }

    .stTabs [aria-selected="true"] {
        background: hsl(var(--background)) !important;
        color: hsl(var(--foreground)) !important;
        border-bottom: 2px solid hsl(var(--primary)) !important;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.875rem !important;
        font-weight: 700 !important;
        color: hsl(var(--foreground)) !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: hsl(var(--muted-foreground)) !important;
    }

    /* Scrollbar Styling */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: hsl(var(--muted));
        border-radius: var(--radius);
    }

    ::-webkit-scrollbar-thumb {
        background: hsl(var(--border));
        border-radius: var(--radius);
        border: 2px solid hsl(var(--muted));
    }

    ::-webkit-scrollbar-thumb:hover {
        background: hsl(var(--muted-foreground));
    }

    /* Footer */
    .main hr {
        border-color: hsl(var(--border)) !important;
        margin: 2rem 0 1rem 0 !important;
    }

    /* Responsive */
    @media (max-width: 768px) {
        [data-testid="column"]:first-child {
            border-right: none;
            border-bottom: 1px solid hsl(var(--border));
            padding-bottom: 1.5rem !important;
        }
    }

    /* Animations */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .stChatMessage {
        animation: slideIn 0.3s ease-out;
    }
</style>

<!-- Load Lucide Icons (shadcn's icon library) -->
<script src="https://unpkg.com/lucide@latest"></script>
<script>
    // Initialize Lucide icons when page loads
    document.addEventListener('DOMContentLoaded', () => {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    });

    // Re-initialize icons when Streamlit reruns
    const observer = new MutationObserver(() => {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
</script>
""", unsafe_allow_html=True)

# Main title
st.title(f"{APP_ICON} {APP_TITLE}")
st.markdown("**Chat Interface** — Modern design powered by shadcn/ui")

# Two-column layout
col1, col2 = st.columns([1, 2])

with col1:
    render_chat_window()

with col2:
    render_output_window()

# Footer
st.markdown("---")
st.caption("Powered by Prophet + Exponential Smoothing | SCAD Foundation Courses | shadcn/ui Design System")
