from __future__ import annotations
import asyncio
import concurrent.futures
import json
import logging
import threading
import traceback
from typing import Optional, Any
import zlib
import time
import sys

from aiohttp import ClientWebSocketResponse, WSMsgType, WSMessage

from rebellion.types.gateway.client import OpCode, Payload
from .handler import EventHandler
from .intents import Intents

logger = logging.getLogger(__name__)


class KeepAlive(threading.Thread):
    def __init__(
            self,
            ws: 'WebsocketClient',
            interval: int,
            shard_id: Optional[int] = None,
            *args: tuple[Any],
            **kwargs: dict[str, Any]):
        self.ws = ws
        self.interval = interval
        self.shard_id = shard_id
        threading.Thread.__init__(self, *args, **kwargs)
        self.main_thread_id = self.ws.thread_id
        self._stop_event = threading.Event()
        self._last_ack = time.perf_counter()
        self._last_send = time.perf_counter()
        self._last_recv = time.perf_counter()
        self.latency = float('inf')
        self.heartbeat_timeout = ws.timeout

    def timeout(self):
        logger.warning(
            f"Shard ID {self.shard_id} has stopped responding to the gateway. Closing and restarting."
        )
        coro = self.ws.close(4000)
        f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)

        try:
            f.result()
        except Exception:
            logger.exception("An error occurred while stopping the gateway. Ignoring.")
        finally:
            self.stop()

    def run(self) -> None:
        while not self._stop_event.wait(self.interval):
            if self._last_recv + self.heartbeat_timeout < time.perf_counter():
                self.timeout()
                return
            payload = self.get_payload()
            logger.debug(f"Keeping shard ID {self.shard_id} websocket alive with sequence {payload['d']}.")
            coro = self.ws.send_heatbeat(payload)
            f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)
            try:
                total = 0
                while True:
                    try:
                        f.result(10)
                        break
                    except concurrent.futures.TimeoutError:
                        total += 10
                        try:
                            frame = sys._current_frames()[self.main_thread_id]
                        except KeyError:
                            msg = f"Shard ID {self.shard_id} heartbeat blocked for more than {total} seconds."
                        else:
                            stack = "".join(traceback.format_stack(frame))
                            msg = f"Shard ID {self.shard_id} heartbeat blocked for more than {total} seconds.\nLoop thread traceback (most recent call last):\n{stack}"
                        logger.warning(msg)
            except Exception:
                self.stop()
            else:
                self._last_send = time.perf_counter()

    def stop(self):
        self._stop_event.set()

    def get_payload(self):
        return Payload(
            op=OpCode.HEARTBEAT,
            d=self.ws.sequence
        )

    def tick(self):
        self._last_recv = time.perf_counter()

    def ack(self):
        ack_time = time.perf_counter()
        self._last_ack = ack_time
        self.latency = ack_time - self._last_send
        if self.latency > 10:
            logger.warning("Can\'t keep up, shard ID %s websocket is %.1fs behind.", self.shard_id, self.latency)


