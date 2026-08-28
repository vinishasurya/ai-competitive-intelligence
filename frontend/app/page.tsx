"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STAGES = [
  { key: "profiling", label: "Profiling the product" },
  { key: "discovery", label: "Discovering & verifying competitors" },
  { key: "evidence", label: "Collecting evidence" },
  { key: "report", label: "Writing the report" },
] as const;

type Job = {
  status: "queued" | "running" | "completed" | "failed";
  stage: string;
  detail: string;
  run_id: number | null;
  error: string | null;
};

export default function Home() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const startedAt = useRef<number>(0);

  async function start(e?: React.FormEvent) {
    e?.preventDefault();
    if (!url.trim()) return;
    setError(null);
    setJob(null);
    try {
      const res = await fetch(`${API}/api/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      startedAt.current = Date.now();
      setJobId(data.job_id);
    } catch {
      setError("Could not reach the research backend. Is it running?");
    }
  }

  useEffect(() => {
    if (!jobId) return;
    const poll = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/runs/${jobId}`);
        const data: Job = await res.json();
        setJob(data);
        setElapsed(Math.round((Date.now() - startedAt.current) / 1000));
        if (data.status === "completed" && data.run_id) {
          clearInterval(poll);
          router.push(`/report/${data.run_id}`);
        }
        if (data.status === "failed") clearInterval(poll);
      } catch {
        /* transient poll failure — keep trying */
      }
    }, 2000);
    return () => clearInterval(poll);
  }, [jobId, router]);

  const running = job && (job.status === "running" || job.status === "queued");
  const activeIdx = STAGES.findIndex((s) => s.key === job?.stage);

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-teal">
        Evidence-backed competitive research
      </p>
      <h1 className="mt-3 text-[2.6rem] leading-[1.05] font-bold tracking-[-0.03em] text-ink">
        Know the competition.
        <br />
        <span className="text-sub font-medium">Verify every claim.</span>
      </h1>
      <p className="mt-5 max-w-[52ch] leading-relaxed text-sub">
        Enter a software product&apos;s URL. Get a competitive report — verified
        rivals, features, and pricing — where every fact links to a retrievable
        public source with its retrieval date.
      </p>

      <form onSubmit={start} className="mt-9 flex gap-3">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="e.g. linear.app"
          disabled={!!running}
          className="card-shadow flex-1 rounded-[14px] border border-card-line bg-white px-5 py-3.5 text-lg text-ink outline-none transition placeholder:text-sub/60 focus:border-teal disabled:bg-row-line"
        />
        <button
          type="submit"
          disabled={!!running}
          className="rounded-[14px] bg-ink px-7 py-3.5 text-lg font-semibold text-white transition hover:bg-ink-soft disabled:bg-sub/40"
        >
          {running ? "Researching…" : "Research"}
        </button>
      </form>

      {error && <p className="mt-4 text-red-600">{error}</p>}

      {job?.status === "failed" && (
        <div className="card-shadow mt-7 rounded-[14px] border border-red-200 bg-white p-5">
          <p className="font-semibold text-red-700">Run failed</p>
          <p className="mt-1 text-sm leading-relaxed text-sub">{job.error}</p>
          <button
            onClick={() => start()}
            className="mt-4 rounded-[10px] bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-ink-soft"
          >
            Retry
          </button>
        </div>
      )}

      {running && (
        <div className="card-shadow mt-9 rounded-[14px] bg-white p-6">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-[0.08em] text-sub">
              Research in progress
            </p>
            <p className="font-mono text-sm tabular-nums text-teal">{elapsed}s</p>
          </div>
          <ol className="mt-5 space-y-3.5">
            {STAGES.map((stage, i) => {
              const state =
                i < activeIdx ? "done" : i === activeIdx ? "active" : "pending";
              return (
                <li key={stage.key} className="flex items-center gap-3">
                  <span
                    className={
                      state === "done"
                        ? "h-2.5 w-2.5 rounded-full bg-teal"
                        : state === "active"
                          ? "h-2.5 w-2.5 animate-pulse rounded-full bg-mint"
                          : "h-2.5 w-2.5 rounded-full bg-row-line"
                    }
                  />
                  <span
                    className={
                      state === "pending"
                        ? "text-sub/70"
                        : "font-medium text-ink"
                    }
                  >
                    {stage.label}
                  </span>
                  {state === "active" && (
                    <span className="text-sm text-sub">{job?.detail}</span>
                  )}
                </li>
              );
            })}
          </ol>
          <p className="mt-5 text-sm text-sub/80">
            A full report typically takes 2–4 minutes.
          </p>
        </div>
      )}
    </main>
  );
}
