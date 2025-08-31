import asyncio
import websockets
import json

# Lista de websockets conectados (frontends)
connected = set()

async def handler(websocket, path):
    # Registrar nuevo cliente
    connected.add(websocket)
    try:
        async for message in websocket:
            # Broadcast a todos los conectados (incluyendo frontends)
            for ws in connected:
                if ws.open:
                    await ws.send(message)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected.remove(websocket)

if __name__ == "__main__":
    start_server = websockets.serve(handler, "0.0.0.0", 8765)
    print("Servidor WebSocket escuchando en ws://0.0.0.0:8765")
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()