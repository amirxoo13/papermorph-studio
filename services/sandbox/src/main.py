from __future__ import annotations
import os
import sys
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Papermorph Network-Isolated Python Sandbox", version="1.0.0")

class SandboxRequest(BaseModel):
    code: str = Field(..., max_length=20000)
    timeout_sec: float = Field(default=5.0, ge=0.5, le=15.0)

class SandboxResponse(BaseModel):
    returncode: int
    stdout: str
    stderr: str
    network_blocked: bool = True

NETWORK_BLOCK_PRELUDE = """
import socket as _socket
import urllib.request as _urllib_req

class _NetworkEgressBlockedError(PermissionError):
    pass

def _blocked_socket(*args, **kwargs):
    raise _NetworkEgressBlockedError("Network egress is strictly prohibited inside pm-sandbox")

_socket.socket = _blocked_socket
_socket.create_connection = _blocked_socket
_socket.getaddrinfo = _blocked_socket
"""

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "pm-sandbox", "network_isolated": True}

@app.post("/execute", response_model=SandboxResponse)
def execute_code(req: SandboxRequest):
    with tempfile.TemporaryDirectory(prefix="pm_sbx_") as tmpdir:
        script_path = os.path.join(tmpdir, "script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(NETWORK_BLOCK_PRELUDE + "\n" + req.code)

        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": tmpdir,
            "PYTHONDONTWRITEBYTECODE": "1",
            "NO_PROXY": "*",
            "http_proxy": "http://127.0.0.1:0",
            "https_proxy": "http://127.0.0.1:0",
        }
        try:
            proc = subprocess.run(
                [sys.executable, "-I", script_path],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=req.timeout_sec,
            )
            return SandboxResponse(
                returncode=proc.returncode,
                stdout=proc.stdout[:10000],
                stderr=proc.stderr[:10000],
                network_blocked=True,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=408, detail="Sandbox execution timed out")
