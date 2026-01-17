import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}
ytdlp_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "default_search": "ytsearch",
    "cookiefile": "cookies.txt",
}

ffmpeg_opts = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@bot.event
async def on_ready():
    print(f"🎵 Conectado como {bot.user}")


async def play_next(ctx):
    if not queues.get(ctx.guild.id):
        await ctx.voice_client.disconnect()
        return

    url = queues[ctx.guild.id].pop(0)
    source = discord.FFmpegPCMAudio(url, **ffmpeg_opts)
    ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))


@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.send("❌ Tenés que estar en un canal de voz.")


@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send("❌ Tenés que estar en un canal de voz.")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        url = info["url"]
        title = info["title"]

    queues.setdefault(ctx.guild.id, []).append(url)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)
        await ctx.send(f"▶️ Reproduciendo: **{title}**")
    else:
        await ctx.send(f"➕ Agregado a la cola: **{title}**")


@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ Saltado.")


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        queues[ctx.guild.id] = []
        await ctx.voice_client.disconnect()
        await ctx.send("⏹ Detenido y desconectado.")


bot.run(TOKEN)
