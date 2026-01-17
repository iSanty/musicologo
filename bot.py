import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

import ctypes

# Ruta donde está libopus.so en tu VPS
discord.opus.load_opus("/usr/lib/x86_64-linux-gnu/libopus.so")
print(discord.opus.is_loaded())  # debería dar True


# Cargar token
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Intents y bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cola por guild
queues = {}

# Opciones de yt-dlp para streaming directo
ytdlp_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "extract_flat": False,  # da URL directa
    "nocheckcertificate": True,
    "geo_bypass": True,
    "default_search": "ytsearch",  # permite buscar por texto
    "source_address": "0.0.0.0",   # evita bloqueos de IP
}

# Opciones FFmpeg para streaming
ffmpeg_opts = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",  # sin video
}

async def play_next(ctx):
    """Reproduce la siguiente canción en la cola."""
    if not queues.get(ctx.guild.id):
        await ctx.voice_client.disconnect()
        return

    url = queues[ctx.guild.id].pop(0)

    # Usamos yt-dlp para obtener la URL directa del stream
    ydl_opts = ytdlp_opts.copy()
    ydl_opts["quiet"] = True
    ydl_opts["format"] = "bestaudio/best"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info["url"]

    # Reproducir en Discord
    source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts)
    ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))

@bot.event
async def on_ready():
    print(f"🎵 Conectado como {bot.user}")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send(f"✅ Conectado a {ctx.author.voice.channel.name}")
    else:
        await ctx.send("❌ Tenés que estar en un canal de voz.")

@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send("❌ Tenés que estar en un canal de voz.")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    try:
        # Extraemos info del video y la URL directa de audio
        with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:  # si es búsqueda o playlist
                info = info["entries"][0]
            audio_url = info["url"]
            title = info["title"]
    except Exception as e:
        return await ctx.send(f"❌ No se pudo reproducir: {e}")

    queues.setdefault(ctx.guild.id, []).append(query)

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
