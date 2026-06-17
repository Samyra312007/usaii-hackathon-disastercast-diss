# DisasterCast
### AI-powered cost of inaction simulator for flood and wildfire prevention policy
**USAII Global AI Hackathon 2026 | Graduate Track | Brief 6A**

## What it does

City officials know what past disasters cost. They do not know what the next one will cost if nothing changes — or what to fix first to change that number.

DisasterCast answers exactly those two questions:

1. **What will the next disaster cost if nothing changes?** Based on real FEMA damage records across multiple events, the tool projects the next-event cost broken into direct damage, displaced families, healthcare burden, school days lost, and lost wages.

2. **What should the city prioritise to reduce that cost?** An AI layer reasons across FEMA Hazard Mitigation Grant Program outcomes and infrastructure research to generate ranked prevention actions specific to each city — ordered by projected disaster cost reduction per dollar invested.

Covers Houston (floods) and Los Angeles (wildfires) with real FEMA OpenFEMA data.

---

## Setup

### 1. Clone and install
```bash
git clone https://github.com/Ruchess07/usaii-hackathon-disastercast-diss.git
cd usaii-hackathon-disastercast-diss
pip install -r requirements.txt
```

### 2. Get a free Gemini API key
Go to: https://aistudio.google.com/app/apikey
Takes 2 minutes, no credit card required.

### 3. Create a .env file
Create a file called `.env` in the project root:
```
GOOGLE_API_KEY=your_key_here
```

### 4. Run the app
```bash
streamlit run app.py
```
Opens at http://localhost:8501

---

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to share.streamlit.io
3. Connect your repo, set `app.py` as the main file
4. Add `GOOGLE_API_KEY` in the Streamlit secrets manager
5. Deploy — shareable link in 2 minutes

---

## Project structure

```
disastercast/
├── app.py                  # Main Streamlit app — 3 screens
├── requirements.txt        # All dependencies
├── README.md
└── utils/
    ├── data_loader.py      # Real FEMA data — Houston + LA events
    ├── cost_engine.py      # Cost projection and escalation model
    └── ai_engine.py        # Gemini API — recommendations + policy brief
```

---

## Data sources

| Dataset | Source | Used for |
|---------|--------|----------|
| FEMA OpenFEMA HousingAssistanceOwners | fema.gov/about/openfema/data-sets | Houston and LA damage by event — 159,412 records |
| FEMA DisasterDeclarationsSummaries | fema.gov/about/openfema/data-sets | Disaster metadata, incident types, dates |
| Harris County HCFCD | hcfcd.org | Houston flood zone infrastructure |
| OECD 2025 | oecd.org | AI and disaster damage cost methodology |
| Urban Institute | urban.org | Disaster to homelessness causal research |

---

## Methodology

FEMA housing assistance records capture residential damage only. Total economic damage is estimated using scale factors derived from two anchor points where full economic damage is publicly documented:

- Harvey 2017: $2.18B FEMA housing → $125B total = **57.3x scale factor**
- Palisades 2025: $1.97B FEMA housing → $52B total = **26.4x scale factor**

Cost escalation rates derived from FEMA data analysis:
- Houston: **14.5% per year** (2019 to 2024 post-Harvey trend)
- Los Angeles: **29.7% per year** (2018 to 2025 trajectory)

Model used: **log-linear regression (exponential growth)** — the same approach used by FEMA, World Bank, and Swiss Re for catastrophe cost modelling. Disaster costs compound, not accumulate linearly, because each event without infrastructure change leaves greater vulnerability for the next.

All projections shown with confidence ranges. Human expert review recommended before policy action.

---

## Responsible AI

**Risk:** Projections based on historic patterns may underestimate costs in rapidly urbanising zones where population density has grown faster than the damage baseline reflects.

**Mitigation:** Confidence intervals are displayed on every projection, not buried in footnotes. When population growth in a vulnerable zone exceeds 15% since the last major event, the tool widens the confidence interval and flags a human review recommendation. AI generates the analysis — the budget committee makes the decision.

---

## Licence

Built for USAII Global AI Hackathon 2026. Data sourced from US federal open data portals under public domain licence.