class WebsocketClient:
    def __init__(
            self,
            socket: ClientWebSocketResponse,
            handler: Optional[EventHandler] = None,
            *,
            loop: asyncio.BaseEventLoop,
            token: str, initial: bool = False,
            session_id: Optional[int] = None, shard_id: Optional[int] = None, shard_count: Optional[int] = None, resume: bool = False) -> None:
        self.socket: ClientWebSocketResponse = socket
        self.loop: asyncio.BaseEventLoop = loop
        self.handler: Optional[EventHandler] = handler

        self.token: str = token
        self.is_initial: bool = initial
        self.shard_id: Optional[int] = shard_id
        self.shard_count: Optional[int] = shard_count
        self.is_resume: bool = resume
        self.timeout: float = 60.0
        self._zlib = zlib.decompressobj()
        self._buffer = bytearray()
        self.session_id = session_id
        self.sequence: Optional[int] = None

        self.keep_alive: Optional[KeepAlive] = None

        self.thread_id = threading.get_ident()

    async def initialize(self, intents: Optional[Intents] = None):
        await self.poll_event()
        await self.identify(intents=intents)

    async def start(self):
        while True:
            await self.poll_event()

    async def close(self, code: int = 4000):
        if self.keep_alive is not None:
            self.keep_alive.stop()
            self.keep_alive = None
        await self.socket.close(code=code)

    async def identify(self, activity=None, status=None, intents: Optional[Intents] = None):
        payload = Payload(
            op=OpCode.IDENTIFY,
            d={
                "token": self.token,
                "properties": {
                    "$os": sys.platform,
                    "$browser": "rebellion",
                    "$device": "rebellion",
                    "$referrer": "",
                    "$referring_domain": ""
                },
                "compress": True,
                "large_threshold": 250,
                'v': 3
            }
        )

        if self.shard_id is not None and self.shard_count is not None:
            payload['d']["shard"] = [self.shard_id, self.shard_count]

        if activity is not None or status is not None:
            payload['d']["presence"] = {
                "status": status,
                "game": activity,
                "since": 0,
                "afk": False
            }

        if intents is not None:
            payload['d']["intents"] = intents.value

        await self.send_json(payload)
        logger.info(f"Shard ID {self.shard_id} has sent IDENTIFY payload.")

    async def send_heatbeat(self, payload: Payload):
        await self.send_json(payload)

    async def send(self, data: str):
        # TODO: Rate limit
        await self.socket.send_str(data)

    async def send_json(self, payload: Payload):
        await self.send(json.dumps(payload, separators=(',', ':'), ensure_ascii=True))

    async def handle_event(self, payload: Payload):
        logger.debug(f"handle event: {payload.get('d')}")
        event = payload.get('t')
        if self.handler is not None:
            await self.handler.handle(event, payload.get('d'))

    async def received_message(self, payload: Payload):
        logger.debug(f"Shard ID {self.shard_id}: WebSocket Event: {payload}")
        op = payload["op"]
        data = payload.get('d')
        seq = payload.get('s')
        if seq is not None:
            self.sequence = seq

        if self.keep_alive is not None:
            self.keep_alive.tick()

        if op == OpCode.DISPATCH:
            await self.handle_event(data)
        elif op == OpCode.HEARTBEAT_ACK:
            if self.keep_alive is not None:
                self.keep_alive.ack()
        elif op == OpCode.HEARTBEAT:
            if self.keep_alive is not None:
                beat = self.keep_alive.get_payload()
                await self.send_json(beat)
        elif op == OpCode.HELLO:
            interval = data["heartbeat_interval"] / 1000.0
            self.keep_alive = KeepAlive(self, interval, self.shard_id)
            await self.send_json(self.keep_alive.get_payload())
            self.keep_alive.start()
        elif op == OpCode.INVALIDATE_SESSION:
            if data is True:
                await self.close()
                raise Exception(f"Reconnect WebSocket: {self.shard_id}")
            self.sequence = None
            self.session_id = None
            logger.info(f"Shard ID {self.shard_id} session has been invalidated.")
            await self.close(code=1000)
            raise Exception(f"Reconnect WebSocket: {self.shard_id}, resume: {False}")
        else:
            logger.warning('Unknown OP code %s.', op)

    async def received_binary_message(self, message: WSMessage):
        raw: bytes = message.data

        self._buffer.extend(raw)
        if len(raw) < 4 or raw[-4:] != b"\x00\x00\xff\xff":
            return
        data = self._zlib.decompress(self._buffer).decode("utf-8")
        self._buffer = bytearray()
        await self.received_message(json.loads(data))

    async def poll_event(self) -> None:
        message = await self.socket.receive(timeout=self.timeout)
        if message.type is WSMsgType.TEXT:
            await self.received_message(message.data)
        elif message.type is WSMsgType.BINARY:
            await self.received_binary_message(message)
        elif message.type is WSMsgType.ERROR:
            raise message.data
        elif message.type in (WSMsgType.CLOSED, WSMsgType.CLOSING, WSMsgType.CLOSE):
            raise Exception("websocket closed")




