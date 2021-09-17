# -*- coding: utf-8 -*-
"""
MIT License

Copyright (c) 2021 Dinesh Pinto

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import logging
import operator
import os
from urllib import parse

import discord
import numpy as np

from config import DISCORD_TOKEN, DISCORD_GUILD_CBD, DISCORD_GUILD_NAME
from src.nft_analytics import NFTAnalytics

logging.basicConfig(filename="logfile.log", filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

cbd = NFTAnalytics("0xe12EDaab53023c75473a5A011bdB729eE73545e8")
DATA_FOLDER = os.path.join("data")

database_path = os.path.join(DATA_FOLDER, "data.json")
asset_data = cbd.load_json(filename=database_path)
total_traits_count, rarities = cbd.get_total_unique_trait_count_and_rarities(asset_data)

last_mtime = os.path.getmtime(database_path)
client = discord.Client()


def get_asset_id_from_url(url: str) -> str:
    split_url = parse.urlsplit(url)
    asset_id = split_url.path.split("/")[-1]
    return asset_id


def _format_mvt(most_valuable_trait: str) -> str:
    most_valuable_trait = most_valuable_trait.replace("_", " ")
    traits = most_valuable_trait.split(" ")
    trait_type = traits[-1]

    idx = 0
    for trait in traits:
        if trait == trait_type:
            idx += 1
    if idx > 1:
        most_valuable_trait = most_valuable_trait[:-len(trait_type)]
    return most_valuable_trait


def format_message(trait_prices: dict, rarity_score: int, asset: dict) -> discord.Embed:
    prices = np.array(list(trait_prices.values()))
    most_valuable_trait = _format_mvt(max(trait_prices.items(), key=operator.itemgetter(1))[0])

    embeds = discord.Embed(title=f"🤑 {asset['name']} 🤑", url=asset["permalink"])
    embeds.add_field(name="**Average Price** 💸", value=f"{np.average(prices):.2f} ETH", inline=False)
    embeds.add_field(name="**Min Price**", value=f"{np.min(prices):.2f} ETH", inline=True)
    embeds.add_field(name="**Max Price**", value=f"{np.max(prices):.2f} ETH", inline=True)
    embeds.add_field(name="**Most Valuable Trait** 🚀", value=f'{most_valuable_trait}', inline=False)
    if rarity_score != -1:
        embeds.add_field(name="**Rarity Score**", value=f'{rarity_score}/100', inline=False)

    embeds.set_image(url=asset["image_url"])
    embeds.set_footer(text=f'The Price My Chibi Bot, created by Dinesh#7505\nDisclaimer: No guarantees on prices. '
                           f'Estimates are based on value of traits from historical listing data.')
    return embeds


@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == DISCORD_GUILD_NAME:
            logger.info(f'{client.user.name} has connected to {guild.name}(id: {guild.id})!')
            break



@client.event
async def on_message(message):
    global asset_data, last_mtime, database_path, total_traits_count, rarities

    if message.author == client.user:
        return

    # Filter messages not from the price-my-ape channel
    if str(message.channel.id) != DISCORD_GUILD_CBD:
        logger.warning(f"Wrong channel={message.channel}")
        return

    current_mtime = os.path.getmtime(os.path.join(DATA_FOLDER, "data.json"))
    if current_mtime != last_mtime:
        logger.info(f"Reloading database from {database_path}  due to changes")
        asset_data = cbd.load_json(filename=database_path)
        last_mtime = current_mtime
        total_traits_count, rarities = cbd.get_total_unique_trait_count_and_rarities(asset_data)

    content = str(message.content)
    if content.startswith("https://opensea.io/assets/0xa0f38233688bb578c0a88102a95b846c18bc0ba7/"):
        try:
            # Remove trailing slashes
            if content.endswith("/"):
                content = content[:-1]

            # Parse the URL to generate an asset ID
            asset_id = get_asset_id_from_url(content)

            logger.info(f"AssetId={asset_id}, Content={content}, Message={message}")

            # single_asset = gaa.get_single_asset(asset_id)

            # Query database if asset id is present, and generate single asset information
            single_asset = None
            for asset in asset_data:
                if asset["token_id"] == asset_id:
                    single_asset = asset
                    break
            if not single_asset:
                raise ValueError(f"Asset id {asset_id} not found in database")

            # Get median trait prices of single asset
            prices = cbd.get_traits_with_median_prices(asset_data, single_asset)

            # Get rarity
            rarity_score = cbd.get_rarity_score(single_asset, rarities, total_traits_count)

            # Format response to Discord bot
            response = format_message(prices, rarity_score, single_asset)
            await message.channel.send(embed=response)
        except Exception as exc:
            logger.error(f"Exception: {exc}")
    else:
        logger.warning(f"Invalid url {message}")


@client.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise


client.run(DISCORD_TOKEN)
