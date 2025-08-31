from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import threading

app = FastAPI()
clientes = {}

class ClienteParams(BaseModel):
    url: str
    navegador: str = "Chromium"
    formato: str = "ffmpeg"

@app.post("/cliente")
def levantar_cliente(params: ClienteParams):
    # Generar un ID único (puedes usar uuid4 si prefieres)
    import uuid
    cliente_id = str(uuid.uuid4())
    cmd = [
        "python3", "client/main.py",
        params.url, params.navegador, params.formato
    ]
    # Lanzar el cliente en un hilo para no bloquear
    proc = subprocess.Popen(cmd)
    clientes[cliente_id] = proc
    return {"id": cliente_id, "pid": proc.pid}

@app.delete("/cliente/{cliente_id}")
def frenar_cliente(cliente_id: str):
    proc = clientes.get(cliente_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    proc.terminate()
    proc.wait()
    del clientes[cliente_id]
    return {"status": "frenado", "id": cliente_id}

@app.get("/cliente")
def listar_clientes():
    return [{"id": cid, "pid": proc.pid} for cid, proc in clientes.items()]