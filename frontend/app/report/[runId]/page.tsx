"use client";

import { use, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Source = { url: string; source_type: string; fetched_at: string; ok: boolean };
type ClaimRow = {
  id: number;
  text: string;
  claim_type: "verified" | "reported" | "interpretation";
  source_ids: number[];
  confidence: number | null;
};
type Payload = {
  run: {
    id: number; status: string; started_at: string; finished_at: string | null;
    cost_cents: number; tool_calls: number;
  };
  product: { name: string; domain: string; url: string; category: string };
  competitors: {
    id: number; name: string; domain: string; relationship: string | null;
    confidence: number | null; discovery_methods: string[];
  }[];
  sections: Record<string, ClaimRow[]>;
  sources: Record<string, Source>;
  flags: { claim_id: number; section: string; flag: string; detail: string }[];
  citation_coverage: number | null;
};

const SECTION_TITLES: Record<string, string> = {
  executive_summary: "Executive summary",
  competitive_landscape: "Competitive landscape",
  feature_comparison: "Feature comparison",
  pricing_comparison: "Pricing comparison",
};

const BADGES: Record<ClaimRow["claim_type"], { label: string; cls: string }> = {
  verified: { label: "Verified", cls: "bg-emerald-100 text-emerald-800" },
  reported: { label: "Reported", cls: "bg-amber-100 text-amber-800" },
  interpretation: { label: "Analysis", cls: "bg-violet-100 text-violet-800" },
};

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
}

export default function ReportPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = use(params);
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/reports/${runId}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [runId]);

  if (error)
    return <main className="p-10 text-red-600">Could not load report: {error}</main>;
  if (!data) return <main className="p-10 text-gray-400">Loading report…</main>;

  // Stable footnote numbering: sorted source ids -> 1..n
  const sourceIds = Object.keys(data.sources).map(Number).sort((a, b) => a - b);
  const footnote = new Map(sourceIds.map((id, i) => [id, i + 1]));

  const durationSec =
    data.run.finished_at && data.run.started_at
      ? Math.round(
          (new Date(data.run.finished_at).getTime() -
            new Date(data.run.started_at).getTime()) / 1000,
        )
      : null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <a href="/" className="text-sm text-blue-600 hover:underline">
        ← New report
      </a>
      <h1 className="mt-2 text-3xl font-bold">
        {data.product.name}{" "}
        <span className="font-normal text-gray-400">competitive report</span>
      </h1>
      <p className="mt-1 text-gray-500">{data.product.category}</p>
      <p className="mt-2 text-sm text-gray-400">
        Generated {fmtDate(data.run.finished_at)}
        {durationSec !== null && <> · {durationSec}s</>}
        {" · "}${(data.run.cost_cents / 100).toFixed(2)} model cost
        {data.citation_coverage !== null && (
          <> · {Math.round(data.citation_coverage * 100)}% of factual claims cited</>
        )}
      </p>

      <div className="mt-5 flex flex-wrap gap-2">
        {data.competitors.map((c) => (
          <span
            key={c.id}
            title={`${c.relationship ?? ""} · confidence ${c.confidence ?? "?"} · found via ${c.discovery_methods.join(", ")}`}
            className="rounded-full border border-gray-300 px-3 py-1 text-sm"
          >
            {c.name}
            {c.relationship === "direct" && (
              <span className="ml-1.5 text-xs text-emerald-600">direct</span>
            )}
            {c.relationship === "adjacent" && (
              <span className="ml-1.5 text-xs text-amber-600">adjacent</span>
            )}
          </span>
        ))}
      </div>

      {data.flags.length > 0 && (
        <div className="mt-6 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm">
          <p className="font-semibold text-amber-800">
            {data.flags.length} validation flag{data.flags.length > 1 && "s"}
          </p>
          <ul className="mt-1 list-inside list-disc text-amber-700">
            {data.flags.map((f, i) => (
              <li key={i}>
                <span className="font-mono">{f.flag}</span>: {f.detail}
              </li>
            ))}
          </ul>
        </div>
      )}

      {Object.entries(SECTION_TITLES).map(([key, title]) => (
        <section key={key} className="mt-10">
          <h2 className="border-b border-gray-200 pb-2 text-xl font-bold">
            {title}
          </h2>
          <ul className="mt-4 space-y-4">
            {(data.sections[key] ?? []).map((claim) => {
              const badge = BADGES[claim.claim_type];
              return (
                <li key={claim.id} className="flex gap-3">
                  <span
                    className={`mt-0.5 h-fit shrink-0 rounded px-1.5 py-0.5 text-xs font-semibold ${badge.cls}`}
                  >
                    {badge.label}
                  </span>
                  <p className="leading-relaxed">
                    {claim.text}{" "}
                    {claim.source_ids.map((sid) => {
                      const src = data.sources[String(sid)];
                      if (!src) return null;
                      return (
                        <a
                          key={sid}
                          href={src.url}
                          target="_blank"
                          rel="noreferrer"
                          title={`${src.url} (${src.source_type}, retrieved ${fmtDate(src.fetched_at)})`}
                          className="ml-0.5 align-super text-xs font-semibold text-blue-600 hover:underline"
                        >
                          [{footnote.get(sid)}]
                        </a>
                      );
                    })}
                  </p>
                </li>
              );
            })}
          </ul>
        </section>
      ))}

      <section className="mt-12">
        <h2 className="border-b border-gray-200 pb-2 text-xl font-bold">Sources</h2>
        <ol className="mt-4 space-y-1.5 text-sm">
          {sourceIds.map((sid) => {
            const src = data.sources[String(sid)];
            return (
              <li key={sid} className="flex gap-2">
                <span className="w-8 shrink-0 font-semibold text-gray-400">
                  [{footnote.get(sid)}]
                </span>
                <span>
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noreferrer"
                    className="break-all text-blue-600 hover:underline"
                  >
                    {src.url}
                  </a>{" "}
                  <span className="text-gray-400">
                    {src.source_type} · retrieved {fmtDate(src.fetched_at)}
                    {!src.ok && " · fetch failed"}
                  </span>
                </span>
              </li>
            );
          })}
        </ol>
      </section>

      <p className="mt-12 border-t border-gray-100 pt-4 text-xs text-gray-400">
        Facts marked <b>Verified</b> come from the company&apos;s own website;{" "}
        <b>Analysis</b> is AI interpretation of the cited evidence. Missing
        information is reported as unavailable, never inferred. This report link
        is stable and shareable.
      </p>
    </main>
  );
}
