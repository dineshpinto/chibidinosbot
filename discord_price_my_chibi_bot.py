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

from config import DISCORD_TOKEN_PMCBOT, DISCORD_CHANNEL_ID_PMC, DISCORD_GUILD_NAME_PMC, CONTRACT_ADDRESS
from src.nft_analytics import NFTAnalytics

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logfile_pmcbot.log", mode="a"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

cbd = NFTAnalytics("0xe12EDaab53023c75473a5A011bdB729eE73545e8")
DATA_FOLDER = os.path.join("data")

database_path = os.path.join(DATA_FOLDER, "data.json")
asset_data = cbd.load_json(filename=database_path)

iqs = cbd.extract_asset_type_from_traits(asset_data, trait_type_to_extract="IQ")
iq_percentiles = cbd.get_percentile_score(iqs)

asset_data = cbd.remove_asset_type_from_traits(asset_data, trait_type_to_remove="IQ")

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


def format_message(trait_prices: dict, asset: dict, user_name: str) -> discord.Embed:
    prices = np.array(list(trait_prices.values()))
    most_valuable_trait = _format_mvt(max(trait_prices.items(), key=operator.itemgetter(1))[0])

    embeds = discord.Embed(title=f"🤑 {asset['name']} for {user_name} 🤑", url=asset["permalink"])
    embeds.add_field(name="**Average Price** 💸", value=f"{np.nanmean(prices):.2f} ETH", inline=False)
    embeds.add_field(name="**Min Price**", value=f"{np.nanmin(prices):.2f} ETH", inline=True)
    embeds.add_field(name="**Max Price**", value=f"{np.nanmax(prices):.2f} ETH", inline=True)
    embeds.add_field(name="**Most Valuable Trait** 🚀", value=f'{most_valuable_trait}', inline=False)
    embeds.add_field(name="**IQ Ranking** 🤯", value=f'{asset["IQ"]} IQ, {asset["IQ_percentile"]}% of Dinos are below '
                                          f'{asset["IQ"]} IQ', inline=False)

    embeds.set_image(url=asset["image_url"])
    embeds.set_footer(text=f'The Price My Chibi Bot, created by Dinesh#7505\nDisclaimer: No guarantees on prices. '
                           f'Estimates are based on value of traits from historical listing data.')
    return embeds


@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == DISCORD_GUILD_NAME_PMC:
            logger.info(f'{client.user.name} has connected to {guild.name} (id: {guild.id})!')
            break


@client.event
async def on_message(message):
    global asset_data, last_mtime, database_path, iqs, iq_percentiles
    if message.author == client.user:
        return

    # Filter messages not from the price-my-chibi channel
    if message.channel.id != DISCORD_CHANNEL_ID_PMC:
        return

    content = str(message.content).lower()

    current_mtime = os.path.getmtime(os.path.join(DATA_FOLDER, "data.json"))
    if current_mtime != last_mtime:
        logger.info(f"Reloading database from {database_path}  due to changes")
        asset_data = cbd.load_json(filename=database_path)
        iqs = cbd.extract_asset_type_from_traits(asset_data, trait_type_to_extract="IQ")
        iq_percentiles = cbd.get_percentile_score(iqs)
        asset_data = cbd.remove_asset_type_from_traits(asset_data, trait_type_to_remove="IQ")
        last_mtime = current_mtime

    if content.startswith(f"https://opensea.io/assets/{CONTRACT_ADDRESS}/".lower()):
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

            await message.channel.send(
                f"Crunching through 10k data points, just for you {message.author.name} 😉. Hold tight!")

            # Get median trait prices of single asset
            prices = cbd.get_traits_with_median_prices(asset_data, single_asset)

            single_asset["IQ"] = iqs[asset_id]
            single_asset["IQ_percentile"] = iq_percentiles[asset_id]

            # Format response to Discord bot
            response = format_message(prices, single_asset, message.author.name)
            await message.channel.send(embed=response)
        except Exception as exc:
            logger.error(f"Exception: {exc}")
    else:
        logger.warning(f"Invalid url {message}")


@client.event
async def on_error(event, *args, **kwargs):
    with open('err2.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise


client.run(DISCORD_TOKEN_PMCBOT)
