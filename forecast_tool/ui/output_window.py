"""
Output window component for the Streamlit UI.
Right panel: forecast results, visualizations, and file upload with shadcn styling.
"""

import streamlit as st
import pandas as pd
import numpy as np
from forecast_tool.chat.conversation import ConversationManager
from forecast_tool.chat.responses import format_forecast_response, format_upload_response, format_error_response
from forecast_tool.data.loaders import load_course_mapping, load_historical_data, calculate_summer_ratios
from forecast_tool.data.transformers import quarter_to_date, date_to_quarter_label
from forecast_tool.forecasting.prophet_forecast import forecast_prophet
from forecast_tool.forecasting.ets_forecast import forecast_ets
from forecast_tool.forecasting.ensemble import calculate_sections, ensemble_forecast
from forecast_tool.config.settings import *
from forecast_tool.ui.components import card, badge, button, alert


def render_output_window():
    """Render the output/results panel in the right column."""
    # Enhanced header
    st.markdown("### 📊 Results & Data")
    st.markdown(
        '<p class="text-sm text-muted-foreground mb-4">Forecast results and data management</p>',
        unsafe_allow_html=True
    )

    conv = ConversationManager()

    # Check if we have a command to process
    last_command = st.session_state.get('last_command')

    # File upload section
    render_file_upload()

    # Configuration sidebar
    render_configuration_sidebar()

    # Process command if present
    if last_command and last_command['intent'] == 'forecast':
        render_forecast_output(last_command)
    elif conv.has_forecast():
        # Display existing forecast
        display_saved_forecast()
    else:
        # Show placeholder
        st.info("Upload data and ask me to generate a forecast in the chat window.")


def render_file_upload():
    """Render file upload interface."""
    with st.expander("📁 Upload Enrollment Data", expanded=False):
        st.markdown("""
        Upload CSV or Excel file with columns:
        - **Term**: Quarter and Year (e.g., "Fall 2025")
        - **Course**: Course code (e.g., "FOUN 110")
        - **Enrollment**: Number of enrolled students
        - **Waitlist** (optional): Waitlisted students
        """)

        uploaded_files = st.file_uploader(
            "Choose file(s)",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key='file_uploader'
        )

        include_history = st.checkbox(
            "Include Historical Data (from Data folder)",
            value=False,
            key='include_history'
        )

        if uploaded_files or include_history:
            process_uploaded_data(uploaded_files, include_history)


def process_uploaded_data(uploaded_files, include_history):
    """Process uploaded files and store in session state."""
    conv = ConversationManager()
    df = pd.DataFrame()

    # Load uploaded files
    if uploaded_files:
        dfs = []
        for file in uploaded_files:
            if file.name.endswith('.csv'):
                dfs.append(pd.read_csv(file))
            else:
                dfs.append(pd.read_excel(file))

        df_uploaded = pd.concat(dfs, ignore_index=True)

        # Normalize column names
        df_uploaded.columns = df_uploaded.columns.str.lower().str.strip()

        # Parse Term into Quarter and Year if needed
        if 'term' in df_uploaded.columns and 'quarter' not in df_uploaded.columns:
            try:
                df_uploaded[['quarter', 'year']] = df_uploaded['term'].str.split(' ', expand=True)
                df_uploaded['year'] = df_uploaded['year'].astype(int)
            except Exception:
                pass

        # Rename columns
        df_uploaded = df_uploaded.rename(columns={'course': 'course_code'})

        # Handle Waitlist
        if 'waitlist' not in df_uploaded.columns:
            wait_col = next((c for c in df_uploaded.columns if 'wait' in c and 'total' in c), None)
            if wait_col:
                df_uploaded = df_uploaded.rename(columns={wait_col: 'waitlist'})
            else:
                df_uploaded['waitlist'] = 0

        # Apply course mapping
        mapping = load_course_mapping()
        if mapping and 'course_code' in df_uploaded.columns:
            df_uploaded['course_code'] = df_uploaded['course_code'].map(mapping).fillna(df_uploaded['course_code'])

        # Keep relevant columns
        cols_to_keep = ['year', 'quarter', 'course_code', 'enrollment', 'waitlist']
        df_uploaded = df_uploaded[[c for c in cols_to_keep if c in df_uploaded.columns]]

        df = pd.concat([df, df_uploaded], ignore_index=True)

    # Load historical data
    if include_history:
        df_hist = load_historical_data()
        if not df_hist.empty:
            df = pd.concat([df, df_hist], ignore_index=True)
            st.info(f"📚 Included {len(df_hist)} historical records")

    if not df.empty:
        # Store in session state
        conv.update_context('enrollment_data', df)
        conv.update_context('uploaded_files', True)

        # Calculate summer ratios
        summer_ratios = calculate_summer_ratios(df)
        conv.update_context('summer_ratios', summer_ratios)

        st.success(f"✅ Loaded {len(df)} records from {df['course_code'].nunique()} courses")

        # Show preview
        with st.expander("Preview Data"):
            st.dataframe(df.head(20), use_container_width=True)


