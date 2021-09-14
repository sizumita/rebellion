from __future__ import annotations
from enum import Enum


class IntentValue(Enum):
    GUILDS = 1 << 0
    MEMBERS = 1 << 1
    BANS = 1 << 2
    EMOJI_AND_STICKERS = 1 << 3
    GUILD_INTEGRATIONS = 1 << 4
    GUILD_WEBHOOKS = 1 << 5
    GUILD_INVITES = 1 << 6
    GUILD_VOICE_STATES = 1 << 7
    GUILD_PRESENCES = 1 << 8
    GUILD_MESSAGES = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
    GUILD_MESSAGE_TYPING = 1 << 11
    DIRECT_MESSAGES = 1 << 12
    DIRECT_MESSAGE_REACTIONS = 1 << 12
    DIRECT_MESSAGE_TYPING = 1 << 14

    @staticmethod
    def max() -> int:
        """Returns max value of Intent"""
        return max(*[x.value for x in IntentValue._member_map_.values()])


class Intents:
    def __init__(self, *args: IntentValue):
        self.value = 0
        for value in args:
            self.add(value)

    @classmethod
    def all(cls) -> Intents:
        bits = IntentValue.max().bit_length()
        value = (1 << bits) - 1
        intents = cls()
        intents.value = value
        return intents

    @classmethod
    def none(cls) -> Intents:
        intents = cls()
        intents.value = 0
        return intents

    @classmethod
    def default(cls) -> Intents:
        return cls.all() - IntentValue.GUILD_PRESENCES - IntentValue.MEMBERS

    def add(self, value: IntentValue) -> Intents:
        self.value |= value.value
        return self

    def remove(self, value: IntentValue) -> Intents:
        self.value &= ~value.value
        return self

    def __sub__(self, other: IntentValue) -> Intents:
        return self.remove(other)

    def __add__(self, other: IntentValue) -> Intents:
        return self.add(other)
