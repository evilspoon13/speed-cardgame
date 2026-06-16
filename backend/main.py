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

ROOM_COUNT = 6
GRACE_SECONDS = 60        # how long a mid-game seat is held for a reconnect
HEARTBEAT_INTERVAL = 25   # seconds between server pings
HEARTBEAT_TIMEOUT = 60    # drop a socket if no pong arrives within this window


class Room:
    """One independent 2-player game."""

    def __init__(self, room_id: int):
        self.id = room_id
        self.game = GameState()
        self.owners: dict[int, str] = {}        # seat (1/2) -> owning client id
        self.sockets: dict[int, WebSocket] = {}  # seat -> live socket (only when connected)
        self.grace: dict[int, asyncio.Task] = {}  # seat -> grace-period timer

    def seat_of(self, client_id: str) -> int | None:
        for seat, cid in self.owners.items():
            if cid == client_id:
                return seat
        return None

    def free_seat(self) -> int | None:
        for seat in (1, 2):
            if seat not in self.owners:
                return seat
        return None

    def is_paused(self) -> bool:
        # Mid-game with a seat owner who is currently disconnected (in grace).
        return self.game.status == "playing" and any(
            s not in self.sockets for s in self.owners
        )


rooms: dict[int, Room] = {i: Room(i) for i in range(1, ROOM_COUNT + 1)}
# Sockets currently viewing the room list (not joined to any room).
browsers: set[WebSocket] = set()
lock = asyncio.Lock()


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


def room_list() -> list[dict]:
    return [
        {"id": r.id, "players": len(r.owners), "status": r.game.status}
        for r in rooms.values()
    ]


async def broadcast_rooms():
    payload = {"type": "rooms", "rooms": room_list()}
    for ws in list(browsers):
        await safe_send(ws, payload)


def state_for_seat(room: Room, seat: int) -> dict:
    if room.game.status == "waiting":
        state = room.game.get_lobby_state(seat)
    else:
        state = room.game.get_state_for_player(seat)
    opp = 2 if seat == 1 else 1
    state["type"] = "game_state"
    state["room"] = room.id
    state["opponentPresent"] = opp in room.owners
    state["opponentConnected"] = opp in room.sockets
    state["paused"] = room.is_paused()
    return state


async def broadcast_room(room: Room):
    for seat, ws in list(room.sockets.items()):
        await safe_send(ws, state_for_seat(room, seat))


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


async def end_game_locked(room: Room, leaving_seat: int):
    """The owner of `leaving_seat` is gone for good. Reset the room to a fresh
    lobby and keep any remaining player waiting for a new opponent. Lock held."""
    room.owners.pop(leaving_seat, None)
    room.sockets.pop(leaving_seat, None)
    task = room.grace.pop(leaving_seat, None)
    if task:
        task.cancel()
    room.game = GameState()
    for _, ws in list(room.sockets.items()):
        await safe_send(ws, {"type": "notice", "message": "Opponent left. Waiting for a new player…"})
    await broadcast_room(room)
    await broadcast_rooms()


async def grace_expire(room: Room, seat: int):
    try:
        await asyncio.sleep(GRACE_SECONDS)
    except asyncio.CancelledError:
        return
    async with lock:
        if seat in room.sockets:  # reconnected in time
            return
        room.grace.pop(seat, None)
        await end_game_locked(room, seat)


async def handle_join(websocket: WebSocket, client_id: str, room_id) -> tuple[Room, int] | None:
    room = rooms.get(room_id)
    if room is None:
        await safe_send(websocket, {"type": "error", "message": "No such room"})
        return None

    old = None
    async with lock:
        browsers.discard(websocket)
        seat = room.seat_of(client_id)
        if seat is None:
            seat = room.free_seat()
        if seat is None:
            # Genuinely full (two other clients own the seats). Send them back to
            # browsing so they can pick another room.
            browsers.add(websocket)
            await safe_send(websocket, {"type": "error", "message": "Game is full"})
            await safe_send(websocket, {"type": "rooms", "rooms": room_list()})
            return None

        old = room.sockets.get(seat)          # set on reconnect / second tab
        grace = room.grace.pop(seat, None)    # resuming -> cancel the grace timer
        if grace:
            grace.cancel()
        room.owners[seat] = client_id
        room.sockets[seat] = websocket

    if old is not None and old is not websocket:
        await safe_send(old, {"type": "taken_over"})
        await close_quietly(old)

    await safe_send(websocket, {"type": "connected", "player": seat, "room": room.id})
    async with lock:
        await broadcast_room(room)
        await broadcast_rooms()
    return (room, seat)


