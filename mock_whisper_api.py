# FastAPI + WebSocket
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import random
import asyncio

from config import MOCK_API_HOST, MOCK_API_PORT

app = FastAPI()
connected = set()

def generar_texto_aleatorio():
    palabras = ["hola","mundo","transcripción","audio","prueba","cliente","websocket",
                "python","streaming","canal","automatizado","mensaje","aleatorio","ejemplo",
                "funciona","flujo","simulación","texto","palabra","frase","segmento","tiempo"]
    return " ".join(random.choices(palabras, k=random.randint(20,40)))

@app.post("/transcribe")
async def transcribe():
    texto = generar_texto_aleatorio()
    # Enviar a todos los websockets conectados
    for ws in connected.copy():
        try:
            await ws.send_json({"client_id":"servidor","transcription":texto})
        except:
            connected.discard(ws)
    return JSONResponse({"transcription": texto})

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected.add(ws)
    try:
        while True:
            await ws.receive_text()
    except:
        pass
    finally:
        connected.discard(ws)


# Permite ejecutar el servidor directamente con: python3 mock_whisper_api.py
if __name__ == "__main__":
    import uvicorn
    print(f"Iniciando mock_whisper_api en {MOCK_API_HOST} ...")
    uvicorn.run("mock_whisper_api:app", host=MOCK_API_HOST, port=MOCK_API_PORT, reload=True)
