"""
Enrollment Forecasting Tool
Predicts future enrollment and recommends course sections using Prophet + ARIMA
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from prophet import Prophet
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Enrollment Forecaster", layout="wide")

# --- Configuration Sidebar ---
st.sidebar.header("⚙️ Settings")
section_capacity = st.sidebar.number_input("Students per Section", min_value=10, max_value=50, value=20)
buffer_percent = st.sidebar.slider("Capacity Buffer (%)", 0, 30, 10, help="Extra capacity for late adds/waitlist")
forecast_quarters = st.sidebar.selectbox("Quarters to Forecast", [1, 2, 3, 4], index=1)
model_weight_prophet = st.sidebar.slider("Prophet Weight (vs Exp. Smoothing)", 0.0, 1.0, 0.6)
include_history = st.sidebar.checkbox("Include Historical Data (from Data folder)", value=False)
include_waitlist = st.sidebar.checkbox("Include Waitlist in Demand", value=False, help="Add waitlisted students to enrollment count for 'True Demand'")
summer_ratio_default = st.sidebar.slider("Default Summer Ratio (vs Spring)", 0.0, 1.0, 0.15, help="Fallback Summer/Spring ratio if no history exists")
growth_pct = st.sidebar.slider("Target Growth %", -20, 20, 0, help="Adjust forecast by this percentage (e.g. 5 = 5% growth)")

st.title("📊 Enrollment Forecasting Tool")
st.markdown("Upload historical enrollment data to forecast future enrollment and section needs.")

# --- Data Upload ---
st.header("1. Upload Enrollment Data")

with st.expander("📋 Expected Data Format", expanded=False):
    st.markdown("""
    Your CSV/Excel should have these columns:
    - **Term**: Quarter and Year (e.g., "Fall 2025")
    - **Course**: Course identifier (e.g., FOUN 110)
    - **Enrollment**: Number of enrolled students
    
    Optional columns:
    - **Section #**: Section identifier
    - **Course Title**: Title of the course
    - **Waitlist**: Number of waitlisted students (for True Demand)
    """)
    
    sample_data = pd.DataFrame({
        'Term': ['Fall 2022', 'Winter 2023', 'Spring 2023', 'Fall 2023', 'Winter 2024', 'Spring 2024'],
        'Course': ['FOUN 110', 'FOUN 110', 'FOUN 110', 'FOUN 110', 'FOUN 110', 'FOUN 110'],
        'Enrollment': [75, 68, 72, 82, 71, 78],
        'Waitlist': [5, 2, 0, 8, 3, 1]
    })
    st.dataframe(sample_data, use_container_width=True)

uploaded_files = st.file_uploader("Upload CSV or Excel file", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)


def quarter_to_date(year, quarter):
    """Convert year and quarter to a datetime for time series modeling."""
    quarter_map = {
        'fall': 9, 'winter': 1, 'spring': 4, 'summer': 6,
        '1': 1, '2': 4, '3': 6, '4': 9
    }
    q = str(quarter).lower().strip()
    month = quarter_map.get(q, 1)
    # Winter quarter belongs to the next calendar year conceptually
    if q == 'winter':
        year = year + 1
    return datetime(int(year), month, 1)


def date_to_quarter_label(date):
    """Convert datetime back to quarter label."""
    month = date.month
    year = date.year
    if month in [1, 2, 3]:
        return f"Winter {year}"
    elif month in [4, 5]:
        return f"Spring {year}"
    elif month in [6, 7, 8]:
        return f"Summer {year}"
    else:
        return f"Fall {year}"


def forecast_prophet(df_ts, periods):
    """Run Prophet forecast."""
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    model.fit(df_ts)
    future = model.make_future_dataframe(periods=periods, freq='QS')
    forecast = model.predict(future)
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)


def forecast_ets(df_ts, periods):
    """Run Exponential Smoothing (Holt-Winters) forecast."""
    try:
        # Try full Holt-Winters (Trend + Seasonality)
        # seasonal_periods=4 for quarterly data
        model = ExponentialSmoothing(
            df_ts['y'].values, 
            seasonal_periods=4, 
            trend='add', 
            seasonal='add', 
            damped_trend=True
        )
        fitted = model.fit()
        forecast = fitted.forecast(steps=periods)
        return forecast
    except Exception:
        try:
            # Fallback 1: Simple Exponential Smoothing (Level only)
            model = ExponentialSmoothing(df_ts['y'].values, trend='add')
            fitted = model.fit()
            return fitted.forecast(steps=periods)
        except Exception:
             # Fallback 2: Naive mean
             return np.full(periods, df_ts['y'].mean())


def calculate_sections(enrollment, capacity, buffer_pct):
    """Calculate sections needed with buffer."""
    effective_capacity = capacity * (1 - buffer_pct / 100)
    return int(np.ceil(enrollment / effective_capacity))


def load_course_mapping():
    """Load course code mapping from Data/sequence_crosswalk_template.csv."""
    try:
        crosswalk_path = "Data/sequence_crosswalk_template.csv"
        df_cross = pd.read_csv(crosswalk_path)
        # Create dictionary: legacy_code -> foun_code
        # Strip whitespace just in case
        mapping = dict(zip(df_cross['legacy_code'].str.strip(), df_cross['foun_code'].str.strip()))
        return mapping
    except FileNotFoundError:
        st.warning("Crosswalk file (Data/sequence_crosswalk_template.csv) not found.")
        return {}
    except Exception as e:
        st.warning(f"Error loading crosswalk: {e}")
        return {}


def load_historical_data():
    """Load and process historical data from Data/FOUN_Historical.csv."""
    try:
        hist_path = "Data/FOUN_Historical.csv"
        df_hist = pd.read_csv(hist_path)
        
        # Process columns
        # Combine SUBJ and CRS NUMBER to create Course
        df_hist['course_code'] = df_hist['SUBJ'] + " " + df_hist['CRS NUMBER'].astype(str)
        
        # Rename Enrollment
        df_hist = df_hist.rename(columns={'ACT ENR': 'enrollment'})
        
        # Add Waitlist column (0 for historical)
        df_hist['waitlist'] = 0
        
        # Parse TERM (YYYYMM)
        # 10=Fall (prev year), 20=Winter, 30=Spring, 40=Summer
        def parse_term(term_code):
            term_str = str(term_code)
            year_part = int(term_str[:4])
            suffix = int(term_str[4:])
            
            if suffix == 10:
                return 'Fall', year_part - 1
            elif suffix == 20:
                return 'Winter', year_part
            elif suffix == 30:
                return 'Spring', year_part
            elif suffix == 40:
                return 'Summer', year_part
            return None, None

        df_hist[['quarter', 'year']] = df_hist['TERM'].apply(lambda x: pd.Series(parse_term(x)))
        
        # Apply Course Mapping
        mapping = load_course_mapping()
        if mapping:
            # Use map to replace, fillna with original to keep codes that don't need mapping
            df_hist['course_code'] = df_hist['course_code'].map(mapping).fillna(df_hist['course_code'])
        
        return df_hist[['year', 'quarter', 'course_code', 'enrollment', 'waitlist']]
        
    except FileNotFoundError:
        st.warning("Historical data file (Data/FOUN_Historical.csv) not found.")
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Error loading historical data: {e}")
        return pd.DataFrame()


def calculate_summer_ratios(df):
    """Calculate average Summer/Spring ratio for each course."""
    ratios = {}
    
    # Ensure we have necessary columns
    if 'course_code' not in df.columns or 'quarter' not in df.columns or 'year' not in df.columns:
        return ratios
        
    # Group by Course, Year, Quarter
    # We need to sum enrollment in case there are multiple rows per course/term
    df_agg = df.groupby(['course_code', 'year', 'quarter'])['enrollment'].sum().reset_index()
    
    courses = df_agg['course_code'].unique()
    
    for course in courses:
        course_df = df_agg[df_agg['course_code'] == course]
        course_ratios = []
        
        years = course_df['year'].unique()
        for year in years:
            # Find Spring and Summer for this year
            spring = course_df[(course_df['year'] == year) & (course_df['quarter'].str.lower() == 'spring')]
            summer = course_df[(course_df['year'] == year) & (course_df['quarter'].str.lower() == 'summer')]
            
            if not spring.empty and not summer.empty:
                spring_val = spring['enrollment'].values[0]
                summer_val = summer['enrollment'].values[0]
                
                if spring_val > 0:
                    course_ratios.append(summer_val / spring_val)
        
        if course_ratios:
            ratios[course] = sum(course_ratios) / len(course_ratios)
            
    return ratios


if uploaded_files or include_history:
    df = pd.DataFrame()
    
    # Load uploaded data
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
                pass # Handle gracefully later if needed
        
        # Rename columns to match internal logic
        df_uploaded = df_uploaded.rename(columns={'course': 'course_code'})
        
        # Handle Waitlist
        if 'waitlist' not in df_uploaded.columns:
            # Check for 'wait total' or similar
            wait_col = next((c for c in df_uploaded.columns if 'wait' in c and 'total' in c), None)
            if wait_col:
                df_uploaded = df_uploaded.rename(columns={wait_col: 'waitlist'})
            else:
                df_uploaded['waitlist'] = 0
        
        # Apply Course Mapping to Uploaded Data
        mapping = load_course_mapping()
        if mapping and 'course_code' in df_uploaded.columns:
             df_uploaded['course_code'] = df_uploaded['course_code'].map(mapping).fillna(df_uploaded['course_code'])
        
        # Keep only relevant columns
        cols_to_keep = ['year', 'quarter', 'course_code', 'enrollment', 'waitlist']
        df_uploaded = df_uploaded[[c for c in cols_to_keep if c in df_uploaded.columns]]
        
        df = pd.concat([df, df_uploaded], ignore_index=True)

    # Load and merge historical data
    if include_history:
        df_hist = load_historical_data()
        if not df_hist.empty:
            df = pd.concat([df, df_hist], ignore_index=True)
            st.info(f"📚 Included {len(df_hist)} historical records")

    if df.empty:
        st.warning("No data loaded. Please upload a file or enable historical data.")
        st.stop()

    # Validate required columns
    required_cols = ['year', 'quarter', 'course_code', 'enrollment']
    missing = [c for c in required_cols if c not in df.columns]
    
    if missing:
        st.error(f"Missing required columns in combined data: {missing}")
        st.stop()
    
    # Calculate True Demand if requested
    if include_waitlist:
        df['enrollment'] = df['enrollment'] + df['waitlist'].fillna(0)
        st.info("ℹ️ Using True Demand (Enrollment + Waitlist)")
    
    # Calculate Course-Specific Summer Ratios
    course_summer_ratios = calculate_summer_ratios(df)
    
    st.success(f"✅ Total records loaded: {len(df)}")
    
    # Preview data
    with st.expander("Preview Combined Data"):
        st.dataframe(df.head(20), use_container_width=True)
        
    with st.expander("☀️ Calculated Summer Ratios"):
        if course_summer_ratios:
            st.write("Based on historical data, these are the Summer/Spring ratios used:")
            st.json(course_summer_ratios)
        else:
            st.write("No historical Summer/Spring pairs found. Using default ratio.")
    
    # --- Course Selection ---
    st.header("2. Select Courses to Forecast")
    
    courses = sorted(df['course_code'].unique())
    
    col1, col2 = st.columns([1, 3])
    with col1:
        select_all = st.checkbox("Select All Courses")
    
    if select_all:
        selected_courses = courses
    else:
        selected_courses = st.multiselect("Choose courses:", courses, default=courses[:5] if len(courses) > 5 else courses)
    
    if not selected_courses:
        st.warning("Please select at least one course.")
        st.stop()
    
    # --- Run Forecasts ---
    st.header("3. Forecast Results")
    
    if st.button("🔮 Generate Forecasts", type="primary"):
        results = []
        progress = st.progress(0)
        status = st.empty()
        
        # Build Masterlist of course offerings from historical data
        course_offerings = {}
        if include_history and not df_hist.empty:
            for course in df_hist['course_code'].unique():
                quarters = df_hist[df_hist['course_code'] == course]['quarter'].unique()
                course_offerings[course] = [q.lower() for q in quarters]
        
        for i, course in enumerate(selected_courses):
            status.text(f"Forecasting {course}...")
            
            # Prepare time series for this course
            course_df = df[df['course_code'] == course].copy()
            course_df['ds'] = course_df.apply(lambda r: quarter_to_date(r['year'], r['quarter']), axis=1)
            course_df = course_df.groupby('ds')['enrollment'].sum().reset_index()
            course_df.columns = ['ds', 'y']
            course_df = course_df.sort_values('ds')
            
            if len(course_df) < 2:
                st.warning(f"⚠️ {course}: Not enough data points (need at least 2 quarters)")
                continue
            
            try:
                # Prophet forecast
                prophet_forecast = forecast_prophet(course_df, forecast_quarters)
                
                # ETS (Exponential Smoothing) forecast
                ets_forecast = forecast_ets(course_df, forecast_quarters)
                
                # Track last Spring forecast for Summer adjustment
                last_spring_forecast = 0
                
                # Determine Summer Ratio for this course
                this_summer_ratio = course_summer_ratios.get(course, summer_ratio_default)
                
                # Ensemble
                for j, (_, row) in enumerate(prophet_forecast.iterrows()):
                    prophet_pred = max(0, row['yhat'])
                    # Check if ets_forecast is a Series/DataFrame (has iloc) or numpy array
                    if hasattr(ets_forecast, 'iloc'):
                        ets_val = ets_forecast.iloc[j]
                    else:
                        ets_val = ets_forecast[j]
                        
                    ets_pred = max(0, ets_val) if j < len(ets_forecast) else prophet_pred
                    
                    # Weighted ensemble
                    ensemble_pred = (model_weight_prophet * prophet_pred + 
                                   (1 - model_weight_prophet) * ets_pred)
                    
                    quarter_label = date_to_quarter_label(row['ds'])
                    
                    # Capture Spring forecast
                    if "Spring" in quarter_label:
                        last_spring_forecast = ensemble_pred
                    
                    # Apply Summer Logic: Force to ratio of Spring
                    if "Summer" in quarter_label:
                        if last_spring_forecast > 0:
                            ensemble_pred = last_spring_forecast * this_summer_ratio
                            # Adjust bounds proportionally
                            prophet_pred = ensemble_pred # Simplify for display
                            ets_pred = ensemble_pred
                        else:
                            # Fallback if no Spring forecast available (unlikely sequence)
                            ensemble_pred = ensemble_pred * this_summer_ratio
                    
                    # Apply Masterlist Logic (Course Offerings)
                    # If we have historical data for this course, check if it's offered in this quarter
                    current_quarter_name = quarter_label.split(' ')[0].lower()
                    if course in course_offerings:
                        if current_quarter_name not in course_offerings[course]:
                            ensemble_pred = 0.0 # Force to 0 if not offered
                            prophet_pred = 0.0
                            ets_pred = 0.0
                    
                    # Apply Growth Scenario
                    growth_multiplier = 1 + (growth_pct / 100)
                    ensemble_pred = ensemble_pred * growth_multiplier
                    prophet_pred = prophet_pred * growth_multiplier
                    ets_pred = ets_pred * growth_multiplier
                    
                    lower_bound = max(0, row['yhat_lower']) * growth_multiplier
                    upper_bound = max(0, row['yhat_upper']) * growth_multiplier
                    
                    # Adjust bounds if ensemble was adjusted
                    if ensemble_pred == 0:
                        lower_bound = 0
                        upper_bound = 0
                    elif "Summer" in quarter_label:
                         lower_bound = ensemble_pred * 0.8
                         upper_bound = ensemble_pred * 1.2
                    
                    results.append({
                        'Course': course,
                        'Quarter': quarter_label,
                        'Prophet Forecast': int(round(prophet_pred)),
                        'ETS Forecast': int(round(ets_pred)),
                        'Ensemble Forecast': int(round(ensemble_pred)),
                        'Lower Bound': int(round(lower_bound)),
                        'Upper Bound': int(round(upper_bound)),
                        'Sections Needed': calculate_sections(ensemble_pred, section_capacity, buffer_percent),
                        'Min Sections': calculate_sections(lower_bound, section_capacity, buffer_percent),
                        'Max Sections': calculate_sections(upper_bound, section_capacity, buffer_percent)
                    })
                    
            except Exception as e:
                st.error(f"Error forecasting {course}: {e}")
                continue
        
        # --- Display Results ---
        if results:
            df_results = pd.DataFrame(results)
            st.success("Forecast generation complete!")
            
            # Display summary table
            st.subheader("Forecast Summary")
            st.dataframe(df_results, use_container_width=True)
            
            # Download button
            csv = df_results.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Forecasts as CSV",
                csv,
                "enrollment_forecast.csv",
                "text/csv",
                key='download-csv'
            )
            
            # Visualizations
            st.subheader("Trend Visualization")
            for course in selected_courses:
                course_data = df_results[df_results['Course'] == course]
                if not course_data.empty:
                    # Get historical data for context
                    hist_data = df[df['course_code'] == course].copy()
                    hist_data['type'] = 'Historical'
                    hist_data['quarter_label'] = hist_data.apply(lambda r: f"{date_to_quarter_label(quarter_to_date(r['year'], r['quarter']))}", axis=1)
                    
                    # Prepare forecast data for plotting
                    fore_data = course_data.copy()
                    fore_data['type'] = 'Forecast'
                    fore_data['enrollment'] = fore_data['Ensemble Forecast']
                    fore_data['quarter_label'] = fore_data['Quarter']
                    
                    # Combine
                    plot_df = pd.concat([
                        hist_data[['quarter_label', 'enrollment', 'type']],
                        fore_data[['quarter_label', 'enrollment', 'type']]
                    ])
                    
                    st.markdown(f"**{course}**")
                    st.line_chart(plot_df.set_index('quarter_label')['enrollment'])

    # --- Cohort Analysis ---
    st.header("4. Cohort Analysis (Incoming Class)")
    st.markdown("Estimate demand based on incoming student counts and major requirements.")
    
    if st.checkbox("Run Cohort Analysis"):
        try:
            # 1. Load Admission Data
            # Finding the header row for PZSAAPF file
            adm_file = "Data/PZSAAPF-SL31 - Accepted Applicants with Latest Decision.xlsx"
            # Based on inspection, data starts around row 10, headers likely at row 9 (0-indexed)
            # We'll try to find the row with 'Major' or 'Program'
            df_adm_raw = pd.read_excel(adm_file, header=None)
            header_row_idx = None
            for i, row in df_adm_raw.iterrows():
                row_str = row.astype(str).str.lower().tolist()
                if 'major' in row_str or 'program' in row_str or 'student type' in row_str: # Heuristic
                     # In the sample, row 9 had '202610 - SAV - FR', row 6 had 'Student Type'.
                     # Let's look for a row that has 'Major' or 'Concentration'
                     pass
            
            # Hardcoding based on file inspection: Row 9 (index 9) seems to be the header or close to it.
            # Actually, let's just read it and look for the column with Major names.
            # In the sample: Col 26 had 'Acting', 'Painting'.
            df_adm = pd.read_excel(adm_file, header=9) 
            
            # Identify Major column - usually named 'Major' or 'Program' or 'Concentration'
            # If not found, look for column with known majors
            major_col = None
            known_majors = ['Animation', 'Acting', 'Graphic Design', 'Illustration']
            for col in df_adm.columns:
                if df_adm[col].astype(str).apply(lambda x: any(m in x for m in known_majors if isinstance(x, str))).sum() > 5:
                    major_col = col
                    break
            
            if not major_col:
                # Fallback: try column index 26
                if len(df_adm.columns) > 26:
                    major_col = df_adm.columns[26]
            
            if major_col:
                # Filter for Freshmen if possible (Look for 'Student Type' or similar)
                # For now, we assume the file contains the relevant cohort.
                cohort_counts = df_adm[major_col].value_counts().reset_index()
                cohort_counts.columns = ['Major', 'Count']
                
                st.write(f"Found {len(cohort_counts)} majors in admission data.")
                with st.expander("Incoming Students by Major"):
                    st.dataframe(cohort_counts)
                
                # 2. Load Masterlists
                df_reqs = pd.read_excel("Data/Masterlist_FOUN_courses_by_major.xlsx")
                df_seq = pd.read_excel("Data/Masterlist_FOUN_courses_by_quarter.xlsx")
                
                # Normalize Major names for matching
                # This is tricky. Admission file might say "Animation - Storytelling", Masterlist might say "ANIMATION".
                # We'll do a fuzzy match or simple containment check.
                
                # 3. Calculate Demand
                # Heuristic:
                # Fall: FOUN 100, 110, 111
                # Winter: FOUN 112, 220
                # Spring: FOUN 230, 240, 250
                # Year 2 Fall: FOUN 113 (if Year 2)
                
                cohort_demand = []
                
                for _, row in cohort_counts.iterrows():
                    major = str(row['Major']).upper()
                    count = row['Count']
                    
                    # Find matching major in requirements
                    # Simple fuzzy match: check if first word of major matches
                    major_key = major.split(' ')[0] 
                    if '-' in major:
                        major_key = major.split('-')[0].strip()
                        
                    req_courses = df_reqs[df_reqs['program'].str.contains(major_key, case=False, na=False)]['course_code'].unique()
                    
                    for course in req_courses:
                        # Determine Quarter
                        # Check sequencing
                        seq_info = df_seq[df_seq['course_code'] == course]
                        year_level = "First Year"
                        if not seq_info.empty:
                            year_level = seq_info.iloc[0]['year']
                        
                        target_quarter = "Unknown"
                        course_num = int(course.split(' ')[1]) if len(course.split(' ')) > 1 and course.split(' ')[1].isdigit() else 0
                        
                        if year_level == "First Year":
                            if course_num in [100, 110, 111]:
                                target_quarter = "Fall 2025"
                            elif course_num in [112, 220]:
                                target_quarter = "Winter 2026"
                            elif course_num in [230, 240, 250]:
                                target_quarter = "Spring 2026"
                            else:
                                target_quarter = "Fall 2025" # Default
                        else:
                            target_quarter = "Fall 2026" # Second Year start
                        
                        cohort_demand.append({
                            'Course': course,
                            'Quarter': target_quarter,
                            'Cohort Demand': count
                        })
                
                if cohort_demand:
                    df_cohort = pd.DataFrame(cohort_demand)
                    df_cohort_agg = df_cohort.groupby(['Course', 'Quarter'])['Cohort Demand'].sum().reset_index()
                    
                    st.subheader("Projected Cohort Demand")
                    st.dataframe(df_cohort_agg, use_container_width=True)
                    
                    # Comparison with Forecast
                    # (This would require running the forecast first)
                else:
                    st.warning("No demand calculated. Check major name matching.")
            else:
                st.error("Could not identify 'Major' column in admission file.")
                
        except Exception as e:
            st.error(f"Error in cohort analysis: {e}")
            
    # --- Visualization ---
    if 'results_df' in st.session_state:
        st.header("4. Visualization")
        
        viz_course = st.selectbox("Select course to visualize:", selected_courses)
        
        if viz_course:
            # Historical data
            hist = df[df['course_code'] == viz_course].copy()
            hist['ds'] = hist.apply(lambda r: quarter_to_date(r['year'], r['quarter']), axis=1)
            hist = hist.groupby('ds')['enrollment'].sum().reset_index()
            hist['type'] = 'Historical'
            
            # Forecast data
            forecast = st.session_state['results_df'][st.session_state['results_df']['Course'] == viz_course].copy()
            
            # Create chart data
            chart_data = hist.rename(columns={'enrollment': 'Enrollment', 'ds': 'Date'})
            chart_data = chart_data[['Date', 'Enrollment']]
            
            st.line_chart(chart_data.set_index('Date'))
            
            st.caption(f"Historical enrollment for {viz_course}. Forecast: {forecast[['Quarter', 'Ensemble Forecast', 'Sections Needed']].to_string(index=False)}")

else:
    st.info("👆 Upload a file to get started")
    
    # Offer sample data download
    st.subheader("Need sample data?")
    sample = pd.DataFrame({
        'Term': ['Fall 2021', 'Winter 2022', 'Spring 2022', 'Summer 2022'] * 4,
        'Course': ['FOUN 110'] * 16,
        'Enrollment': [72, 68, 75, 45, 78, 71, 80, 48, 85, 74, 82, 52, 88, 78, 86, 55]
    })
    
    # Add more courses
    for course, base in [('FOUN 111', 55), ('FOUN 112', 90), ('FOUN 113', 35)]:
        noise = np.random.randint(-5, 10, 16)
        trend = np.arange(16) * 1.5
        enrollments = (base + noise + trend).astype(int)
        course_data = pd.DataFrame({
            'Term': ['Fall 2021', 'Winter 2022', 'Spring 2022', 'Summer 2022'] * 4,
            'Course': [course] * 16,
            'Enrollment': enrollments
        })
        sample = pd.concat([sample, course_data], ignore_index=True)
    
    csv = sample.to_csv(index=False)
    st.download_button(
        label="Download Sample Data",
        data=csv,
        file_name="sample_enrollment_data.csv",
        mime="text/csv"
    )
