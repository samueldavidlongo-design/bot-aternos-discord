import os
from threading import Thread
import time
from flask import Flask
import discord
from discord.ext import commands
import requests

# --- 1. SERVIDOR WEB 24/7 PARA RENDER ---
app = Flask("")

@app.route("/")
def home():
    return "¡El bot de Aternos está activo y despierto!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- 2. CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ATERNOS_SESSION = os.getenv("ATERNOS_SESSION")
MINECRAFT_IP = os.getenv("MINECRAFT_IP", "tu_servidor.aternos.me")
BOT_START_TIME = time.time()

@bot.event
async def on_ready():
    print(f"¡Bot conectado como {bot.user}!")

# --- 3. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    await ctx.send(f"🔄 **{ctx.author.name}**, enviando orden para encender Aternos... ⏳")
    
    if not ATERNOS_SESSION:
        await ctx.send("❌ Error: Falta configurar la variable `ATERNOS_SESSION` en Render.")
        return

    try:
        # Cabeceras completas imitando a un navegador haciendo AJAX
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Cookie": ATERNOS_SESSION,
            "Referer": "https://aternos.org/server/",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }

        response = requests.get("https://aternos.org/panel/ajax/start.php", headers=headers, timeout=10)
        
        if response.status_code == 200:
            await ctx.send(f"✅ ¡Orden enviada con éxito por **{ctx.author.name}**! El servidor se está iniciando. 🚀\n*Tardará 1-2 minutos en quedar Online.*")
        elif response.status_code == 403:
            await ctx.send("⚠️ Error 403: Aternos rechazó la cookie o expiró la sesión. Vuelve a copiar el `document.cookie` desde Opera GX e introdúcelo en Render.")
        else:
            await ctx.send(f"⚠️ Aternos respondió con código `{response.status_code}`.")

    except Exception as e:
        await ctx.send(f"❌ Ocurrió un error de conexión:\n`{e}`")

# --- 4. COMANDO: !status (Con API de respaldo y mayor tiempo de espera) ---
@bot.command(name="status")
async def status(ctx):
    await ctx.send("🔎 Consultando estado del servidor de Minecraft... 📡")

    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    is_online = False
    online_players = 0
    max_players = 0
    ping = "N/A"
    version = "Desconocida"

    # Intento 1: API mcstatus.io (Timeout aumentado a 12s)
    try:
        res = requests.get(f"https://api.mcstatus.io/v2/status/java/{MINECRAFT_IP}", timeout=12).json()
        if res.get("online"):
            is_online = True
            online_players = res["players"]["online"]
            max_players = res["players"]["max"]
            ping = res.get("roundTripLatency", "N/A")
            version = res.get("version", {}).get("name_clean", "Desconocida")
    except Exception:
        # Intento 2: API de respaldo (mcsrvstat.us)
        try:
            res = requests.get(f"https://api.mcsrvstat.us/2/{MINECRAFT_IP}", timeout=12).json()
            if res.get("online"):
                is_online = True
                online_players = res["players"]["online"]
                max_players = res["players"]["max"]
                version = res.get("version", "Desconocida")
        except Exception:
            pass

    # Generar Embed
    if is_online:
        embed = discord.Embed(
            title=f"🎮 Servidor Online: {MINECRAFT_IP}",
            description="¡El mundo está abierto y listo para jugar! ⚔️",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 Jugadores", value=f"**{online_players}/{max_players}**", inline=True)
        embed.add_field(name="⚡ Ping MC", value=f"**{ping} ms**", inline=True)
        embed.add_field(name="📶 Ping Bot", value=f"**{round(bot.latency * 1000)} ms**", inline=True)
        embed.add_field(name="📌 Versión", value=f"`{version}`", inline=False)
    else:
        embed = discord.Embed(
            title="😴 Servidor Fuera de Línea",
            description="💤 *El servidor está apagado o encendiéndose...*\n\n👉 Escribe **`!encender`** para iniciar Aternos.",
            color=discord.Color.red()
        )
        embed.add_field(name="📶 Ping Bot", value=f"**{round(bot.latency * 1000)} ms**", inline=True)

    embed.set_footer(text=f"Bot activo desde hace: {uptime_str} | IP: {MINECRAFT_IP}")
    await ctx.send(embed=embed)

# --- 5. INICIO ---
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: Falta DISCORD_TOKEN.")