def render_configuration_sidebar():
    """Render configuration options in sidebar."""
    with st.sidebar:
        st.header("⚙️ Forecast Settings")

        capacity = st.number_input(
            "Students per Section",
            min_value=10,
            max_value=50,
            value=DEFAULT_SECTION_CAPACITY,
            key='capacity'
        )

        buffer = st.slider(
            "Capacity Buffer (%)",
            0, 30, DEFAULT_BUFFER_PERCENT,
            help="Extra capacity for late adds/waitlist",
            key='buffer'
        )

        quarters = st.selectbox(
            "Quarters to Forecast",
            [1, 2, 3, 4],
            index=1,
            key='quarters'
        )

        prophet_weight = st.slider(
            "Prophet Weight",
            0.0, 1.0, DEFAULT_PROPHET_WEIGHT,
            help="Weight for Prophet vs Exponential Smoothing",
            key='prophet_weight'
        )

        include_waitlist = st.checkbox(
            "Include Waitlist in Demand",
            value=False,
            help="Add waitlisted students to enrollment count",
            key='include_waitlist'
        )

        growth_pct = st.slider(
            "Target Growth %",
            -20, 20, DEFAULT_GROWTH_PERCENT,
            help="Adjust forecast by this percentage",
            key='growth'
        )

        # Store settings in session state
        settings = {
            'capacity': capacity,
            'buffer': buffer,
            'quarters': quarters,
            'prophet_weight': prophet_weight,
            'include_waitlist': include_waitlist,
            'growth_pct': growth_pct,
        }

        conv = ConversationManager()
        conv.update_context('settings', settings)


