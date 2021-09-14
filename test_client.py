import asyncio
import datetime

import discord.http
import os
from rebellion.gateway.client import WebsocketClient
from rebellion.gateway.handler import EventHandler
from rebellion.gateway.intents import Intents, IntentValue
from rebellion.types.gateway.activity import Activity
import logging

logging.basicConfig(level=logging.DEBUG)


class Handler(EventHandler):
    async def handle(self, ws: WebsocketClient, event: str, data: dict):
        print(event)
        if event == "READY":
            print("ready!")
            await ws.change_presence(activity=Activity(type=0, name="test", created_at=0))


async def main():
    http = discord.http.HTTPClient()
    print(await http.static_login(os.environ["DISCORD_BOT_TOKEN"], bot=True))
    url = await http.get_bot_gateway()
    print(f"{url=}")
    ws = await http.ws_connect(url[1])
    print(ws)
    websocket = WebsocketClient(ws, handler=Handler(), loop=http.loop, token=os.environ["DISCORD_BOT_TOKEN"], initial=True)
    await websocket.initialize(Intents.default() - IntentValue.GUILD_MESSAGE_TYPING - IntentValue.GUILDS)
    await websocket.start()


asyncio.run(main())
