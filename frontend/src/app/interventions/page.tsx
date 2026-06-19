"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense, useEffect, useState, useCallback } from "react";
import { InterventionCard } from "@/components/intervention-card";
import { MetricCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChartSkeleton } from "@/components/ui/skeleton";
import { InterventionScorecard } from "@/components/intervention-scorecard";
import { generateReport } from "@/lib/report";
import { saveState, loadState } from "@/lib/persist";
import {
  getCitySummary,
  getCityProjection,
  getCityInterventions,
  getCityAffectedZones,
  getCityPatternExplanation,
  getReportUrl,
  postRecommendations,
  postPolicyBrief,
} from "@/lib/api";
import type { ProjectionResponse, Intervention, CitySummary } from "@/types";

/* Zone keyword mapping */
const ZONE_KEYWORDS: Record<string, string> = {
  Brays: "Brays Bayou",
  Addicks: "Addicks / Barker Reservoir",
  "White Oak": "White Oak Bayou",
  Hunting: "Hunting Bayou",
  Floodplain: "Addicks / Brays / White Oak",
  Warning: "All zones",
  Palisades: "Pacific Palisades",
  Eaton: "Altadena / Eaton Canyon",
  "Power Line": "Pacific Palisades / Altadena / Hollywood Hills",
  "Building Code": "All WUI zones",
  Vegetation: "Topanga / Malibu / Hollywood Hills",
  Evacuation: "Pacific Palisades / Topanga / Malibu",
  "Home Hardening": "Pacific Palisades / Altadena / Hollywood Hills",
  "Fuel Break": "Topanga / Malibu / Angeles National Forest WUI",
};

function findZone(action: string, defaultZones: string): string {
  for (const [kw, zone] of Object.entries(ZONE_KEYWORDS)) {
    if (action.toLowerCase().includes(kw.toLowerCase())) return zone;
  }
  return defaultZones.split(", ").slice(0, 3).join(", ");
}

