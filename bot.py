import os
import re
import time
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests

# --- 1. SERVIDOR WEB 24/7 PARA RENDER / UPTIMEROBOT ---
app = Flask("")

@app.route("/")
def home():
    return "¡El bot de BelmoSMP está activo y súper ligero!"

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

# Cargar variables de entorno
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "9b8f9cb65f804598be72dd323213327559006dbca70")
ATERNOS_SESSION = os.getenv("ATERNOS_SESSION")
MINECRAFT_IP = os.getenv("MINECRAFT_IP", "belmosmp.aternos.me")
BOT_START_TIME = time.time()

def scraper_get(target_url, headers=None, cookies=None):
    """Realiza peticiones a través de ScraperAPI para saltar Cloudflare"""
    params = {
        'api_key': SCRAPER_API_KEY,
        'url': target_url,
        'keep_headers': 'true'
    }
    
    req_headers = headers or {}
    if cookies:
        req_headers['Cookie'] = cookies
        
    return requests.get('http://api.scraperapi.com', params=params, headers=req_headers, timeout=30)

@bot.event
async def on_ready():
    print(f"¡Bot conectado exitosamente como {bot.user}!")

# --- 3. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    await ctx.send(f"🌱 Dale **{ctx.author.name}**, saltando Cloudflare con ScraperAPI y enviando orden a Aternos... ⚡")

    if not ATERNOS_SESSION:
        await ctx.send("❌ Uy, falta la variable `ATERNOS_SESSION` en el panel de Render.")
        return

    try:
        # Formatear la cookie
        cookie_header = ATERNOS_SESSION if "ATERNOS_SESSION=" in ATERNOS_SESSION else f"ATERNOS_SESSION={ATERNOS_SESSION}"

        # Paso 1: Obtener la página del panel para extraer el Token SEC/AJAX
        panel_res = scraper_get("https://aternos.org/server/", cookies=cookie_header)

        if panel_res.status_code != 200:
            await ctx.send(f"⚠️ Aternos / ScraperAPI devolvió el código `{panel_res.status_code}`.")
            return

        # Buscar el token interno de la sesión de Aternos
        sec_match = (
            re.search(r'window\.AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'SEC\s*:\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text)
        )

        if not sec_match:
            await ctx.send(
                "⚠️ No pude extraer el token de inicio. Es probable que la cookie `ATERNOS_SESSION` haya caducado.\n"
                "👉 Si vuelve a fallar, copia el nuevo valor de `ATERNOS_SESSION` desde tu navegador."
            )
            return

        sec_token = sec_match.group(1)

        # Paso 2: Enviar la petición AJAX de inicio
        start_url = f"https://aternos.org/panel/ajax/start.php?head={sec_token}"
        start_res = scraper_get(start_url, cookies=cookie_header)

        if start_res.status_code == 200:
            try:
                resp_json = start_res.json()
                if resp_json.get("success"):
                    await ctx.send("🚀 **¡Listo!** Enviada la orden de encendido para **BelmoSMP**. En unos minutos estará online 🎮")
                else:
                    error_msg = resp_json.get("error", "Desconocido")
                    await ctx.send(f"⚠️ Aternos respondió, pero no inició. Mensaje: `{error_msg}`")
            except Exception:
                await ctx.send("✅ Petición enviada exitosamente a Aternos. Revisa con `!status` en breve.")
        else:
            await ctx.send(f"⚠️ Error al enviar la orden: Código HTTP `{start_res.status_code}`.")

    except Exception as e:
        await ctx.send(f"❌ Ocurrió un error en la conexión:\n`{e}`")

# --- 4. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
    await ctx.send("🔎 Revisando el estado de **BelmoSMP**... 📡")

    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    is_online = False
    online_players = 0
    max_players = 0
    ping = "N/A"
    version = "Desconocida"

    try:
        res = requests.get(f"https://api.mcstatus.io/v2/status/java/{MINECRAFT_IP}", timeout=8).json()
        if res.get("online"):
            is_online = True
            online_players = res["players"]["online"]
            max_players = res["players"]["max"]
            ping = res.get("roundTripLatency", "N/A")
            version = res.get("version", {}).get("name_clean", "Desconocida")
    except Exception:
        pass

    if is_online:
        embed = discord.Embed(
            title="🎮 BelmoSMP está Online",
            description=f"¡El servidor ya está listo! IP: `{MINECRAFT_IP}` ⚔️",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 Jugadores", value=f"**{online_players}/{max_players}**", inline=True)
        embed.add_field(name="⚡ Ping MC", value=f"**{ping} ms**", inline=True)
        embed.add_field(name="📌 Versión", value=f"`{version}`", inline=False)
    else:
        embed = discord.Embed(
            title="😴 BelmoSMP está Apagado",
            description="💤 El servidor está offline o cargando...\n\n👉 Ejecuta **`!encender`** para iniciarlo.",
            color=discord.Color.red()
        )

    embed.set_footer(text=f"Bot activo desde hace: {uptime_str} | IP: {MINECRAFT_IP}")
    await ctx.send(embed=embed)

# --- 5. INICIO ---
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: Falta la variable DISCORD_TOKEN.")
