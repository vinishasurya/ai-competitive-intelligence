from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Competitive Intelligence API", version="0.1.0")

# The Next.js dev server runs on a different port, so the browser blocks
# cross-origin requests unless the API explicitly allows them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "ci-backend", "version": "0.1.0"}
