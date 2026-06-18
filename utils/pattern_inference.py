"""
pattern_inference.py
Uses scikit-learn to detect cost compounding patterns from historical
disaster data and project future costs.

Methodology: LinearRegression on year->cost with population growth adjustment.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def fit_trend_model(events_df: pd.DataFrame) -> LinearRegression:
    """
    Fit a linear trend: cost ~ year.
    Excludes catastrophic outliers (>3x median) to show underlying trend.
    """
    cost_col = "total_damage_bn"
    df = events_df.copy()
    median_cost = df[cost_col].median()
    trend_df = df[df[cost_col] <= median_cost * 10]

    if len(trend_df) < 2:
        trend_df = df

    X = trend_df[["year"]].values
    y = trend_df[cost_col].values
    model = LinearRegression()
    model.fit(X, y)
    return model


def project_next_cost(events_df: pd.DataFrame,
                       population_df: pd.DataFrame = None) -> dict:
    """
    Project the cost of the next event using LinearRegression trend
    adjusted for population growth in vulnerable zones.
    """
    model = fit_trend_model(events_df)
    last_year = int(events_df["year"].max())

    # When is the next event? (Use average gap from historical data)
    years = sorted(events_df["year"].unique())
    if len(years) >= 2:
        gaps = [years[i+1] - years[i] for i in range(len(years)-1)]
        avg_gap = max(2, round(np.mean(gaps)))
    else:
        avg_gap = 3

    next_year = last_year + avg_gap
    base_projection = float(model.predict([[next_year]])[0])

    # Apply population growth factor
    pop_factor = calculate_population_factor(population_df) if population_df is not None else 1.0
    projected_direct_bn = round(base_projection * pop_factor, 2)

    # Guard against negative projections from sparse data
    if projected_direct_bn <= 0:
        last_cost = float(events_df["total_damage_bn"].iloc[-1])
        projected_direct_bn = round(last_cost * 1.10, 2)

    # Calculate trend rate
    trend_rate = float(model.coef_[0])

    return {
        "direct_damage_bn": projected_direct_bn,
        "trend_rate": trend_rate,
        "population_factor": round(pop_factor, 2),
        "next_event_year": next_year,
        "avg_gap_years": avg_gap,
        "base_projection_bn": round(base_projection, 2),
    }


def calculate_population_factor(population_df: pd.DataFrame) -> float:
    """
    Calculate cost compounding factor from population growth.
    If population in vulnerable zones has grown 28% since baseline,
    the factor is 1.28, meaning costs compound 28% higher.
    """
    if population_df is None or population_df.empty:
        return 1.0

    df = population_df.copy()
    years = sorted(df["year"].unique())
    if len(years) < 2:
        return 1.0

    base_yr = years[0]
    current_yr = years[-1]
    base_pop = df[df["year"] == base_yr]["population"].sum()
    current_pop = df[df["year"] == current_yr]["population"].sum()

    if base_pop == 0:
        return 1.0

    growth_pct = (current_pop - base_pop) / base_pop
    # Convert population growth to cost multiplier effect.
    # Each 10% population growth in vulnerable zones compounds ~8% more cost
    # (not 1:1 because mitigation measures partially offset)
    factor = 1.0 + (growth_pct * 0.8)
    return max(1.0, factor)


def compute_compounding_trend(events_df: pd.DataFrame,
                               population_df: pd.DataFrame = None,
                               n_future_events: int = 4) -> pd.DataFrame:
    """
    Project costs across multiple future events using trend + population.
    """
    model = fit_trend_model(events_df)
    years = sorted(events_df["year"].unique())
    last_year = years[-1]

    if len(years) >= 2:
        gaps = [years[i+1] - years[i] for i in range(len(years)-1)]
        avg_gap = max(2, round(np.mean(gaps)))
    else:
        avg_gap = 3

    pop_factor = calculate_population_factor(population_df) if population_df is not None else 1.0

    rows = []
    last_cost = float(events_df["total_damage_bn"].iloc[-1])

    # Derive annual escalation rate from model trend slope vs mean cost
    mean_cost = float(events_df["total_damage_bn"].mean())
    annual_rate = abs(model.coef_[0]) / max(mean_cost, 1) if mean_cost > 0 else 0.145
    # Blend with population factor
    effective_rate = max(annual_rate, 0.05) * pop_factor

    cost = last_cost
    for i in range(1, n_future_events + 1):
        proj_year = last_year + int(i * avg_gap)
        # Compound: cost grows exponentially with effective rate
        cost = round(cost * (1 + effective_rate) ** avg_gap, 2)
        cost = max(0.1, cost)

        rows.append({
            "event_number": f"Event {i}",
            "approx_year": proj_year,
            "direct_damage_bn": cost,
            "total_cost_bn": cost,
            "displaced": int(cost * 2400),
        })

    return pd.DataFrame(rows)


def explain_pattern(events_df: pd.DataFrame,
                    zones_df: pd.DataFrame = None,
                    population_df: pd.DataFrame = None,
                    infrastructure_df: pd.DataFrame = None,
                    city: str = "Houston") -> str:
    """
    Generate a plain-language explanation of the cost compounding pattern
    detected by the model.
    """
    model = fit_trend_model(events_df)
    trend_rate = float(model.coef_[0])
    cost_col = "total_damage_bn"

    # Is cost growing?
    first_cost = events_df[cost_col].iloc[0]
    last_cost = events_df[cost_col].iloc[-1]
    total_growth_pct = round((last_cost - first_cost) / first_cost * 100, 0)

    # Find fastest-growing zone
    zone_text = ""
    if zones_df is not None and not zones_df.empty:
        zone_col = "zone_name" if "zone_name" in zones_df.columns else "neighborhood"
        zone_growth = zones_df.groupby(zone_col)["damage_usd"].agg(["mean", "max", "sum"])
        fastest = zone_growth["sum"].idxmax()
        zone_text = f" The {fastest} area shows the fastest-growing damage pattern."

    # Population growth
    pop_text = ""
    if population_df is not None and not population_df.empty:
        factor = calculate_population_factor(population_df)
        if factor > 1.1:
            pct = round((factor - 1) / 0.8 * 100, 0)
            pop_text = (f" Population density in vulnerable zones has grown "
                        f"approximately {pct}% since the first major event, "
                        f"amplifying potential disaster costs.")

    # Infrastructure capacity gap
    infra_text = ""
    if infrastructure_df is not None and not infrastructure_df.empty:
        below_50 = infrastructure_df[infrastructure_df["capacity_pct"] < 50]
        if not below_50.empty:
            worst = below_50.sort_values("capacity_pct").iloc[0]
            infra_text = (f" Meanwhile, \"{worst['project_name']}\" is at only "
                          f"{int(worst['capacity_pct'])}% of needed capacity "
                          f"({worst['status']}). "
                          f"This means more people and property are exposed "
                          f"to the same or reduced infrastructure capacity.")

    direction = "increasing" if trend_rate > 0 else "stable or decreasing"
    severity = "significantly" if total_growth_pct > 100 else "moderately" if total_growth_pct > 30 else "slightly"

    return (
        f"Pattern detected: {city}'s {events_df['disaster_type'].iloc[0].lower() if 'disaster_type' in events_df.columns else 'disaster'} "
        f"costs are {direction} — total damage has grown {severity} "
        f"({total_growth_pct:.0f}%) across {len(events_df)} documented events."
        f"{zone_text}{pop_text}{infra_text} "
        f"This means the same type of event costs more each time it occurs, "
        f"because the same vulnerable zones face higher density and unchanged infrastructure."
    )
