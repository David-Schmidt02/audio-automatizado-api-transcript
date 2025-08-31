from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import random
import uvicorn

app = FastAPI()

def generar_texto_aleatorio():
    palabras = [
        "hola", "mundo", "transcripción", "audio", "prueba", "cliente", "websocket",
        "python", "streaming", "canal", "automatizado", "mensaje", "aleatorio", "ejemplo",
        "funciona", "flujo", "simulación", "texto", "palabra", "frase", "segmento", "tiempo"
    ]
    return " ".join(random.choices(palabras, k=random.randint(20, 40)))

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    texto = generar_texto_aleatorio()
    return JSONResponse(content={
        "transcription": texto
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)