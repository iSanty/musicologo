import os
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
import wavelink

# ========================
# Configuración base
# ========================

load_dotenv()

TOKEN = os.getenv("TOKEN")
LAVALINK_URI = os.getenv("LAVALINK_URI", "http://127.0.0.1:2333")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

log = logging.getLogger("musicologo")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========================
# Estado por servidor
# ========================

queues: dict[int, list[wavelink.Playable]] = {}

def get_queue(guild_id: int):
    return queues.setdefault(guild_id, [])

# ========================
# Eventos
# ========================

@bot.event
async def on_ready():
    log.info(f"🎵 Musicólogo conectado como {bot.user} (ID: {bot.user.id})")

    node = wavelink.Node(
        uri=LAVALINK_URI,
        password=LAVALINK_PASSWORD,
    )

    await wavelink.Pool.connect(client=bot, nodes=[node])

# ========================
# Core playback
# ========================

async def play_next(player: wavelink.Player, ctx: commands.Context):
    queue = get_queue(ctx.guild.id)

    if not queue:
        await player.disconnect()
        return

    track = queue.pop(0)
    await player.play(track)
    await ctx.send(f"▶️ **Reproduciendo:** {track.title}")

# ========================
# Comandos
# ========================

@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("Tenés que estar en un canal de voz.")

    channel = ctx.author.voice.channel

    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect(cls=wavelink.Player)

    await ctx.send(f"🎧 Conectado a **{channel.name}**")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        get_queue(ctx.guild.id).clear()
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Desconectado.")
    else:
        await ctx.send("No estoy conectado.")

@bot.command()
async def play(ctx, *, search: str):
    if not ctx.voice_client:
        await join(ctx)

    player: wavelink.Player = ctx.voice_client

    tracks = await wavelink.Playable.search(search)
    if not tracks:
        return await ctx.send("❌ No encontré resultados.")

    track = tracks[0]
    queue = get_queue(ctx.guild.id)
    queue.append(track)

    await ctx.send(f"➕ Agregado: **{track.title}**")

    if not player.playing:
        await play_next(player, ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.playing:
        await ctx.voice_client.stop()
        await ctx.send("⏭️ Saltado.")
    else:
        await ctx.send("No hay nada reproduciéndose.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        get_queue(ctx.guild.id).clear()
        await ctx.voice_client.stop()
        await ctx.send("⏹️ Música detenida y cola limpia.")
    else:
        await ctx.send("No estoy reproduciendo nada.")

# ========================
# Auto-play siguiente track
# ========================

@bot.event
async def on_wavelink_track_end(payload):
    player = payload.player
    guild = player.guild
    channel = guild.text_channels[0]  # fallback
    fake_ctx = await bot.get_context(await channel.send(""))

    await play_next(player, fake_ctx)

# ========================
# Run
# ========================

if not TOKEN:
    raise RuntimeError("TOKEN no definido en .env")

bot.run(TOKEN)
