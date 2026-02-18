"""
Core Prophet-based enrollment forecasting for university scheduling.
"""

import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional

from prophet import Prophet

from prophet_forecast.config import (
    DEFAULT_SECTION_CAPACITY,
    DEFAULT_BUFFER_PERCENT,
    PROPHET_CONFIG,
    DEFAULT_SUMMER_RATIO,
)
from prophet_forecast.data_loader import date_to_quarter_label, aggregate_enrollment


warnings.filterwarnings("ignore")


class UniversityForecaster:
    """
    Prophet-based enrollment forecaster for university course scheduling.
    
    Trains separate Prophet models for each course (and optionally campus)
    to generate enrollment forecasts and section recommendations.
    
    Attributes:
        section_capacity: Number of students per section
        buffer_percent: Extra capacity buffer for section planning
        by_campus: Whether to create separate models per campus
        models: Dictionary of trained Prophet models
    """
    
    def __init__(
        self,
        section_capacity: int = DEFAULT_SECTION_CAPACITY,
        buffer_percent: float = DEFAULT_BUFFER_PERCENT,
        by_campus: bool = False,
        summer_ratio: float = DEFAULT_SUMMER_RATIO,
    ):
        """
        Initialize the forecaster.
        
        Args:
            section_capacity: Students per section (default: 20)
            buffer_percent: Buffer percentage for sections (default: 10)
            by_campus: Train separate models per campus (default: False)
            summer_ratio: Default Summer/Spring enrollment ratio (default: 0.15)
        """
        self.section_capacity = section_capacity
        self.buffer_percent = buffer_percent
        self.by_campus = by_campus
        self.summer_ratio = summer_ratio
        
        self.models: dict[str, Prophet] = {}
        self.training_data: Optional[pd.DataFrame] = None
        self.summer_ratios: dict[str, float] = {}
        self._last_spring_forecasts: dict[str, float] = {}
    
    def _create_prophet_model(self) -> Prophet:
        """Create a new Prophet model with configured settings."""
        return Prophet(
            yearly_seasonality=PROPHET_CONFIG["yearly_seasonality"],
            weekly_seasonality=PROPHET_CONFIG["weekly_seasonality"],
            daily_seasonality=PROPHET_CONFIG["daily_seasonality"],
            seasonality_mode=PROPHET_CONFIG["seasonality_mode"],
        )
    
    def _calculate_summer_ratios(self, df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate historical Summer/Spring enrollment ratios per course.
        
        Args:
            df: Aggregated enrollment data
            
        Returns:
            Dictionary mapping course keys to Summer/Spring ratios
        """
        ratios = {}
        
        if self.by_campus:
            group_key = lambda r: f"{r['course_code']}|{r['campus']}"
        else:
            group_key = lambda r: r["course_code"]
        
        # Group data by course (and campus)
        for key in df.apply(group_key, axis=1).unique():
            if self.by_campus:
                course, campus = key.split("|")
                course_df = df[(df["course_code"] == course) & (df["campus"] == campus)]
            else:
                course_df = df[df["course_code"] == key]
            
            course_ratios = []
            years = course_df["year"].unique()
            
            for year in years:
                spring = course_df[(course_df["year"] == year) & (course_df["quarter"].str.lower() == "spring")]
                summer = course_df[(course_df["year"] == year) & (course_df["quarter"].str.lower() == "summer")]
                
                if not spring.empty and not summer.empty:
                    spring_val = spring["enrollment"].sum()
                    summer_val = summer["enrollment"].sum()
                    
                    if spring_val > 0:
                        course_ratios.append(summer_val / spring_val)
            
            if course_ratios:
                ratios[key] = sum(course_ratios) / len(course_ratios)
        
        return ratios
    
    def fit(self, df: pd.DataFrame) -> "UniversityForecaster":
        """
        Train Prophet models on historical enrollment data.
        
        Args:
            df: DataFrame with columns: year, quarter, course_code, campus, enrollment, ds
            
        Returns:
            self (for method chaining)
        """
        # Aggregate the data
        agg_df = aggregate_enrollment(df, by_campus=self.by_campus)
        self.training_data = agg_df
        
        # Calculate summer ratios
        self.summer_ratios = self._calculate_summer_ratios(agg_df)
        
        # Train a model for each course (and campus if by_campus=True)
        if self.by_campus:
            groups = agg_df.groupby(["course_code", "campus"])
        else:
            groups = agg_df.groupby("course_code")
        
        for group_key, group_df in groups:
            if self.by_campus:
                course, campus = group_key
                model_key = f"{course}|{campus}"
            else:
                model_key = group_key
            
            # Prepare data for Prophet (requires 'ds' and 'y' columns)
            prophet_df = group_df[["ds", "enrollment"]].copy()
            prophet_df.columns = ["ds", "y"]
            prophet_df = prophet_df.groupby("ds")["y"].sum().reset_index()
            prophet_df = prophet_df.sort_values("ds")
            
            # Need at least 2 data points for Prophet
            if len(prophet_df) < 2:
                continue
            
            # Train the model
            model = self._create_prophet_model()
            model.fit(prophet_df)
            self.models[model_key] = model
        
        return self
    
    def predict(
        self,
        periods: int = 4,
        growth_percent: float = 0.0,
    ) -> pd.DataFrame:
        """
        Generate enrollment forecasts for future quarters.
        
        Args:
            periods: Number of quarters to forecast (default: 4)
            growth_percent: Adjustment factor for growth scenarios (default: 0)
            
        Returns:
            DataFrame with forecasts and section recommendations
        """
        if not self.models:
            raise ValueError("No models trained. Call fit() first.")
        
        results = []
        growth_multiplier = 1 + (growth_percent / 100)
        
        for model_key, model in self.models.items():
            # Generate future dates
            future = model.make_future_dataframe(periods=periods, freq="QS")
            forecast = model.predict(future)
            
            # Get only future predictions
            forecast_future = forecast.tail(periods).copy()
            
            # Parse model key
            if self.by_campus and "|" in model_key:
                course, campus = model_key.split("|")
            else:
                course = model_key
                campus = "ALL"
            
            # Get summer ratio for this course
            summer_ratio = self.summer_ratios.get(model_key, self.summer_ratio)
            
            # Track last Spring forecast for Summer adjustment
            last_spring_forecast = 0
            
            for _, row in forecast_future.iterrows():
                quarter_label = date_to_quarter_label(row["ds"])
                
                # Base forecast
                base_forecast = max(0, row["yhat"])
                lower = max(0, row["yhat_lower"])
                upper = max(0, row["yhat_upper"])
                
                # Track Spring for Summer adjustment
                if "Spring" in quarter_label:
                    last_spring_forecast = base_forecast
                
                # Apply Summer logic
                if "Summer" in quarter_label and last_spring_forecast > 0:
                    base_forecast = last_spring_forecast * summer_ratio
                    lower = base_forecast * 0.8
                    upper = base_forecast * 1.2
                
                # Apply growth multiplier
                forecast_val = base_forecast * growth_multiplier
                lower = lower * growth_multiplier
                upper = upper * growth_multiplier
                
                # Calculate sections
                sections = self._calculate_sections(forecast_val)
                
                results.append({
                    "course": course,
                    "campus": campus,
                    "quarter": quarter_label,
                    "forecast": int(round(forecast_val)),
                    "lower_bound": int(round(lower)),
                    "upper_bound": int(round(upper)),
                    "sections": sections,
                })
        
        return pd.DataFrame(results)
    
    def _calculate_sections(self, enrollment: float) -> int:
        """
        Calculate the number of sections needed.
        
        Args:
            enrollment: Forecasted enrollment
            
        Returns:
            Number of sections (integer)
        """
        if enrollment <= 0:
            return 0
        
        effective_capacity = self.section_capacity * (1 - self.buffer_percent / 100)
        return int(np.ceil(enrollment / effective_capacity))
    
    def get_summary(self) -> pd.DataFrame:
        """
        Get a summary of trained models.
        
        Returns:
            DataFrame with model keys and data point counts
        """
        summary = []
        for key, model in self.models.items():
            if self.by_campus and "|" in key:
                course, campus = key.split("|")
            else:
                course = key
                campus = "ALL"
            
            # Count training data points
            n_points = len(model.history) if hasattr(model, "history") else 0
            
            summary.append({
                "course": course,
                "campus": campus,
                "training_points": n_points,
                "summer_ratio": self.summer_ratios.get(key, self.summer_ratio),
            })
        
        return pd.DataFrame(summary)
