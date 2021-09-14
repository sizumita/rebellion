from __future__ import annotations
from typing import TypedDict
from typing import Optional, Literal

from ..snowflake import Snowflake


Status = Literal["idle", "dnd", "online", "offline"]
Types = Literal[0, 1, 2, 3, 4, 5]

class Secrets(TypedDict, total=False):
    join: str
    spectate: str
    match: str


class Button(TypedDict):
    label: str
    url: str


class Timestamps(TypedDict, total=False):
    start: int
    end: int


class Party(TypedDict, total=False):
    id: str
    size: list[int]


class EmojiOptional(TypedDict, total=False):
    id: Snowflake
    animated: bool


class Emoji(EmojiOptional):
    name: str


class Assets(TypedDict, total=False):
    large_image: str
    large_text: str
    small_image: str
    small_text: str


class BotActivityOptional(TypedDict, total=False):
    url: Optional[str]


class BotActivity(BotActivityOptional):
    name: str
    type: Types


class BaseActivity(BotActivity):
    created_at: int


class Activity(BaseActivity, total=False):
    state: Optional[str]
    details: Optional[str]
    timestamps: Timestamps
    assets: Assets
    party: Party
    application_id: Snowflake
    flags: int
    emoji: Optional[Emoji]
    secrets: Secrets
    session_id: Optional[str]
    instance: bool
    buttons: list[Button]
