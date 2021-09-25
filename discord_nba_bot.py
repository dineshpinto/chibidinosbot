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

import datetime
import re
import logging
import discord
from discord.ext import tasks
from pbpstats.data_loader import DataNbaScheduleLoader

from config import DISCORD_TOKEN_NBABOT, DISCORD_CHANNEL_ID_NBA, DISCORD_GUILD_NAME_NBA


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logfile_nbabot.log", mode="a"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


client = discord.Client()


games2020_21 = []
schedule_loader = DataNbaScheduleLoader("nba", "2020-21", "Regular Season", "web")
for schedule in schedule_loader.items:
    if schedule.data["date"].startswith("2021"):
        schedule.data["date"] = datetime.datetime.strptime(schedule.data["date"], "%Y-%m-%d")
        games2020_21.append(schedule.data)


games2021_22 = []
schedule_loader = DataNbaScheduleLoader("nba", "2021-22", "Regular Season", "web")
for schedule in schedule_loader.items:
    if schedule.data["date"].startswith("2021"):
        schedule.data["date"] = datetime.datetime.strptime(schedule.data["date"], "%Y-%m-%d")
        games2021_22.append(schedule.data)


@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == DISCORD_GUILD_NAME_NBA:
            logger.info(f'{client.user.name} has connected to {guild.name}(id: {guild.id})!')
            break


def format_last_game_message(game: dict) -> discord.Embed:
    embeds = discord.Embed(title=f"🏀 {game['home_team_abbreviation']} vs {game['away_team_abbreviation']} 🏀")

    embeds.add_field(name=f"Match Date", value=game["date"].strftime("%d %b %Y"), inline=False)

    if int(game["home_score"]) > int(game["away_score"]):
        winning_team_text = f"{game['home_team_abbreviation']} ({game['home_score']})"
        losing_team_text = f"{game['away_team_abbreviation']} ({game['away_score']})"
    else:
        winning_team_text = f"{game['away_team_abbreviation']} ({game['away_score']})"
        losing_team_text = f"{game['home_team_abbreviation']} ({game['home_score']})"

    embeds.add_field(name="🏆 **Winners**", value=winning_team_text, inline=True)
    embeds.add_field(name="😞 **Losers**", value=losing_team_text, inline=True)

    return embeds


def format_next_game_message(game: dict) -> discord.Embed:
    embeds = discord.Embed(title=f"🏀 {game['home_team_abbreviation']} vs {game['away_team_abbreviation']} 🏀")
    embeds.add_field(name=f"Match Date", value=f'{game["date"].strftime("%d %b %Y")} {game["status"]}', inline=False)
    return embeds


def format_help_message() -> discord.Embed:
    embeds = discord.Embed(title=f"🏀 nba-bot Helpdesk 🏀")
    embeds.add_field(name=f"!lastscores", value=f'Will show you the most recent NBA games final score', inline=False)
    embeds.add_field(name=f"!upcoming", value=f'Will show you the upcoming NBA games', inline=False)
    embeds.add_field(name=f"Custom ranges", value=f'Add a number to the end of the above commands to get custom '
                                                  f'data, eg. !upcoming5 will show the next 5 games', inline=False)
    embeds.set_footer(text=f'nba-bot, created by Dinesh#7505')
    return embeds


def get_last_games(games: list, limit: int) -> list:
    current_time = datetime.datetime.now()

    last_games = []
    idx = 0
    for game in games:
        if game["date"] < current_time and idx < limit:
            last_games.append(game)
            idx += 1
    return last_games


def get_next_games(games: list, limit: int) -> list:
    current_time = datetime.datetime.now()

    next_games = []
    idx = 0
    for game in games:
        if game["date"] > current_time and idx < limit:
            next_games.append(game)
            idx += 1
    return next_games


def get_number_from_str(string: str, default=5) -> int:
    m = re.search(r'\d+$', string)
    if m is not None:
        value = int(m.group())
        if not value > 0 and value < 10:
            return default
        else:
            return value
    else:
        return default


@tasks.loop(hours=24)
async def next_games_daily():
    await client.wait_until_ready()
    try:
        message_channel = client.get_channel(DISCORD_CHANNEL_ID_NBA)
        logger.info(f"Sending daily message to {message_channel}")
        await message_channel.send("Your daily NBA schedule, served with ☕")
        next_games = get_next_games(games2021_22, limit=3)
        for game in next_games:
            response = format_next_game_message(game)
            await message_channel.send(embed=response)
    except Exception as exc:
        logger.exception(f"Exception: {exc}")


@client.event
async def on_message(message):
    global games2020_21

    if message.author == client.user:
        return

    # Filter messages not from the price-my-ape channel
    if message.channel.id != DISCORD_CHANNEL_ID_NBA:
        return

    content = str(message.content).lower()
    logger.info(f"Message={message}")
    if content.startswith("!lastscores".lower()):
        try:
            limit = get_number_from_str(content, default=3)
            last_games = get_last_games(games2020_21, limit)
            for game in last_games:
                response = format_last_game_message(game)
                await message.channel.send(embed=response)
            logger.info(f"Successfully sent lastscores")
        except Exception as exc:
            print(f"Exception: {exc}")
    elif content.startswith("!upcoming".lower()):
        try:
            limit = get_number_from_str(content, default=3)
            next_games = get_next_games(games2021_22, limit)
            for game in next_games:
                response = format_next_game_message(game)
                await message.channel.send(embed=response)
            logger.info(f"Successfully sent upcoming")
        except Exception as exc:
            logger.exception(f"Exception: {exc}")
    elif content.startswith("!nbahelp".lower()):
        response = format_help_message()
        await message.channel.send(embed=response)
        logger.info(f"Successfully sent help")
    else:
        logger.debug(f"Invalid message {message}")


@client.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise

next_games_daily.start()
client.run(DISCORD_TOKEN_NBABOT)
