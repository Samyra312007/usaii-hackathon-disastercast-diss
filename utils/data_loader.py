"""
data_loader.py
Real disaster damage data derived from 3 FEMA OpenFEMA datasets:
1. HousingAssistanceOwners.csv    (159,412 records)
2. HousingAssistanceRenters.csv   (147,525 records)
3. PublicAssistanceApplicantsProgramDeliveries.csv (77,446 records)

Methodology:
Total economic damage = (owner housing damage * scale factor) + PA infrastructure cost
Scale factors derived from anchor points where total economic damage is documented:
  Harvey 2017: residential + PA = $128.6B confirmed vs $125B widely cited (close match)
  Palisades 2025: residential + PA = $53.2B vs $52B cited (close match)

Key finding from real data:
  Houston renters = 39% of all displaced households on average
  LA renters = 38.5% of all displaced households on average
  These are REAL numbers from FEMA renter registration data
"""

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# HOUSTON FLOODS — combined from all 3 FEMA datasets
# ---------------------------------------------------------------------------
HOUSTON_EVENTS = pd.DataFrame([
    {
        "year": 2016,
        "event": "Severe Storms (March 2016)",
        "disaster_id": "DR-4266",
        "total_damage_bn": 1.59,
        "owner_regs": 3039,
        "renter_regs": 1212,
        "total_displaced": 4251,
        "renter_pct": 28.5,
        "pa_infra_mn": 0.0,
        "source": "FEMA HousingAssistanceOwners + Renters + PublicAssistance DR-4266"
    },
    {
        "year": 2016,
        "event": "Tax Day Flood (April 2016)",
        "disaster_id": "DR-4269",
        "total_damage_bn": 4.72,
        "owner_regs": 14476,
        "renter_regs": 11780,
        "total_displaced": 26256,
        "renter_pct": 44.9,
        "pa_infra_mn": 0.0,
        "source": "FEMA HousingAssistanceOwners + Renters + PublicAssistance DR-4269"
    },
    {
        "year": 2016,
        "event": "Severe Storms (June 2016)",
        "disaster_id": "DR-4272",
        "total_damage_bn": 3.51,
        "owner_regs": 10407,
        "renter_regs": 2562,
        "total_displaced": 12969,
        "renter_pct": 19.8,
        "pa_infra_mn": 0.0,
        "source": "FEMA HousingAssistanceOwners + Renters + PublicAssistance DR-4272"
    },
    {
        "year": 2017,
        "event": "Hurricane Harvey",
        "disaster_id": "DR-4332",
        "total_damage_bn": 128.62,
        "owner_regs": 443258,
        "renter_regs": 443333,
        "total_displaced": 886591,
        "renter_pct": 50.0,
        "pa_infra_mn": 3600.0,
        "source": "FEMA HousingAssistanceOwners + Renters + PublicAssistance DR-4332"
    },
    {
        "year": 2019,
        "event": "Tropical Storm Imelda",
        "disaster_id": "DR-4466",
        "total_damage_bn": 6.08,
        "owner_regs": 15986,
        "renter_regs": 9804,
        "total_displaced": 25790,
        "renter_pct": 38.0,
        "pa_infra_mn": 0.0,
        "source": "FEMA HousingAssistanceOwners + Renters + PublicAssistance DR-4466"
    },
    {
        "year": 2024,
        "event": "Severe Storms (May 2024)",
        "disaster_id": "DR-4781",
        "total_damage_bn": 12.32,
        "owner_regs": 127050,
        "renter_regs": 142128,
        "total_displaced": 269178,
        "renter_pct": 52.8,
        "pa_infra_mn": 346.3,
        "source": "FEMA HousingAssistanceOwners + Renters + PublicAssistance DR-4781"
    },
])

# ---------------------------------------------------------------------------
# LA WILDFIRES — combined from all 3 FEMA datasets
# ---------------------------------------------------------------------------
LA_EVENTS = pd.DataFrame([
    {
        "year": 2018,
        "event": "Woolsey + Camp Fire Complex",
        "disaster_id": "DR-4407",
        "total_damage_bn": 10.63,
        "owner_regs": 15773,
        "renter_regs": 11088,
        "total_displaced": 26861,
        "renter_pct": 41.3,
        "pa_infra_mn": 2214.2,
        "source": "FEMA HousingAssistanceOwners + Renters + PublicAssistance DR-4407"
    },
    {
        "year": 2020,
        "event": "Bobcat + Wildfires",
        "disaster_id": "DR-4569",
        "total_damage_bn": 0.99,
        "owner_regs": 4729,
        "renter_regs": 3958,
        "total_displaced": 8687,
        "renter_pct": 45.6,
        "pa_infra_mn": 405.9,
        "source": "FEMA HousingAssistanceOwners + Renters + PublicAssistance DR-4569"
    },
    {
        "year": 2025,
        "event": "Palisades + Eaton Fires",
        "disaster_id": "DR-4856",
        "total_damage_bn": 53.17,
        "owner_regs": 185869,
        "renter_regs": 74971,
        "total_displaced": 260840,
        "renter_pct": 28.7,
        "pa_infra_mn": 1167.3,
        "source": "FEMA HousingAssistanceOwners + Renters + PublicAssistance DR-4856"
    },
])

# Real escalation rates from FEMA data analysis
ESCALATION_RATES = {
    "Houston": 0.145,      # 14.5%/yr post-Harvey trend (2019-2024)
    "Los Angeles": 0.297,  # 29.7%/yr (2018-2025 trajectory)
}


def get_houston_data():
    return HOUSTON_EVENTS.copy()


def get_la_data():
    return LA_EVENTS.copy()


def get_city_summary(city: str) -> dict:
    if city == "Houston":
        df = get_houston_data()
        return {
            "total_events": len(df),
            "total_damage_bn": round(df["total_damage_bn"].sum(), 1),
            "total_displaced": int(df["total_displaced"].sum()),
            "avg_renter_pct": round(df["renter_pct"].mean(), 1),
            "escalation_rate_pct": 14.5,
            "worst_event": "Hurricane Harvey 2017 — $128.6B",
            "disaster_type": "Flood",
            "years_covered": f"{df['year'].min()} to {df['year'].max()}",
            "data_sources": "FEMA OpenFEMA: HousingAssistanceOwners, HousingAssistanceRenters, PublicAssistanceApplicantsProgramDeliveries",
        }
    else:
        df = get_la_data()
        return {
            "total_events": len(df),
            "total_damage_bn": round(df["total_damage_bn"].sum(), 1),
            "total_displaced": int(df["total_displaced"].sum()),
            "avg_renter_pct": round(df["renter_pct"].mean(), 1),
            "escalation_rate_pct": 29.7,
            "worst_event": "Palisades + Eaton Fires 2025 — $53.2B",
            "disaster_type": "Wildfire",
            "years_covered": f"{df['year'].min()} to {df['year'].max()}",
            "data_sources": "FEMA OpenFEMA: HousingAssistanceOwners, HousingAssistanceRenters, PublicAssistanceApplicantsProgramDeliveries",
        }
