"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { CitySummaryBar } from "@/components/city-summary-bar";
import { AffectedZonesBadge } from "@/components/affected-zones-badge";
import { HistoricalChart } from "@/components/historical-chart";
import { RenterOwnerBreakdown } from "@/components/renter-owner-breakdown";
import { CostBreakdown } from "@/components/cost-breakdown";
import { CompoundingChart } from "@/components/compounding-chart";
import { PatternBox } from "@/components/pattern-box";
import { ZoneHeatmap } from "@/components/zone-heatmap";
import { ZoneEscalationChart } from "@/components/zone-escalation-chart";
import { ZoneCompoundingGrid } from "@/components/zone-compounding-grid";
import { HomelessnessTrendChart } from "@/components/homelessness-trend-chart";
import { HarveyDamageMap } from "@/components/harvey-damage-map";
import { WatershedChart } from "@/components/watershed-chart";
import { ScenarioSliders } from "@/components/scenario-sliders";
import { InfrastructureCapacity } from "@/components/infrastructure-capacity";
import { Button } from "@/components/ui/button";
import { TimeRangeSelector } from "@/components/time-range-selector";
import { saveState, loadState } from "@/lib/persist";

function DashboardContent() {
  const searchParams = useSearchParams();
  const [city, setCity] = useState<string>("houston");

  const [rangeSince, setRangeSince] = useState<number>(2015);
  const [rangeUntil, setRangeUntil] = useState<number>(2025);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = params.get("city");
    const saved = loadState<string | null>("city", null);
    setCity(fromUrl || saved || "houston");
    setRangeSince(loadState("rangeSince", 2015));
    setRangeUntil(loadState("rangeUntil", 2025));
  }, [searchParams]);

  useEffect(() => {
    if (city) saveState("city", city);
  }, [city]);

  useEffect(() => {
    saveState("rangeSince", rangeSince);
    saveState("rangeUntil", rangeUntil);
  }, [rangeSince, rangeUntil]);
  const cityName = city === "houston" ? "Houston" : "Los Angeles";
  const disasterType = city === "houston" ? "Flood" : "Wildfire";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <p className="text-[10px] uppercase tracking-[0.12em] text-[#787774] mb-2 font-medium">
          Step 02 · {cityName}, {disasterType} risk zone
        </p>
        <h1 className="text-xl md:text-2xl font-semibold text-[#1E293B] tracking-tight">
          Cost of the next {disasterType.toLowerCase()} if nothing changes
        </h1>
      </div>

      {/* City summary + zones */}
      <CitySummaryBar slug={city} />
      <AffectedZonesBadge slug={city} />
      <InfrastructureCapacity slug={city} />

      {/* Time range + Historical chart */}
      <TimeRangeSelector
        since={rangeSince}
        until={rangeUntil}
        minYear={2000}
        maxYear={2025}
        onChange={(s, u) => { setRangeSince(s); setRangeUntil(u); }}
      />
      <HistoricalChart slug={city} since={rangeSince} until={rangeUntil} />
      <RenterOwnerBreakdown slug={city} />

      {/* Cost breakdown */}
      <CostBreakdown slug={city} />

      {/* Pattern box */}
      <PatternBox slug={city} />

      {/* Zone heatmap */}
      <ZoneHeatmap slug={city} />
      <ZoneEscalationChart slug={city} />
      <ZoneCompoundingGrid slug={city} />

      {/* Homelessness trend — real HUD PIT count data */}
      <HomelessnessTrendChart slug={city} cityName={cityName} />

      {/* Harvey property damage map — Houston only, real GeoJSON */}
      {city === "houston" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <HarveyDamageMap />
          <WatershedChart />
        </div>
      )}

      {/* Scenario sliders */}
      <ScenarioSliders slug={city} />

      {/* Compounding chart */}
      <CompoundingChart slug={city} since={rangeSince} until={rangeUntil} />

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4">
        <Link href="/">
          <Button variant="secondary">← Back</Button>
        </Link>
        <Link href={`/interventions?city=${city}`}>
          <Button>See What to Prioritize →</Button>
        </Link>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <div className="animate-pulse bg-[#EAEAEA] h-8 w-64 rounded" />
          <div className="animate-pulse bg-[#EAEAEA] h-32 w-full rounded" />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
