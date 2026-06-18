"""
build_data.py

Reads raw FEMA OpenFEMA owner/renter registration CSVs from datasets/,
cleans and aggregates them, applies scale factors for total economic damage,
and writes structured events.csv to data/ for the app to consume.

Usage:
    python build_data.py

Outputs:
    data/houston/flood/events.csv
    data/los_angeles/wildfire/events.csv

Other CSVs under data/ (population_growth.csv, infrastructure_capacity.csv,
damage_by_zone.csv, damage_by_neighborhood.csv, interventions_db.csv) contain
data from non-FEMA sources (US Census, city reports, policy research) and
cannot be auto-generated from raw FEMA data. They are committed to the repo
directly.
"""

import os
import pandas as pd

DATA_DIR = "data"
DATASETS_DIR = "datasets"

SCALE_FACTORS = {
    "Houston": 57.3,
    "Los Angeles": 26.4,
}

AFFECTED_ZONES = {
    "Houston": (
        "Brays Bayou, Buffalo Bayou, White Oak Bayou, Addicks Reservoir, "
        "Barker Reservoir, Hunting Bayou, Meyerland, East Houston, Greenspoint"
    ),
    "Los Angeles": (
        "Pacific Palisades, Altadena, Eaton Canyon, Malibu, Topanga, "
        "Hollywood Hills, Ventura County WUI"
    ),
}

REGISTRATION_OVERRIDES = {
    # Registration totals from FEMA state-level summaries.
    # Raw datasets/ CSVs only cover individual counties (primarily Harris for
    # Houston), so these are hardcoded for the full multi-county totals.
    # Key: (disasterNumber, city) -> (owner_regs, renter_regs)
    (4266, "Houston"): (3039, 1212),
    (4269, "Houston"): (14476, 11780),
    (4272, "Houston"): (10407, 2562),
    (4332, "Houston"): (183459, 263617),
    (4466, "Houston"): (15986, 9804),
    (4781, "Houston"): (75225, 102218),
    (4407, "Los Angeles"): (15773, 11088),
    (4569, "Los Angeles"): (4729, 3958),
    (4856, "Los Angeles"): (185869, 74971),
}

IHP_OVERRIDES = {
    # Total IHP (Individuals & Households Program) amounts from FEMA
    # declaration summaries. Raw datasets/ CSVs are zip-code-level and only
    # contain a subset of total IHP for each disaster (primarily Harris
    # County). These are the full state-level IHP totals used with the
    # scale factors to compute total economic damage.
    # Key: (disasterNumber, city) -> (owner_ihp, renter_ihp)
    (4266, "Houston"): (0.0, 0.0),
    (4269, "Houston"): (29413924.11, 18135665.94),
    (4272, "Houston"): (1429849.47, 286076.17),
    (4332, "Houston"): (587923710.17, 192694336.2),
    (4466, "Houston"): (9169058.78, 2889908.52),
    (4781, "Houston"): (81872435.8, 48931629.12),
    (4407, "Los Angeles"): (381721.56, 262133.3),
    (4569, "Los Angeles"): (387298.82, 174912.0),
    (4856, "Los Angeles"): (72795958.23, 104340498.0),
}

INFRASTRUCTURE_COSTS = {
    (4266, "Houston"): 0,
    (4269, "Houston"): 480_000_000,
    (4272, "Houston"): 200_000_000,
    (4332, "Houston"): 3_600_000_000,
    (4466, "Houston"): 0,
    (4781, "Houston"): 346_300_000,
    (4407, "Los Angeles"): 2_214_200_000,
    (4569, "Los Angeles"): 405_900_000,
    (4856, "Los Angeles"): 1_167_300_000,
}

NAME_OVERRIDES = {
    4266: "Severe Storms (March 2016)",
    4269: "Tax Day Flood (April 2016)",
    4272: "Severe Storms (June 2016)",
    4332: "Hurricane Harvey",
    4466: "Tropical Storm Imelda",
    4781: "Severe Storms (May 2024)",
    4407: "Woolsey + Camp Fire Complex",
    4569: "Bobcat + Wildfires",
    4856: "Palisades + Eaton Fires",
}

CITY_CONFIGS = [
    {
        "city": "Houston",
        "disaster": "flood",
        "datasets_city_dir": os.path.join(DATASETS_DIR, "houston"),
        "datasets_disaster_dir": os.path.join(DATASETS_DIR, "houston", "flood"),
        "output_dir": os.path.join(DATA_DIR, "houston", "flood"),
        "state_declaration_files": [
            os.path.join(DATASETS_DIR, "tx_flood_declarations.csv"),
            os.path.join(DATASETS_DIR, "tx_hurricane_declarations.csv"),
            os.path.join(DATASETS_DIR, "tx_storm_declarations.csv"),
        ],
        "disaster_numbers": [4266, 4269, 4272, 4332, 4466, 4781],
        "disaster_type": "Flood",
    },
    {
        "city": "Los Angeles",
        "disaster": "wildfire",
        "datasets_city_dir": os.path.join(DATASETS_DIR, "los_angeles"),
        "datasets_disaster_dir": os.path.join(DATASETS_DIR, "los_angeles", "wildfire"),
        "output_dir": os.path.join(DATA_DIR, "los_angeles", "wildfire"),
        "state_declaration_files": [
            os.path.join(DATASETS_DIR, "ca_fire_declarations.csv"),
        ],
        "disaster_numbers": [4407, 4569, 4856],
        "disaster_type": "Wildfire",
    },
]

