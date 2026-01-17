import os
import asyncio
import logging
import discord
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv

# ========================
# Configuración base
# ========================

load_dotenv()

TOKEN = os.getenv("TOKEN")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

print("FFMPEG_PATH =", repr(FFMPEG_PATH))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

log = logging.getLogger("musicologo")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========================
# YT-DLP / FFMPEG
# ========================

YTDLP_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "cookiefile": "cookies.txt",
}


FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

# ========================
# Estado por servidor
# ========================

queues: dict[int, list[tuple[str, str]]] = {}

def get_queue(guild_id: int):
    return queues.setdefault(guild_id, [])

# ========================
# Eventos
# ========================

@bot.event
async def on_ready():
    log.info(f"🎵 Musicólogo conectado como {bot.user} (ID: {bot.user.id})")

# ========================
# Core playback
# ========================

async def play_next(ctx: commands.Context):
    queue = get_queue(ctx.guild.id)

    if not queue:
        return

    url, title = queue.pop(0)

    source = discord.FFmpegPCMAudio(
        url,
        executable=FFMPEG_PATH,
        **FFMPEG_OPTS,
    )

    def after_playing(error):
        if error:
            log.error(f"Error reproduciendo audio: {error}")
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    ctx.voice_client.play(source, after=after_playing)
    await ctx.send(f"▶️ **Reproduciendo:** {title}")

# ========================
# Comandos
# ========================

@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("Tenés que estar en un canal de voz.")
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()

    await ctx.send(f"🎧 Conectado a **{channel.name}**")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        get_queue(ctx.guild.id).clear()
        await ctx.send("👋 Desconectado del canal.")
    else:
        await ctx.send("No estoy conectado.")

@bot.command()
async def play(ctx, url: str):
    if not ctx.voice_client:
        await join(ctx)

    try:
        with yt_dlp.YoutubeDL(YTDLP_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info["url"]
            title = info.get("title", "Desconocido")
    except Exception as e:
        log.error(e)
        await ctx.send("❌ No pude obtener el audio.")
        return

    queue = get_queue(ctx.guild.id)
    queue.append((audio_url, title))

    await ctx.send(f"➕ Agregado a la cola: **{title}**")

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Canción saltada.")
    else:
        await ctx.send("No hay nada reproduciéndose.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        get_queue(ctx.guild.id).clear()
        ctx.voice_client.stop()
        await ctx.send("⏹️ Música detenida y cola limpia.")
    else:
        await ctx.send("No estoy reproduciendo nada.")

# ========================
# Run
# ========================

if not TOKEN:
    raise RuntimeError("TOKEN no definido en .env")

bot.run(TOKEN)
