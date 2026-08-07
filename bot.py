import os
import re
import time
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests

# --- 1. MANTENER VIVO EN RENDER (24/7) ---
app = Flask("")

@app.route("/")
def home():
    return "¡BelmoSMP Bot activo!"

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

BOT_START_TIME = time.time()

def solicitar_via_scrapedo(target_url, cookie_val):
    """Petición a Aternos a través de Scrape.do"""
    # Busca 'scrape_api_key' o 'SCRAPER_API_KEY' o usa la clave por defecto
    token = (
        os.getenv("scrape_api_key") or 
        os.getenv("SCRAPER_API_KEY") or 
        "9b8f9cb65f804598be72dd323213327559006dbca70"
    ).strip()

    params = {
        'token': token,
        'url': target_url
    }
    
    headers = {
        'Cookie': f"ATERNOS_SESSION={cookie_val}" if "ATERNOS_SESSION=" not in cookie_val else cookie_val,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
    }
    
    response = requests.get('https://api.scrape.do', params=params, headers=headers, timeout=35)
    return response

@bot.event
async def on_ready():
    print(f"🤖 Bot encendido correctamente como: {bot.user}")

# --- 3. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    await ctx.send(f"Entendido! **{ctx.author.display_name}**, prendiendo el server BelmoSMP... ⚡")

    session_cookie = os.getenv("ATERNOS_SESSION")
    if not session_cookie:
        await ctx.send("❌ **[Debug]:** Falta la variable `ATERNOS_SESSION` en Render.")
        return

    try:
        # Paso 1: Leer el panel de Aternos vía Scrape.do
        panel_res = solicitar_via_scrapedo("https://aternos.org/server/", session_cookie)

        if panel_res.status_code == 401:
            await ctx.send("⚠️ **[Debug Error 401]:** Scrape.do rechazó el token. Revisa tu API Key en https://dashboard.scrape.do/overview")
            return
        elif panel_res.status_code != 200:
            await ctx.send(f"⚠️ **[Debug Error HTTP {panel_res.status_code}]:** Scrape.do / Aternos devolvió código de error.")
            return

        # Extraer el token interno AJAX/SEC
        sec_match = (
            re.search(r'window\.AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'SEC\s*:\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text)
        )

        if not sec_match:
            await ctx.send("⚠️ **[Debug]:** No se pudo extraer el token AJAX. Es posible que la cookie `ATERNOS_SESSION` haya caducado.")
            return

        sec_token = sec_match.group(1)

        # Paso 2: Enviar la orden de inicio a Aternos
        start_url = f"https://aternos.org/panel/ajax/start.php?head={sec_token}"
        start_res = solicitar_via_scrapedo(start_url, session_cookie)

        if start_res.status_code == 200:
            try:
                resp_json = start_res.json()
                if resp_json.get("success"):
                    await ctx.send("🚀 **¡Listo! Servidor mandado a encender.** En unos minutos BelmoSMP estará listo para jugar. 🎮")
                else:
                    msg = resp_json.get("error", "Desconocido")
                    await ctx.send(f"⚠️ Aternos respondió pero no inició: `{msg}`")
            except Exception:
                await ctx.send("✅ ¡Orden enviada a Aternos! Revisa con `!status` en un momento.")
        else:
            await ctx.send(f"⚠️ **[Debug Error HTTP {start_res.status_code}]:** Falló el envío de la orden de inicio.")

    except Exception as e:
        await ctx.send(f"❌ **[Debug Exception]:** `{e}`")

# --- 4. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
    await ctx.send("🔎 Consultando el estado de **BelmoSMP**...")

    minecraft_ip = os.getenv("MINECRAFT_IP", "belmosmp.aternos.me")
    
    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    is_online = False
    online_players = 0
    max_players = 0
    version = "Desconocida"

    try:
        # Verificación precisa mediante la API de mcsrvstat.us
        res = requests.get(f"https://api.mcsrvstat.us/3/{minecraft_ip}", timeout=6).json()
        if res.get("online") is True:
            is_online = True
            online_players = res.get("players", {}).get("online", 0)
            max_players = res.get("players", {}).get("max", 0)
            version = res.get("version", "Java")
    except Exception:
        is_online = False

    if is_online:
        embed = discord.Embed(
            title="🎮 ¡BelmoSMP está Online!",
            description=f"¡Servidor listo! IP: `{minecraft_ip}` ⚔️",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 Jugadores", value=f"**{online_players}/{max_players}**", inline=True)
        embed.add_field(name="📌 Versión", value=f"`{version}`", inline=True)
    else:
        embed = discord.Embed(
            title="😴 BelmoSMP está Apagado",
            description="El servidor se encuentra offline.\n\n👉 Escribe **`!encender`** para iniciarlo.",
            color=discord.Color.red()
        )

    embed.set_footer(text=f"Bot activo desde hace: {uptime_str} | IP: {minecraft_ip}")
    await ctx.send(embed=embed)

# --- 5. INICIALIZACIÓN ---
if __name__ == "__main__":
    keep_alive()
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token:
        bot.run(discord_token)
    else:
        print("❌ ERROR: Falta DISCORD_TOKEN.")
