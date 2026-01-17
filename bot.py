import os
import asyncio
import logging
import discord
from discord.ext import commands
import wavelink
from dotenv import load_dotenv

# ========================
# Configuración base
# ========================

load_dotenv()

TOKEN = os.getenv("TOKEN")
LAVALINK_HOST = os.getenv("LAVALINK_HOST", "127.0.0.1")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "2333"))
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
# Lavalink / Wavelink
# ========================

@bot.event
async def on_ready():
    log.info(f"🎵 Musicólogo conectado como {bot.user} (ID: {bot.user.id})")

    if not wavelink.Pool.nodes:
        await wavelink.Pool.connect(
            client=bot,
            nodes=[
                wavelink.Node(
                    uri=f"http://{LAVALINK_HOST}:{LAVALINK_PORT}",
                    password=LAVALINK_PASSWORD,
                )
            ],
        )
        log.info("✅ Conectado a Lavalink")

# ========================
# Comandos
# ========================

@bot.command()
async def join(ctx: commands.Context):
    if not ctx.author.voice:
        return await ctx.send("Tenés que estar en un canal de voz.")

    if ctx.voice_client:
        await ctx.voice_client.move_to(ctx.author.voice.channel)
    else:
        await ctx.author.voice.channel.connect(cls=wavelink.Player)

    await ctx.send("🎧 Conectado al canal.")

@bot.command()
async def play(ctx: commands.Context, *, query: str):
    if not ctx.voice_client:
        await join(ctx)

    player: wavelink.Player = ctx.voice_client
    tracks = await wavelink.Playable.search(f"scsearch:{query}")


    if not tracks:
        return await ctx.send("❌ No encontré nada.")

    track = tracks[0]
    await player.play(track)
    await ctx.send(f"▶️ Reproduciendo: **{track.title}**")

@bot.command()
async def skip(ctx):
    if ctx.voice_client:
        await ctx.voice_client.stop()
        await ctx.send("⏭️ Saltado.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Detenido.")

# ========================
# Run
# ========================

if not TOKEN:
    raise RuntimeError("TOKEN no definido en .env")

bot.run(TOKEN)
