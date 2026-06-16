import asyncio
import json
import time

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

# Player slot (1/2) -> owning stable client id. A client keeps its slot across
# reconnects/new tabs, which is what lets a fresh tab take over rather than steal
# the opponent's slot.
slots: dict[int, str] = {}
# Player slot (1/2) -> current live socket for that slot.
sockets: dict[int, WebSocket] = {}

HEARTBEAT_INTERVAL = 25  # seconds between server pings
HEARTBEAT_TIMEOUT = 60   # drop a socket if no pong arrives within this window


async def safe_send(ws: WebSocket, data: dict):
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(data)
    except Exception:
        pass


async def close_quietly(ws: WebSocket):
    try:
        await ws.close()
    except Exception:
        pass


async def broadcast_state():
    for player, ws in list(sockets.items()):
        if game.status == "waiting":
            state = game.get_lobby_state(player)
        else:
            state = game.get_state_for_player(player)
        state["type"] = "game_state"
        await safe_send(ws, state)


def reset_game():
    global game
    game = GameState()


def find_slot(client_id: str) -> int | None:
    """Existing slot for this client, else the lowest free slot, else None (full)."""
    for slot, cid in slots.items():
        if cid == client_id:
            return slot
    for slot in (1, 2):
        if slot not in slots:
            return slot
    return None


async def heartbeat(websocket: WebSocket, hb: dict):
    """Ping periodically; close the socket if it stops answering."""
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if time.monotonic() - hb["last_pong"] > HEARTBEAT_TIMEOUT:
                await close_quietly(websocket)
                return
            await safe_send(websocket, {"type": "ping"})
    except asyncio.CancelledError:
        pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Require an explicit join handshake carrying a stable client id before
    # assigning a player slot. No identity -> no slot.
    try:
        msg = json.loads(await websocket.receive_text())
    except Exception:
        await close_quietly(websocket)
        return

    client_id = msg.get("clientId")
    if msg.get("type") != "join" or not client_id:
        await safe_send(websocket, {"type": "error", "message": "Expected join"})
        await close_quietly(websocket)
        return

    old_ws = None
    async with lock:
        slot = find_slot(client_id)
        if slot is None:
            await safe_send(websocket, {"type": "error", "message": "Game is full"})
            await close_quietly(websocket)
            return

        old_ws = sockets.get(slot)  # set only when this client is taking over its slot
        slots[slot] = client_id
        sockets[slot] = websocket

    # Retire the old socket for this slot (reconnect / second tab). Its reader will
    # see the close, but the `sockets.get(slot) is websocket` guard below stops it
    # from tearing down the live game.
    if old_ws is not None:
        await safe_send(old_ws, {"type": "taken_over"})
        await close_quietly(old_ws)

    await safe_send(websocket, {"type": "connected", "player": slot})
    async with lock:
        await broadcast_state()

    hb = {"last_pong": time.monotonic()}
    heartbeat_task = asyncio.create_task(heartbeat(websocket, hb))

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")

            if msg_type == "pong":
                hb["last_pong"] = time.monotonic()
                continue

            async with lock:
                # Ignore actions from a socket that has been superseded by a takeover.
                if sockets.get(slot) is not websocket:
                    continue

                if msg_type == "ready":
                    if slot == 1:
                        game.player1_ready = True
                    else:
                        game.player2_ready = True

                    if game.player1_ready and game.player2_ready:
                        game.deal()

                    await broadcast_state()

                elif msg_type == "play_card":
                    error = game.play_card(
                        slot,
                        msg.get("cardIndex", -1),
                        msg.get("target", ""),
                    )
                    if error:
                        await safe_send(websocket, {"type": "error", "message": error})
                    else:
                        await broadcast_state()

                elif msg_type == "draw_card":
                    error = game.draw_card(slot)
                    if error:
                        await safe_send(websocket, {"type": "error", "message": error})
                    else:
                        await broadcast_state()

                elif msg_type == "stuck":
                    error = game.declare_stuck(slot)
                    if error:
                        await safe_send(websocket, {"type": "error", "message": error})
                    else:
                        await broadcast_state()

                elif msg_type == "play_again":
                    if slot == 1:
                        game.player1_ready = True
                        game.player2_ready = False
                    else:
                        game.player2_ready = True
                        game.player1_ready = False

                    game.status = "waiting"
                    game.winner = None
                    await broadcast_state()

    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        heartbeat_task.cancel()
        async with lock:
            # Only tear down if this socket still owns the slot. A taken-over old
            # socket closing here must NOT reset the live game.
            if sockets.get(slot) is websocket:
                sockets.pop(slot, None)
                slots.pop(slot, None)
                reset_game()
                for _, ws in list(sockets.items()):
                    await safe_send(ws, {"type": "opponent_disconnected"})