async def handle_game_message(room: Room, seat: int, websocket: WebSocket, msg: dict):
    """Apply an in-room game action. Lock is held by the caller."""
    msg_type = msg.get("type")
    game = room.game

    if room.is_paused() and msg_type in ("play_card", "draw_card", "stuck"):
        await safe_send(websocket, {"type": "error", "message": "Waiting for opponent to reconnect…"})
        return

    if msg_type == "ready":
        if seat == 1:
            game.player1_ready = True
        else:
            game.player2_ready = True
        if game.player1_ready and game.player2_ready:
            game.deal()
        await broadcast_room(room)
        await broadcast_rooms()

    elif msg_type == "play_card":
        error = game.play_card(seat, msg.get("cardIndex", -1), msg.get("target", ""))
        if error:
            await safe_send(websocket, {"type": "error", "message": error})
        else:
            await broadcast_room(room)

    elif msg_type == "draw_card":
        error = game.draw_card(seat)
        if error:
            await safe_send(websocket, {"type": "error", "message": error})
        else:
            await broadcast_room(room)

    elif msg_type == "stuck":
        error = game.declare_stuck(seat)
        if error:
            await safe_send(websocket, {"type": "error", "message": error})
        else:
            await broadcast_room(room)

    elif msg_type == "play_again":
        if seat == 1:
            game.player1_ready = True
            game.player2_ready = False
        else:
            game.player2_ready = True
            game.player1_ready = False
        game.status = "waiting"
        game.winner = None
        await broadcast_room(room)
        await broadcast_rooms()


async def handle_disconnect(websocket: WebSocket, current: tuple[Room, int]):
    room, seat = current
    async with lock:
        if room.sockets.get(seat) is not websocket:
            return  # superseded by a takeover; nothing to clean up
        room.sockets.pop(seat, None)
        if room.game.status == "playing":
            # Mid-game: hold the seat and pause for a reconnect window.
            await broadcast_room(room)
            await broadcast_rooms()
            room.grace[seat] = asyncio.create_task(grace_expire(room, seat))
        else:
            # In the lobby / game over: free the seat immediately.
            await end_game_locked(room, seat)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async with lock:
        browsers.add(websocket)
        await safe_send(websocket, {"type": "rooms", "rooms": room_list()})

    current: tuple[Room, int] | None = None
    hb = {"last_pong": time.monotonic()}
    heartbeat_task = asyncio.create_task(heartbeat(websocket, hb))

    try:
        while True:
            msg = json.loads(await websocket.receive_text())
            msg_type = msg.get("type")

            if msg_type == "pong":
                hb["last_pong"] = time.monotonic()
                continue

            if msg_type == "list":
                async with lock:
                    browsers.add(websocket)
                    await safe_send(websocket, {"type": "rooms", "rooms": room_list()})
                continue

            if msg_type == "join":
                client_id = msg.get("clientId")
                if not client_id or msg.get("room") is None:
                    await safe_send(websocket, {"type": "error", "message": "Bad join"})
                    continue
                result = await handle_join(websocket, client_id, msg.get("room"))
                if result:
                    current = result
                continue

            if msg_type == "leave":
                if current:
                    room, seat = current
                    async with lock:
                        if room.sockets.get(seat) is websocket:
                            room.sockets.pop(seat, None)
                            await end_game_locked(room, seat)
                    current = None
                async with lock:
                    browsers.add(websocket)
                    await safe_send(websocket, {"type": "rooms", "rooms": room_list()})
                continue

            # In-room game actions.
            if not current:
                continue
            room, seat = current
            async with lock:
                if room.sockets.get(seat) is not websocket:
                    continue  # superseded
                await handle_game_message(room, seat, websocket, msg)

    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        heartbeat_task.cancel()
        async with lock:
            browsers.discard(websocket)
        if current:
            await handle_disconnect(websocket, current)
