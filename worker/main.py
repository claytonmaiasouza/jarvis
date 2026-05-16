import os
import json
import asyncio
import subprocess
import psutil
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

app = FastAPI()
security = HTTPBearer()

API_KEY = os.environ["WORKER_API_KEY"]

PROJECTS = {
    "agendamento":         "/opt/agendamento",
    "bot-restaurante":     "/opt/bot-restaurante",
    "farmacia-santaclara": "/opt/farmacia-santaclara",
    "fintrack":            "/opt/fintrack",
    "jarvis":              "/opt/jarvis",
}


def auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


class DeployRequest(BaseModel):
    project: str


class ClaudeRequest(BaseModel):
    project: str
    prompt: str


def run(cmd: str, cwd: str) -> str:
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True, timeout=300
    )
    return result.stdout + result.stderr


@app.get("/status")
def status(_=Depends(auth)):
    result = {}
    for name, path in PROJECTS.items():
        out = run("docker compose ps --format json", path)
        containers = []
        for line in out.strip().splitlines():
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        result[name] = containers
    return result


@app.get("/metrics")
def metrics(_=Depends(auth)):
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_pct": round(psutil.cpu_percent(interval=1), 1),
        "mem_used_mb": mem.used // 1024 // 1024,
        "mem_total_mb": mem.total // 1024 // 1024,
        "mem_pct": round(mem.percent, 1),
        "disk_used_gb": round(disk.used / 1024 ** 3, 1),
        "disk_total_gb": round(disk.total / 1024 ** 3, 1),
        "disk_pct": round(disk.percent, 1),
    }


@app.post("/deploy")
def deploy(req: DeployRequest, _=Depends(auth)):
    if req.project not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")
    path = PROJECTS[req.project]
    out = run("git pull", path)
    out += run("docker compose up -d --build", path)
    return {"output": out}


@app.post("/deploy/stream/{project}")
async def deploy_stream(project: str, _=Depends(auth)):
    if project not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")
    path = PROJECTS[project]

    async def generate():
        for cmd in ["git pull", "docker compose up -d --build"]:
            yield f"data: $ {cmd}\n\n"
            proc = await asyncio.create_subprocess_shell(
                cmd, cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            async for line in proc.stdout:
                yield f"data: {line.decode(errors='replace').rstrip()}\n\n"
            await proc.wait()
        yield "data: ✓ DONE\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/logs/stream/{container}")
async def logs_stream(container: str, lines: int = 200, _=Depends(auth)):
    async def generate():
        proc = await asyncio.create_subprocess_shell(
            f"docker logs --tail {lines} -f {container} 2>&1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            async for line in proc.stdout:
                yield f"data: {line.decode(errors='replace').rstrip()}\n\n"
        finally:
            try:
                proc.kill()
            except Exception:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/claude")
def claude(req: ClaudeRequest, _=Depends(auth)):
    if req.project not in PROJECTS:
        raise HTTPException(status_code=404, detail="Project not found")
    path = PROJECTS[req.project]
    out = run(f'claude --print "{req.prompt}"', path)
    return {"output": out}


@app.websocket("/deploy/ws")
async def deploy_ws(ws, project: str, token: str):
    from fastapi import WebSocket
    if token != API_KEY:
        await ws.close(code=1008)
        return
    if project not in PROJECTS:
        await ws.close(code=1003)
        return

    await ws.accept()
    path = PROJECTS[project]

    for cmd in ["git pull", "docker compose up -d --build"]:
        await ws.send_text(f"$ {cmd}\n")
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        async for line in proc.stdout:
            await ws.send_text(line.decode())
        await proc.wait()

    await ws.send_text("DONE\n")
    await ws.close()
