import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from runner import run_safely

app = FastAPI(title="DataPilot Python Sandbox", docs_url=None, redoc_url=None)


class RunRequest(BaseModel):
    dataset_file: str = Field(min_length=1, max_length=300)
    code: str = Field(min_length=1, max_length=12000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run(body: RunRequest):
    try:
        return run_safely(body.dataset_file, body.code, int(os.getenv("EXEC_TIMEOUT_SECONDS", "8")))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
