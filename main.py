import discord
from music_cog import musicCog
from discord.ext import commands
import asyncio
from api import BOT_TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

async def main():
    await bot.add_cog(musicCog(bot))
    await bot.start(BOT_TOKEN)

asyncio.run(main())
