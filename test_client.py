import asyncio

import discord.http
import os
from rebellion.gateway.client import Websocket
from rebellion.gateway.handler import EventHandler
import logging

logging.basicConfig(level=logging.DEBUG)


async def main():
    http = discord.http.HTTPClient()
    print(await http.static_login(os.environ["DISCORD_BOT_TOKEN"], bot=True))
    url = await http.get_bot_gateway()
    print(f"{url=}")
    ws = await http.ws_connect(url[1])
    print(ws)
    websocket = Websocket(ws, EventHandler(), loop=http.loop, token=os.environ["DISCORD_BOT_TOKEN"], initial=True)
    await websocket.poll_event()
    await websocket.identify()
    while True:
        await websocket.poll_event()


asyncio.run(main())
