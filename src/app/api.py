from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess

app = FastAPI(title="Sector Rotation MLOps API (Modular)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_make_command(target: str):
    try:
        result = subprocess.run(
            ["make", target],
            capture_output=True,
            text=True,
            check=True
        )
        return {
            "status": "success",
            "step": target,
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "step": target,
            "output": e.stdout + "\n" + e.stderr
        }

@app.post("/run/ingest")
def step_ingest():
    return run_make_command("ingest")

@app.post("/run/features")
def step_features():
    return run_make_command("features")

@app.post("/run/train")
def step_train():
    return run_make_command("train")

@app.post("/run/signals")
def step_signals():
    return run_make_command("signals")

@app.post("/run/backtest")
def step_backtest():
    return run_make_command("backtest")

@app.post("/run/all")
def step_all():
    return run_make_command("run_all")