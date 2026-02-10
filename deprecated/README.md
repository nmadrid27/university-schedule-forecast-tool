# Deprecated Files

This directory contains legacy Streamlit-based interfaces that have been superseded by the modern Next.js frontend.

## Why Deprecated?

As of v3.0, the primary interface for the SCAD FOUN Enrollment Forecasting Tool is the **Next.js React frontend** located in the `frontend/` directory.

**Benefits of the new frontend:**
- Modern, responsive UI built with React 19 and Tailwind CSS
- Better performance and user experience
- Component-based architecture for maintainability
- Professional design with Radix UI components
- Faster load times and interactions

## Legacy Files

- **`app_chat.py`** - Streamlit chat-based interface (deprecated)
- **`app.py`** - Streamlit form-based interface (deprecated)
- **`QUICKSTART_CHAT.md`** - Chat interface guide (superseded by frontend README)
- **`requirements_chat.txt`** - Streamlit dependencies (no longer needed)

## Migration Path

If you need to use the forecasting engine:

1. **Recommended:** Use the **Next.js frontend** at `../frontend/`
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

2. **For production automation:** Use the **CLI scripts**
   ```bash
   python3 forecast_spring26_from_sequence_guides.py --config forecast_config.json
   ```

3. **If you must run legacy code:** Set up Python environment and run manually
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install streamlit prophet statsmodels pandas numpy openpyxl
   streamlit run app_chat.py  # Or app.py
   ```

## What's New

- **Frontend:** See `../frontend/README.md` and `../frontend/src/`
- **Architecture:** See `../CLAUDE.md` (Version 3.0 section)
- **Getting Started:** See `../README.md`

## Questions?

Refer to:
- `../README.md` - Quick start guide
- `../CLAUDE.md` - Developer documentation
- `../AGENTS.md` - Production workflow

---

**Last Updated:** 2026-02-04
**Status:** Archived - use Next.js frontend instead
