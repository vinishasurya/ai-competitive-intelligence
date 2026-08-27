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
      <h1 className="text-4xl font-bold tracking-tight">
        AI Competitive Intelligence
      </h1>
      <p className="mt-3 text-lg text-gray-500">
        Enter a software product&apos;s URL. Get an evidence-backed competitive
        report — every claim cited to a retrievable public source.
      </p>

      <form onSubmit={start} className="mt-8 flex gap-3">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="e.g. linear.app"
          disabled={!!running}
          className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-lg outline-none focus:border-blue-500 disabled:bg-gray-100"
        />
        <button
          type="submit"
          disabled={!!running}
          className="rounded-lg bg-blue-600 px-6 py-3 text-lg font-semibold text-white hover:bg-blue-700 disabled:bg-gray-300"
        >
          {running ? "Researching…" : "Research"}
        </button>
      </form>

      {error && <p className="mt-4 text-red-600">{error}</p>}

      {job?.status === "failed" && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="font-semibold text-red-700">Run failed</p>
          <p className="mt-1 text-sm text-red-600">{job.error}</p>
          <button
            onClick={() => start()}
            className="mt-3 rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      )}

      {running && (
        <div className="mt-8 rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <p className="font-semibold">Research in progress</p>
            <p className="font-mono text-sm text-gray-400">{elapsed}s</p>
          </div>
          <ol className="mt-4 space-y-3">
            {STAGES.map((stage, i) => {
              const state =
                i < activeIdx ? "done" : i === activeIdx ? "active" : "pending";
              return (
                <li key={stage.key} className="flex items-center gap-3">
                  <span
                    className={
                      state === "done"
                        ? "h-2.5 w-2.5 rounded-full bg-emerald-500"
                        : state === "active"
                          ? "h-2.5 w-2.5 animate-pulse rounded-full bg-blue-500"
                          : "h-2.5 w-2.5 rounded-full bg-gray-200"
                    }
                  />
                  <span
                    className={
                      state === "pending" ? "text-gray-400" : "text-gray-900"
                    }
                  >
                    {stage.label}
                  </span>
                  {state === "active" && (
                    <span className="text-sm text-gray-400">{job?.detail}</span>
                  )}
                </li>
              );
            })}
          </ol>
          <p className="mt-4 text-sm text-gray-400">
            A full report typically takes 2–4 minutes.
          </p>
        </div>
      )}
    </main>
  );
}
