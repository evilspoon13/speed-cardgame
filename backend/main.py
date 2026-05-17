import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState

from game import GameState

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

game = GameState()
lock = asyncio.Lock()
connections: dict[int, WebSocket] = {}


async def safe_send(ws: WebSocket, data: dict):
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(data)
    except Exception:
        pass


async def broadcast_state():
    for player, ws in list(connections.items()):
        if game.status == "waiting":
            state = game.get_lobby_state()
        else:
            state = game.get_state_for_player(player)
        state["type"] = "game_state"
        await safe_send(ws, state)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async with lock:
        if len(connections) >= 2:
            try:
                await websocket.send_json({"type": "error", "message": "Game is full"})
                await websocket.close()
            except Exception:
                pass
            return

        player = 1 if 1 not in connections else 2
        connections[player] = websocket

    await safe_send(websocket, {"type": "connected", "player": player})

    async with lock:
        await broadcast_state()

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")

            async with lock:
                if msg_type == "ready":
                    if player == 1:
                        game.player1_ready = True
                    else:
                        game.player2_ready = True

                    if game.player1_ready and game.player2_ready:
                        game.deal()

                    await broadcast_state()

                elif msg_type == "play_card":
                    error = game.play_card(
                        player,
                        msg.get("cardIndex", -1),
                        msg.get("target", ""),
                    )
                    if error:
                        await safe_send(websocket, {"type": "error", "message": error})
                    else:
                        await broadcast_state()

                elif msg_type == "draw_card":
                    error = game.draw_card(player)
                    if error:
                        await safe_send(websocket, {"type": "error", "message": error})
                    else:
                        await broadcast_state()

                elif msg_type == "stuck":
                    error = game.declare_stuck(player)
                    if error:
                        await safe_send(websocket, {"type": "error", "message": error})
                    else:
                        await broadcast_state()

                elif msg_type == "play_again":
                    if player == 1:
                        game.player1_ready = True
                        game.player2_ready = False
                    else:
                        game.player2_ready = True
                        game.player1_ready = False

                    game.status = "waiting"
                    game.winner = None
                    await broadcast_state()

    except (WebSocketDisconnect, RuntimeError):
        async with lock:
            connections.pop(player, None)
            reset_game()
            for _, ws in list(connections.items()):
                await safe_send(ws, {"type": "opponent_disconnected"})


def reset_game():
    global game
    game = GameState()
