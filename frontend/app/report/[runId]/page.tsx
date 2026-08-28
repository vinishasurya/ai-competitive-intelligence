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
type Tier = {
  name: string;
  price_text: string;
  price_usd: number | null;
  billing_period: string;
};
type PricingRow = {
  company: string;
  domain: string;
  is_subject: boolean;
  available: boolean;
  tiers: Tier[];
  notes: string | null;
  source_ids: number[];
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
  pricing: PricingRow[];
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
  verified: { label: "Verified", cls: "bg-mint-wash text-teal-deep" },
  reported: { label: "Reported", cls: "bg-amber-100 text-amber-800" },
  interpretation: { label: "Analysis", cls: "bg-ink text-mint" },
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
  if (!data) return <main className="p-10 text-sub">Loading report…</main>;

  const sourceIds = Object.keys(data.sources).map(Number).sort((a, b) => a - b);
  const footnote = new Map(sourceIds.map((id, i) => [id, i + 1]));

  const durationSec =
    data.run.finished_at && data.run.started_at
      ? Math.round(
          (new Date(data.run.finished_at).getTime() -
            new Date(data.run.started_at).getTime()) / 1000,
        )
      : null;

  const Cite = ({ sid }: { sid: number }) => {
    const src = data.sources[String(sid)];
    if (!src) return null;
    return (
      <a
        href={src.url}
        target="_blank"
        rel="noreferrer"
        title={`${src.url} (${src.source_type}, retrieved ${fmtDate(src.fetched_at)})`}
        className="ml-0.5 align-super text-xs font-bold text-teal hover:underline"
      >
        [{footnote.get(sid)}]
      </a>
    );
  };

  const stats = [
    {
      value: data.citation_coverage !== null
        ? `${Math.round(data.citation_coverage * 100)}%`
        : "—",
      label: "claims cited",
      hot: true,
    },
    { value: String(data.competitors.length), label: "verified rivals" },
    { value: durationSec !== null ? `${durationSec}s` : "—", label: "research time" },
    { value: `$${(data.run.cost_cents / 100).toFixed(2)}`, label: "model cost" },
  ];

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <a href="/" className="text-sm font-medium text-teal hover:underline">
        ← New report
      </a>
      <p className="mt-4 text-xs font-bold uppercase tracking-[0.1em] text-teal">
        Competitive report · {fmtDate(data.run.finished_at)}
      </p>
      <h1 className="mt-1.5 text-3xl font-bold tracking-[-0.03em] text-ink">
        {data.product.name}{" "}
        <span className="font-normal text-sub">{data.product.category}</span>
      </h1>

      <div className="mt-6 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="rounded-[14px] bg-ink px-4 py-3">
            <b className={`block text-xl tabular-nums tracking-[-0.02em] ${s.hot ? "text-mint" : "text-white"}`}>
              {s.value}
            </b>
            <span className="text-[0.62rem] font-semibold uppercase tracking-[0.06em] text-white/50">
              {s.label}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {data.competitors.map((c) => (
          <span
            key={c.id}
            title={`${c.relationship ?? ""} · confidence ${c.confidence ?? "?"} · found via ${c.discovery_methods.join(", ")}`}
            className="rounded-[10px] border border-card-line bg-white px-3 py-1.5 text-sm font-medium text-ink"
          >
            {c.name}
            {c.relationship && (
              <span className="ml-1.5 text-xs font-bold text-teal">
                {c.relationship === "adjacent" ? "adj" : c.relationship}
              </span>
            )}
          </span>
        ))}
      </div>

      {data.flags.length > 0 && (
        <div className="card-shadow mt-6 rounded-[14px] border border-amber-200 bg-white p-4 text-sm">
          <p className="font-bold text-amber-700">
            {data.flags.length} validation flag{data.flags.length > 1 && "s"}
          </p>
          <ul className="mt-1 list-inside list-disc text-sub">
            {data.flags.map((f, i) => (
              <li key={i}>
                <span className="font-mono text-xs">{f.flag}</span>: {f.detail}
              </li>
            ))}
          </ul>
        </div>
      )}

      {Object.entries(SECTION_TITLES).map(([key, title]) => (
        <section key={key} className="mt-11">
          <h2 className="text-xs font-bold uppercase tracking-[0.09em] text-sub">
            {title}
          </h2>
          <ul className="mt-4 space-y-2.5">
            {(data.sections[key] ?? []).map((claim) => {
              const badge = BADGES[claim.claim_type];
              return (
                <li
                  key={claim.id}
                  className="card-shadow flex gap-3 rounded-[14px] bg-white px-4 py-3.5"
                >
                  <span
                    className={`mt-0.5 h-fit shrink-0 rounded-[7px] px-2 py-0.5 text-[0.62rem] font-extrabold uppercase tracking-[0.04em] ${badge.cls}`}
                  >
                    {badge.label}
                  </span>
                  <p className="leading-relaxed text-ink">
                    {claim.text}{" "}
                    {claim.source_ids.map((sid) => (
                      <Cite key={sid} sid={sid} />
                    ))}
                  </p>
                </li>
              );
            })}
          </ul>

          {key === "pricing_comparison" && data.pricing?.length > 0 && (
            <div className="card-shadow mt-4 overflow-x-auto rounded-[14px] bg-white">
              <table className="w-full border-collapse text-sm tabular-nums">
                <thead>
                  <tr className="bg-ink text-left text-[0.66rem] font-bold uppercase tracking-[0.05em] text-white">
                    <th className="px-4 py-2.5">Company</th>
                    <th className="px-4 py-2.5">Public tiers</th>
                    <th className="px-4 py-2.5">Src</th>
                  </tr>
                </thead>
                <tbody>
                  {data.pricing.map((row) => (
                    <tr key={row.domain + row.company} className="border-b border-row-line last:border-0 align-top">
                      <td className="px-4 py-3 font-semibold text-ink">
                        {row.company}
                        {row.is_subject && (
                          <span className="ml-1.5 text-[0.6rem] font-bold uppercase text-teal">subject</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {row.available ? (
                          <div className="flex flex-wrap gap-1.5">
                            {row.tiers.map((t, i) => (
                              <span
                                key={i}
                                className="rounded-[7px] bg-row-line px-2 py-1 text-xs font-medium text-ink"
                                title={t.price_text}
                              >
                                {t.name}{" "}
                                <b className="text-teal-deep">
                                  {t.price_usd !== null
                                    ? `$${t.price_usd}${t.billing_period === "monthly" || t.billing_period === "annual" ? "/mo" : ""}`
                                    : t.price_text.length <= 16
                                      ? t.price_text
                                      : "—"}
                                </b>
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-sub">Unavailable — {row.notes ?? "no accessible pricing page"}</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {row.source_ids.map((sid) => (
                          <Cite key={sid} sid={sid} />
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ))}

      <section className="mt-12">
        <h2 className="text-xs font-bold uppercase tracking-[0.09em] text-sub">
          Sources
        </h2>
        <ol className="card-shadow mt-4 space-y-2 rounded-[14px] bg-white p-5 text-sm">
          {sourceIds.map((sid) => {
            const src = data.sources[String(sid)];
            return (
              <li key={sid} className="flex gap-2.5">
                <span className="w-8 shrink-0 font-bold tabular-nums text-sub/70">
                  [{footnote.get(sid)}]
                </span>
                <span className="min-w-0">
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noreferrer"
                    className="break-all font-medium text-teal hover:underline"
                  >
                    {src.url}
                  </a>{" "}
                  <span className="text-sub">
                    {src.source_type} · retrieved {fmtDate(src.fetched_at)}
                    {!src.ok && " · fetch failed"}
                  </span>
                </span>
              </li>
            );
          })}
        </ol>
      </section>

      <p className="mt-12 border-t border-card-line pt-4 text-xs leading-relaxed text-sub">
        Facts marked <b className="text-teal-deep">Verified</b> come from the
        company&apos;s own website; <b className="text-ink">Analysis</b> is AI
        interpretation of the cited evidence. Missing information is reported as
        unavailable, never inferred. This report link is stable and shareable.
      </p>
    </main>
  );
}
