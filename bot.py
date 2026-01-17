import discord
from discord.ext import commands
import yt_dlp
import asyncio
from discord import FFmpegPCMAudio
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.getenv("TOKEN")

# Cola de reproducción global
song_queue = []

@bot.event
async def on_ready():
    print(f'Conectado como {bot.user}')

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f'Conectado a {channel.name}')
    else:
        await ctx.send("¡Necesitas estar en un canal de voz primero!")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Desconectado del canal de voz.')
    else:
        await ctx.send("¡No estoy en ningún canal de voz!")

@bot.command()
async def play(ctx, url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        title = info.get("title", "desconocido")

    if not ctx.voice_client:
        await ctx.send("El bot no está conectado a un canal de voz.")
        return

    song_queue.append(file_path)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

    await ctx.send(f'Agregado a la cola: {title}')

async def play_next(ctx):
    if song_queue:
        song = song_queue.pop(0)
        ffmpeg_options = {'options': '-vn'}

        try:
            ctx.voice_client.play(
                FFmpegPCMAudio(executable="ffmpeg", source=song, **ffmpeg_options),
                after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            )
            await ctx.send(f'Reproduciendo: {os.path.basename(song)}')
        except Exception as e:
            await ctx.send(f"Ocurrió un error: {e}")
    else:
        await ctx.send("No hay más canciones en la cola.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        song_queue.clear()
        await ctx.send("Música detenida y cola vacía.")
    else:
        await ctx.send("No estoy reproduciendo música en este momento.")

@bot.command()
async def skip(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await play_next(ctx)
        await ctx.send("Canción saltada.")
    else:
        await ctx.send("No hay música para saltar.")

bot.run(TOKEN)
