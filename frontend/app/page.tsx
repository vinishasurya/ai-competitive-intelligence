"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Health = { status: string; service: string; version: string };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((res) => res.json())
      .then(setHealth)
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-bold">AI Competitive Intelligence</h1>
      <p className="text-gray-500">
        Enter a product URL, get an evidence-backed competitive report.
      </p>
      <div className="rounded-lg border p-4 font-mono text-sm">
        {health && (
          <span className="text-green-600">
            backend: {health.service} v{health.version} — {health.status}
          </span>
        )}
        {error && <span className="text-red-600">backend unreachable: {error}</span>}
        {!health && !error && <span>checking backend…</span>}
      </div>
    </main>
  );
}