/* ROI chart (pure SVG) */
function RoiChart({ interventions }: { interventions: Intervention[] }) {
  if (!interventions.length) return null;
  const maxSaving = Math.max(...interventions.map((r) => r.projected_saving_mn));
  const barH = 24;
  const gap = 8;
  const chartH = interventions.length * (barH + gap);
  const labelW = 140;

  // Sort a copy to confirm the displayed order matches ROI ranking logic
  const sortedByRoi = [...interventions].sort(
    (a, b) => b.projected_saving_mn / b.estimated_cost_mn - a.projected_saving_mn / a.estimated_cost_mn
  );
  const topPick = sortedByRoi[0];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="md:col-span-2 bg-white border border-[#EAEAEA] rounded-[8px] p-5">
        <p className="text-xs font-medium text-[#1E293B] mb-4">
          Projected disaster cost reduction per intervention
        </p>
        <svg width="100%" height={chartH + 20} className="overflow-visible">
          {interventions.map((r, i) => {
            const pct = r.projected_saving_mn / maxSaving;
            const barW = pct * (400 - labelW);
            const y = i * (barH + gap);
            return (
              <g key={i}>
                <text x={0} y={y + barH / 2 + 4} textAnchor="start" className="text-[11px] fill-[#787774]">
                  {r.action.length > 22 ? r.action.slice(0, 20) + "..." : r.action}
                </text>
                <rect
                  x={labelW}
                  y={y}
                  width={barW}
                  height={barH}
                  rx={4}
                  fill="#346538"
                  opacity={0.85}
                />
                <text
                  x={labelW + barW + 6}
                  y={y + barH / 2 + 4}
                  textAnchor="start"
                  className="text-[11px] fill-[#1E293B] font-medium"
                >
                  ${r.projected_saving_mn}M saved
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="bg-[#F7F6F3] border border-[#EAEAEA] rounded-[8px] p-4">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[#787774] mb-2">
          How this ranking works
        </p>
        <p className="text-[11px] leading-relaxed text-[#1E293B]">
          Bars are ordered by <strong>return on investment</strong> — projected savings
          divided by intervention cost — not by raw dollar size. A smaller, cheaper fix
          that prevents a lot of damage ranks above a bigger fix that costs more per
          dollar saved.
        </p>
        {topPick && (
          <p className="text-[11px] leading-relaxed text-[#346538] mt-2">
            <strong>Top pick:</strong> {topPick.action} returns{" "}
            ${(topPick.projected_saving_mn / topPick.estimated_cost_mn).toFixed(1)} saved
            for every $1 spent — the highest ratio of any option here.
          </p>
        )}
        <p className="text-[11px] leading-relaxed text-[#787774] mt-2">
          This means the order can change if a cheaper project with a smaller total
          saving still beats an expensive one on efficiency.
        </p>
      </div>
    </div>
  );
}

function InterventionsContent() {
  const searchParams = useSearchParams();
  const [city, setCity] = useState<string>("houston");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = params.get("city");
    const saved = loadState<string | null>("city", null);
    setCity(fromUrl || saved || "houston");
  }, [searchParams]);

  const cityName = city === "houston" ? "Houston" : "Los Angeles";

  useEffect(() => {
    if (city) saveState("city", city);
  }, [city]);

  const [summary, setSummary] = useState<CitySummary | null>(null);
  const [projection, setProjection] = useState<ProjectionResponse | null>(null);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [aiRecs, setAiRecs] = useState<Intervention[] | null>(null);
  const [brief, setBrief] = useState<string | null>(null);
  const [savedReport, setSavedReport] = useState<string | null>(null);
  const [affectedZones, setAffectedZones] = useState("");
  const [patternText, setPatternText] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatingBrief, setGeneratingBrief] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getCitySummary(city),
      getCityProjection(city),
      getCityInterventions(city),
      getCityAffectedZones(city),
      getCityPatternExplanation(city),
    ]).then(([s, p, i, z, pat]) => {
      setSummary(s);
      setProjection(p);
      setInterventions(i);
      setAffectedZones(z.zones);
      setPatternText(pat.explanation);
    }).finally(() => setLoading(false));
  }, [city]);

  const handleGenerateRecs = useCallback(async () => {
    if (!summary || !projection) return;
    setGenerating(true);
    try {
      const recs = await postRecommendations(city, {
        next_event_cost_bn: projection.projection.total_projected_cost_bn,
        total_historic_cost_bn: summary.total_damage_bn,
        total_events: summary.total_events,
        years_covered: summary.years_covered,
      });
      setAiRecs(recs);
    } catch {
      setAiRecs(null);
    }
    setGenerating(false);
  }, [city, summary, projection]);

  const handleGenerateBrief = useCallback(async () => {
    if (!projection || !aiRecs) return;
    setGeneratingBrief(true);
    try {
      const res = await postPolicyBrief(city, {
        next_event_cost_bn: projection.projection.total_projected_cost_bn,
        recommendations: aiRecs,
      });
      setBrief(res.brief);
    } catch {
      setBrief(null);
    }
    setGeneratingBrief(false);
  }, [city, projection, aiRecs]);

  const handleSaveReport = () => {
    if (!summary || !projection) return;
    const report = generateReport(
      cityName,
      city === "houston" ? "Flood" : "Wildfire",
      summary,
      projection,
      aiRecs || interventions,
      affectedZones
    );
    setSavedReport(report);
  };

  const displayRecs = aiRecs || interventions;

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse bg-[#EAEAEA] h-8 w-64 rounded" />
        <div className="grid grid-cols-2 gap-4">
          {[1, 2].map((i) => <div key={i} className="animate-pulse bg-[#EAEAEA] h-24 rounded" />)}
        </div>
        <ChartSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <p className="text-[10px] uppercase tracking-[0.12em] text-[#787774] mb-2 font-medium">
          Step 03 · Prevention strategy for {cityName}
        </p>
        <h1 className="text-xl md:text-2xl font-semibold text-[#1E293B] tracking-tight">
          What to prioritise to change that number
        </h1>
      </div>

      {/* Savings cards */}
      {projection && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <MetricCard
            label="Cost if nothing changes (next event)"
            value={`$${projection.savings.next_event_cost_bn.toFixed(1)}B`}
            variant="cost"
          />
          <MetricCard
            label="Preventable with targeted action"
            value={`$${projection.savings.prevented_cost_bn.toFixed(1)}B`}
            subtitle={`~${projection.savings.reduction_pct}% reduction — FEMA HMGP outcomes`}
            variant="success"
          />
        </div>
      )}

      {/* Pattern summary */}
      {patternText && (
        <div className="bg-[#FBF3DB] border border-[#956400]/20 rounded-[8px] p-4">
          <p className="text-xs text-[#956400] leading-relaxed">{patternText}</p>
        </div>
      )}

      <InterventionScorecard slug={city} />

      {/* Generate AI recs */}
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleGenerateRecs} disabled={generating} size="lg">
          {generating ? "Analysing..." : "Generate AI prevention recommendations"}
        </Button>
        {(aiRecs || interventions.length > 0) && (
          <Button variant="secondary" onClick={handleSaveReport}>
            Save Report
          </Button>
        )}
      </div>

      {savedReport && (
        <div className="flex items-center gap-4">
          <a
            href={`data:text/plain;charset=utf-8,${encodeURIComponent(savedReport)}`}
            download={`disastercast_report_${city}.txt`}
            className="inline-block text-xs text-[#1F6C9F] underline"
          >
            Download report (.txt)
          </a>
          <a
            href={getReportUrl(city)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-xs text-[#346538] underline"
          >
            Download report (PDF)
          </a>
        </div>
      )}

      {/* Intervention cards */}
      {displayRecs.length > 0 && (
        <>
          <RoiChart interventions={displayRecs} />

          {displayRecs.map((r) => (
            <InterventionCard
              key={r.rank}
              intervention={r}
              zone={findZone(r.action, affectedZones)}
            />
          ))}

          {/* Policy brief */}
          {!brief && aiRecs && (
            <Button variant="secondary" onClick={handleGenerateBrief} disabled={generatingBrief}>
              {generatingBrief ? "Drafting..." : "Generate policy brief"}
            </Button>
          )}

          {brief && (
            <div className="bg-[#F7F6F3] border border-[#EAEAEA] rounded-[8px] p-5">
              <p className="text-xs font-medium text-[#1E293B] mb-2">Policy brief — ready for budget committee</p>
              <p className="text-sm text-[#1E293B] leading-relaxed whitespace-pre-line">{brief}</p>
              <div className="mt-3">
                <a
                  href={`data:text/plain;charset=utf-8,${encodeURIComponent(brief)}`}
                  download={`disastercast_policy_brief_${city}.txt`}
                  className="inline-block text-xs text-[#1F6C9F] underline"
                >
                  Download policy brief
                </a>
              </div>
            </div>
          )}
        </>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4">
        <Link href={`/dashboard?city=${city}`}>
          <Button variant="secondary">← Back to cost projection</Button>
        </Link>
        <Link href="/">
          <Button variant="ghost">Start Over</Button>
        </Link>
      </div>
    </div>
  );
}

export default function InterventionsPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <div className="animate-pulse bg-[#EAEAEA] h-8 w-64 rounded" />
          <div className="animate-pulse bg-[#EAEAEA] h-32 w-full rounded" />
        </div>
      }
    >
      <InterventionsContent />
    </Suspense>
  );
}