def render_forecast_output(command):
    """Generate and display forecast based on command."""
    conv = ConversationManager()

    # Get enrollment data
    df = conv.get_context('enrollment_data')
    if df is None or df.empty:
        st.error("No enrollment data loaded. Please upload data first.")
        return

    # Get settings
    settings = conv.get_context('settings') or {}
    capacity = settings.get('capacity', DEFAULT_SECTION_CAPACITY)
    buffer = settings.get('buffer', DEFAULT_BUFFER_PERCENT)
    quarters = settings.get('quarters', DEFAULT_FORECAST_QUARTERS)
    prophet_weight = settings.get('prophet_weight', DEFAULT_PROPHET_WEIGHT)
    include_waitlist = settings.get('include_waitlist', False)
    growth_pct = settings.get('growth_pct', DEFAULT_GROWTH_PERCENT)

    # Get summer ratios
    summer_ratios = conv.get_context('summer_ratios') or {}

    # Determine courses to forecast
    params = command.get('parameters', {})
    if params.get('all_courses'):
        selected_courses = sorted(df['course_code'].unique())
    elif params.get('courses'):
        selected_courses = params['courses']
    else:
        # Default to first 5 courses
        selected_courses = sorted(df['course_code'].unique())[:5]

    # Apply waitlist if requested
    if include_waitlist and 'waitlist' in df.columns:
        df['enrollment'] = df['enrollment'] + df['waitlist'].fillna(0)

    # Generate forecasts
    results = []
    progress = st.progress(0)
    status = st.empty()

    for i, course in enumerate(selected_courses):
        status.text(f"Forecasting {course}...")

        # Prepare time series
        course_df = df[df['course_code'] == course].copy()
        course_df['ds'] = course_df.apply(lambda r: quarter_to_date(r['year'], r['quarter']), axis=1)
        course_df = course_df.groupby('ds')['enrollment'].sum().reset_index()
        course_df.columns = ['ds', 'y']
        course_df = course_df.sort_values('ds')

        if len(course_df) < 2:
            st.warning(f"⚠️ {course}: Not enough data points")
            continue

        try:
            # Run models
            prophet_fc = forecast_prophet(course_df, quarters)
            ets_fc = forecast_ets(course_df, quarters)

            # Get summer ratio for this course
            summer_ratio = summer_ratios.get(course, DEFAULT_SUMMER_RATIO)
            last_spring_forecast = 0

            # Generate ensemble predictions
            for j, (_, row) in enumerate(prophet_fc.iterrows()):
                prophet_pred = max(0, row['yhat'])

                if hasattr(ets_fc, 'iloc'):
                    ets_val = ets_fc.iloc[j]
                else:
                    ets_val = ets_fc[j]

                ets_pred = max(0, ets_val) if j < len(ets_fc) else prophet_pred

                # Ensemble
                ensemble_pred = ensemble_forecast(prophet_pred, ets_pred, prophet_weight)

                quarter_label = date_to_quarter_label(row['ds'])

                # Track Spring for Summer adjustment
                if "Spring" in quarter_label:
                    last_spring_forecast = ensemble_pred

                # Apply Summer logic
                if "Summer" in quarter_label and last_spring_forecast > 0:
                    ensemble_pred = last_spring_forecast * summer_ratio

                # Apply growth
                growth_multiplier = 1 + (growth_pct / 100)
                ensemble_pred *= growth_multiplier
                prophet_pred *= growth_multiplier
                ets_pred *= growth_multiplier

                lower_bound = max(0, row['yhat_lower']) * growth_multiplier
                upper_bound = max(0, row['yhat_upper']) * growth_multiplier

                results.append({
                    'Course': course,
                    'Quarter': quarter_label,
                    'Prophet Forecast': int(round(prophet_pred)),
                    'ETS Forecast': int(round(ets_pred)),
                    'Ensemble Forecast': int(round(ensemble_pred)),
                    'Lower Bound': int(round(lower_bound)),
                    'Upper Bound': int(round(upper_bound)),
                    'Sections Needed': calculate_sections(ensemble_pred, capacity, buffer),
                    'Min Sections': calculate_sections(lower_bound, capacity, buffer),
                    'Max Sections': calculate_sections(upper_bound, capacity, buffer)
                })

        except Exception as e:
            st.error(f"Error forecasting {course}: {e}")
            continue

        progress.progress((i + 1) / len(selected_courses))

    progress.empty()
    status.empty()

    # Display results
    if results:
        df_results = pd.DataFrame(results)

        # Store in session state
        conv.update_context('current_forecast', df_results)

        # Display
        st.success("Forecast generation complete!")
        st.subheader("Forecast Summary")
        st.dataframe(df_results, use_container_width=True)

        # Download button
        csv = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Forecast CSV",
            csv,
            "enrollment_forecast.csv",
            "text/csv",
            key='download-csv'
        )

        # Visualizations
        render_visualizations(df_results, df, selected_courses)

        # Update conversation
        response = format_forecast_response({
            'num_courses': len(selected_courses),
            'term': params.get('term', 'selected terms')
        })
        conv.add_message('assistant', response)


def display_saved_forecast():
    """Display previously generated forecast from session state."""
    conv = ConversationManager()
    df_results = conv.get_context('current_forecast')

    if df_results is not None and not df_results.empty:
        st.subheader("Current Forecast")
        st.dataframe(df_results, use_container_width=True)

        csv = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Forecast CSV",
            csv,
            "enrollment_forecast.csv",
            "text/csv",
            key='download-saved-csv'
        )


def render_visualizations(df_results, df_historical, selected_courses):
    """Render trend visualizations."""
    st.subheader("Trend Visualization")

    for course in selected_courses:
        course_forecast = df_results[df_results['Course'] == course]

        if not course_forecast.empty:
            st.markdown(f"**{course}**")

            # Prepare chart data
            # Historical
            hist = df_historical[df_historical['course_code'] == course].copy()
            if not hist.empty:
                hist['ds'] = hist.apply(lambda r: quarter_to_date(r['year'], r['quarter']), axis=1)
                hist = hist.groupby('ds')['enrollment'].sum().reset_index()
                hist['quarter_label'] = hist['ds'].apply(date_to_quarter_label)
                hist['type'] = 'Historical'

                # Forecast
                forecast = course_forecast.copy()
                forecast['enrollment'] = forecast['Ensemble Forecast']
                forecast['quarter_label'] = forecast['Quarter']
                forecast['type'] = 'Forecast'

                # Combine
                plot_df = pd.concat([
                    hist[['quarter_label', 'enrollment']],
                    forecast[['quarter_label', 'enrollment']]
                ])

                st.line_chart(plot_df.set_index('quarter_label')['enrollment'])
