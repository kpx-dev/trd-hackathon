"""Chart creation utilities for racing data visualization."""

from typing import Dict, Optional

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from loguru import logger


def create_lap_time_chart(df: pd.DataFrame, title: str = "Lap Times") -> go.Figure:
    """Create an interactive lap time chart.

    Args:
        df: Lap timing DataFrame
        title: Chart title

    Returns:
        Plotly figure object
    """
    logger.info(f"Creating lap time chart: {title}")

    fig = go.Figure()

    if df.empty:
        logger.warning("DataFrame is empty, creating placeholder chart")
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    else:
        # Check if we have the analysis format with LAP_TIME column
        if 'LAP_TIME' in df.columns:
            # Convert LAP_TIME from M:SS.mmm format to seconds for plotting
            lap_times_seconds = []
            lap_numbers = []
            car_identifiers = []

            # Use NUMBER column (car number) if available, otherwise fall back to DRIVER_NUMBER
            id_column = 'NUMBER' if 'NUMBER' in df.columns else 'DRIVER_NUMBER'
            id_label = 'Car' if id_column == 'NUMBER' else 'Driver'

            for _, row in df.iterrows():
                try:
                    lap_time_str = str(row['LAP_TIME']).strip()
                    if ':' in lap_time_str and lap_time_str != 'nan':
                        parts = lap_time_str.split(':')
                        if len(parts) == 2:
                            minutes = int(parts[0])
                            seconds = float(parts[1])
                            total_seconds = minutes * 60 + seconds

                            lap_times_seconds.append(total_seconds)
                            lap_numbers.append(row['LAP_NUMBER'])
                            car_identifiers.append(row[id_column])
                except (ValueError, IndexError):
                    continue

            if lap_times_seconds:
                # Create separate traces for each car/driver
                unique_cars = sorted(set(car_identifiers))
                colors = px.colors.qualitative.Set1

                for i, car_id in enumerate(unique_cars):
                    car_mask = [cid == car_id for cid in car_identifiers]
                    car_laps = [ln for ln, mask in zip(lap_numbers, car_mask) if mask]
                    car_times = [lt for lt, mask in zip(lap_times_seconds, car_mask) if mask]

                    if car_times:  # Only add trace if car has lap times
                        hovertemplate = f'{id_label} #{car_id}: %{{y:.3f}}s<extra></extra>'

                        fig.add_trace(go.Scatter(
                            x=car_laps,
                            y=car_times,
                            mode='lines+markers',
                            name=f'{id_label} {car_id}',
                            line=dict(color=colors[i % len(colors)]),
                            marker=dict(size=8),  # Larger markers for easier hovering
                            hovertemplate=hovertemplate
                        ))

                # Add fastest lap annotation
                if lap_times_seconds:
                    fastest_time = min(lap_times_seconds)
                    fastest_idx = lap_times_seconds.index(fastest_time)
                    fastest_lap = lap_numbers[fastest_idx]
                    fastest_car = car_identifiers[fastest_idx]

                    fig.add_annotation(
                        x=fastest_lap,
                        y=fastest_time,
                        text=f"Fastest: {fastest_time:.3f}s<br>{id_label} {fastest_car}",
                        showarrow=True,
                        arrowhead=2,
                        bgcolor="rgba(255,255,0,0.8)",
                        bordercolor="orange",
                        borderwidth=2
                    )
            else:
                fig.add_annotation(
                    text="No valid lap times found",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
        else:
            # Fallback for other data formats
            fig.add_trace(go.Scatter(
                x=list(range(len(df))),
                y=[0] * len(df),
                mode='lines+markers',
                name='Data Points',
            ))

    fig.update_layout(
        title=title,
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        template="plotly_white",
        hovermode="x unified",  # Show all cars at the same lap
        showlegend=True,
        height=600,
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="monospace",
            align="left"
        )
    )

    return fig


def create_sector_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Create sector time comparison chart.

    Args:
        df: Sector timing DataFrame

    Returns:
        Plotly figure object
    """
    logger.info("Creating sector comparison chart")

    fig = go.Figure()

    # Placeholder implementation
    sectors = ["Sector 1", "Sector 2", "Sector 3"]
    for sector in sectors:
        fig.add_trace(go.Bar(
            x=list(range(len(df))) if not df.empty else [],
            y=[0] * len(df) if not df.empty else [],
            name=sector,
        ))

    fig.update_layout(
        title="Sector Time Comparison",
        xaxis_title="Lap Number",
        yaxis_title="Sector Time (seconds)",
        template="plotly_white",
    )

    return fig


def create_weather_correlation_chart(
    lap_df: pd.DataFrame,
    weather_df: pd.DataFrame,
) -> go.Figure:
    """Create weather correlation visualization.

    Args:
        lap_df: Lap timing DataFrame
        weather_df: Weather data DataFrame

    Returns:
        Plotly figure object
    """
    logger.info("Creating weather correlation chart")

    fig = go.Figure()

    # Placeholder implementation
    fig.add_trace(go.Scatter(
        x=[0, 1, 2] if not weather_df.empty else [],
        y=[0, 1, 2] if not lap_df.empty else [],
        mode='markers',
        name='Lap Time vs Temperature',
    ))

    fig.update_layout(
        title="Weather Impact on Lap Times",
        xaxis_title="Temperature (°C)",
        yaxis_title="Lap Time (seconds)",
        template="plotly_white",
    )

    return fig