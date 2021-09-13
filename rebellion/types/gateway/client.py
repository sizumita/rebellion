from __future__ import annotations
from enum import IntEnum
from typing import TypedDict, Optional


class OpCode(IntEnum):
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE = 3
    VOICE_STATE = 4
    VOICE_PING = 5
    RESUME = 6
    RECONNECT = 7
    REQUEST_MEMBERS = 8
    INVALIDATE_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11
    GUILD_SYNC = 12


class Payload(TypedDict, total=False):
    # https://discord.com/developers/docs/topics/gateway#payloads-gateway-payload-structure
    op: OpCode
    d: Optional[dict]
    s: Optional[int]
    t: Optional[str]
