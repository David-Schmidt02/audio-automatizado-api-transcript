import asyncio
import websockets
import json


# ===============================
# MEJORA: Broadcast concurrente y logs de error para robustez y trazabilidad
# Ahora los mensajes se envían a todos los clientes en paralelo y se loguean los errores de envío.
# ===============================
connected = set()

# Handler compatible con websockets >=11.x (solo recibe websocket)
async def handler(websocket):
    connected.add(websocket)
    # Enviar mensaje de bienvenida al nuevo cliente
    bienvenida = {
        "client_id": "servidor",
        "transcription": "✅ Conectado al WebSocket correctamente."
    }
    try:
        await websocket.send(json.dumps(bienvenida))
        async for message in websocket:
            try:
                data = json.loads(message)
                channel_name = data.get("channel_name")
                client_id = data.get("client_id")
                transcription = data.get("transcription")
                # Imprimir el nombre del canal si está disponible, si no el client_id
                if channel_name:
                    print(f"Mensaje recibido de canal '{channel_name}': {transcription}")
                else:
                    print(f"Mensaje recibido de cliente {client_id}: {transcription}")
            except Exception:
                print(f"Mensaje recibido (no JSON): {message}")
            # Broadcast concurrente a todos los conectados
            to_remove = set()
            send_tasks = []
            for ws in connected.copy():
                send_tasks.append(_send_with_log(ws, message, to_remove))
            await asyncio.gather(*send_tasks)
            connected.difference_update(to_remove)
    except Exception as e:
        print(f"[ERROR handler] {e}")
    finally:
        connected.discard(websocket)

# Enviar mensaje y loguear error si ocurre
async def _send_with_log(ws, message, to_remove):
    try:
        await ws.send(message)
    except Exception as e:
        print(f"[ERROR envío a cliente] {e}")
        to_remove.add(ws)

if __name__ == "__main__":

    async def main():
        # Aumentar el timeout de ping y el intervalo para tolerancia
        server = await websockets.serve(
            handler,
            "0.0.0.0", 8765,
        )
        print("Servidor WebSocket escuchando en ws://0.0.0.0:8765")
        await server.wait_closed()

    asyncio.run(main())