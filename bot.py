import os
import discord
from discord.ext import commands
from mcstatus import JavaServer
from pyaternos import Client

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ATERNOS_USER = os.getenv("ATERNOS_USER")
ATERNOS_PASS = os.getenv("ATERNOS_PASS")
SERVER_NAME = os.getenv("SERVER_NAME", "BelmoSMP")
SERVER_IP = "belmoSMP.aternos.me"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 Bot 24/7 conectado como: {bot.user}")
    await bot.change_presence(activity=discord.Game(name=f"!estado | {SERVER_IP}"))

@bot.command(name="estado", aliases=["status"])
async def estado(ctx):
    try:
        mensaje_espera = await ctx.send("🔍 Consultando estado del servidor...")
        server = await JavaServer.async_lookup(SERVER_IP)
        status = await server.async_status()

        embed = discord.Embed(
            title="🟢 ¡Servidor En Línea!", 
            description=f"El servidor **`{SERVER_IP}`** está abierto.", 
            color=discord.Color.green()
        )
        embed.add_field(name="👥 Jugadores", value=f"`{status.players.online} / {status.players.max}`", inline=True)
        embed.add_field(name="⚡ Latencia", value=f"`{round(status.latency)} ms`", inline=True)
        await mensaje_espera.edit(content=None, embed=embed)
    except Exception:
        embed = discord.Embed(
            title="🔴 Servidor Desconectado", 
            description=f"El servidor **`{SERVER_IP}`** está apagado.", 
            color=discord.Color.red()
        )
        embed.add_field(name="💡 ¿Qué hacer?", value="Usa **`!encender`** para iniciarlo.", inline=False)
        await mensaje_espera.edit(content=None, embed=embed)

@bot.command(name="encender", aliases=["start"])
async def encender(ctx):
    if not ATERNOS_USER or not ATERNOS_PASS:
        await ctx.send("❌ Faltan las credenciales de Aternos en la configuración de Render.")
        return

    mensaje = await ctx.send("🤖 Conectando con Aternos para encender el servidor...")

    try:
        at = Client(ATERNOS_USER, ATERNOS_PASS)
        my_servers = at.server_list
        
        servidor_objetivo = None
        for srv in my_servers:
            if SERVER_NAME.lower() in srv.address.lower() or SERVER_NAME.lower() in str(srv).lower():
                servidor_objetivo = srv
                break
        
        if not servidor_objetivo and len(my_servers) > 0:
            servidor_objetivo = my_servers[0]

        if servidor_objetivo:
            if servidor_objetivo.status == "online":
                await mensaje.edit(content="ℹ️ ¡El servidor ya se encuentra encendido!")
                return
            
            servidor_objetivo.start()
            await mensaje.edit(content=f"✅ **¡Servidor encendido con éxito!** Aternos está arrancando **{SERVER_NAME}**.")
        else:
            await mensaje.edit(content="❌ No se encontró ningún servidor asociado a tu cuenta de Aternos.")

    except Exception as e:
        print(f"Error al encender: {e}")
        await mensaje.edit(content=f"❌ Error al comunicarse con Aternos: `{str(e)[:100]}`")

bot.run(DISCORD_TOKEN)