EVENTS_COLUMNS = [
    "event_id", "event_name", "year",
    "total_damage_usd", "total_damage_bn", "infrastructure_cost",
    "owner_registrations", "renter_registrations",
    "total_displaced", "renter_pct",
    "total_owner_ihp_amount", "total_renter_ihp_amount",
    "incident_begin", "incident_end",
    "disaster_type", "affected_zones",
]


def _strftime_iso(date_str):
    """Convert '2017-08-23T00:00:00.000Z' to '2017-08-23'."""
    if not isinstance(date_str, str) or not date_str:
        return ""
    return date_str[:10]


def load_declarations(config):
    """
    Load all relevant declaration CSVs and build a lookup dict:
    disasterNumber -> {event_name, incident_begin, incident_end}
    """
    city = config["city"]
    dns = config["disaster_numbers"]
    all_dfs = []

    for path in config["state_declaration_files"]:
        if os.path.exists(path):
            df = pd.read_csv(path)
            all_dfs.append(df)

    dd = config["datasets_city_dir"]
    for dn in dns:
        path = os.path.join(dd, f"declarations_{dn}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            all_dfs.append(df)

    if not all_dfs:
        return {}

    combined = pd.concat(all_dfs, ignore_index=True)
    combined["disasterNumber"] = combined["disasterNumber"].astype(int)
    mask = combined["disasterNumber"].isin(dns)
    filtered = combined[mask]

    result = {}
    for dn in dns:
        rows = filtered[filtered["disasterNumber"] == dn]
        if rows.empty:
            print(f"  [warn] No declaration found for DR-{dn}")
            continue
        row = rows.iloc[0]
        event_name = NAME_OVERRIDES.get(
            dn, row["declarationTitle"].title()
        )
        result[dn] = {
            "event_name": event_name,
            "incident_begin": _strftime_iso(row["incidentBeginDate"]),
            "incident_end": _strftime_iso(row["incidentEndDate"]),
        }
    return result


def build_events(config):
    """Build events.csv for one city/disaster config."""
    city = config["city"]
    scale = SCALE_FACTORS[city]
    dns = config["disaster_numbers"]
    print(f"\n=== Building events for {city} ===")

    declarations = load_declarations(config)

    merged = pd.DataFrame({"disasterNumber": dns})

    def lookup(dn, key):
        if key in ("owner_ihp", "renter_ihp"):
            idx = 0 if key == "owner_ihp" else 1
            val = IHP_OVERRIDES.get((int(dn), city))
            return val[idx] if val else 0.0
        if key in ("owner_regs", "renter_regs"):
            idx = 0 if key == "owner_regs" else 1
            val = REGISTRATION_OVERRIDES.get((int(dn), city))
            return val[idx] if val else 0
        info = declarations.get(int(dn))
        if info is None:
            return NAME_OVERRIDES.get(int(dn), f"Unknown Event {dn}") if key == "event_name" else ""
        return info.get(key, "")

    merged["total_owner_ihp_amount"] = merged["disasterNumber"].apply(
        lambda dn: lookup(dn, "owner_ihp")
    )
    merged["total_renter_ihp_amount"] = merged["disasterNumber"].apply(
        lambda dn: lookup(dn, "renter_ihp")
    )
    merged["owner_registrations"] = merged["disasterNumber"].apply(
        lambda dn: lookup(dn, "owner_regs")
    )
    merged["renter_registrations"] = merged["disasterNumber"].apply(
        lambda dn: lookup(dn, "renter_regs")
    )

    merged["total_displaced"] = (
        merged["owner_registrations"] + merged["renter_registrations"]
    ).astype(int)

    merged["renter_pct"] = round(
        merged["renter_registrations"] / merged["total_displaced"] * 100, 1
    )
    merged["renter_pct"] = merged["renter_pct"].fillna(0.0)

    merged["total_ihp"] = (
        merged["total_owner_ihp_amount"].astype(float)
        + merged["total_renter_ihp_amount"].astype(float)
    )
    merged["total_damage_usd"] = (merged["total_ihp"] * scale).round(2)
    merged["total_damage_bn"] = round(merged["total_damage_usd"] / 1e9, 2)

    merged["infrastructure_cost"] = merged["disasterNumber"].map(
        lambda dn: INFRASTRUCTURE_COSTS.get((int(dn), city), 0)
    ).astype(float)

    merged["event_name"] = merged["disasterNumber"].apply(
        lambda dn: lookup(dn, "event_name")
    )
    merged["year"] = merged["disasterNumber"].map(
        lambda dn: int(declarations.get(int(dn), {}).get("incident_begin", "2000")[:4])
    )
    merged["incident_begin"] = merged["disasterNumber"].apply(
        lambda dn: lookup(dn, "incident_begin")
    )
    merged["incident_end"] = merged["disasterNumber"].apply(
        lambda dn: lookup(dn, "incident_end")
    )
    merged["disaster_type"] = config["disaster_type"]
    merged["affected_zones"] = AFFECTED_ZONES[city]

    merged = merged.rename(columns={"disasterNumber": "event_id"})
    merged["event_id"] = merged["event_id"].apply(lambda x: f"DR-{int(x)}")

    merged = merged[EVENTS_COLUMNS]
    merged = merged.sort_values("year").reset_index(drop=True)

    os.makedirs(config["output_dir"], exist_ok=True)
    output_path = os.path.join(config["output_dir"], "events.csv")
    merged.to_csv(output_path, index=False)
    print(f"  Wrote {output_path} ({len(merged)} events)")


def main():
    print("build_data.py — FEMA raw data to structured events.csv")
    print("=" * 55)
    for config in CITY_CONFIGS:
        build_events(config)
    print("\nDone.")


if __name__ == "__main__":
    main()
