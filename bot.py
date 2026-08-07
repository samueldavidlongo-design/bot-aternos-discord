kkimport os
import re
import time
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests

# --- 1. SERVIDOR WEB 24/7 ---
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

def solicitar_via_scraper(target_url, cookie_val):
    """Petición a Aternos a través de ScraperAPI"""
    api_key = os.getenv("SCRAPER_API_KEY", "").strip()
    
    # Si por alguna razón no lee la variable de Render, usa la clave por defecto
    if not api_key:
        api_key = "9b8f9cb65f804598be72dd323213327559006dbca70"

    params = {
        'api_key': api_key,
        'url': target_url,
        'keep_headers': 'true'
    }
    
    headers = {
        'Cookie': f"ATERNOS_SESSION={cookie_val}" if "ATERNOS_SESSION=" not in cookie_val else cookie_val,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
    }
    
    response = requests.get('http://api.scraperapi.com', params=params, headers=headers, timeout=35)
    return response, api_key

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
        # Paso 1: Intentar leer el panel de Aternos
        panel_res, used_key = solicitar_via_scraper("https://aternos.org/server/", session_cookie)

        if panel_res.status_code == 401:
            key_preview = f"{used_key[:6]}...{used_key[-4:]}" if len(used_key) > 10 else "inválida"
            await ctx.send(
                f"⚠️ **[Debug Error 401 - ScraperAPI]:** La API Key empleada (`{key_preview}`) fue rechazada.\n"
                f"👉 Regenera la clave en scraperapi.com, actualiza `SCRAPER_API_KEY` en Render y guarda cambios."
            )
            return
        elif panel_res.status_code != 200:
            await ctx.send(f"⚠️ **[Debug Error HTTP {panel_res.status_code}]:** ScraperAPI devolvió código de error.")
            return

        # Extraer el token de inicio interno
        sec_match = (
            re.search(r'window\.AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'SEC\s*:\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text)
        )

        if not sec_match:
            await ctx.send("⚠️ **[Debug]:** No se pudo extraer el token AJAX. La sesión de Aternos puede haber expirado.")
            return

        sec_token = sec_match.group(1)

        # Paso 2: Enviar petición de encendido
        start_url = f"https://aternos.org/panel/ajax/start.php?head={sec_token}"
        start_res, _ = solicitar_via_scraper(start_url, session_cookie)

        if start_res.status_code == 200:
            try:
                resp_json = start_res.json()
                if resp_json.get("success"):
                    await ctx.send("🚀 **¡Listo! Servidor mandado a encender.** En unos minutos BelmoSMP estará listo para jugar. 🎮")
                else:
                    msg = resp_json.get("error", "Desconocido")
                    await ctx.send(f"⚠️ Aternos devolvió una respuesta, pero no inició: `{msg}`")
            except Exception:
                await ctx.send("✅ ¡Orden enviada a Aternos! Revisa el estado con `!status` en un momento.")
        else:
            await ctx.send(f"⚠️ **[Debug Error HTTP {start_res.status_code}]:** Falló el envío de la orden de encendido.")

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
    ping = "N/A"
    version = "Desconocida"

    try:
        res = requests.get(f"https://api.mcstatus.io/v2/status/java/{minecraft_ip}", timeout=8).json()
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
            title="🎮 ¡BelmoSMP está Online!",
            description=f"¡Servidor listo! IP: `{minecraft_ip}` ⚔️",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 Jugadores", value=f"**{online_players}/{max_players}**", inline=True)
        embed.add_field(name="⚡ Ping", value=f"**{ping} ms**", inline=True)
        embed.add_field(name="📌 Versión", value=f"`{version}`", inline=False)
    else:
        embed = discord.Embed(
            title="😴 BelmoSMP está Apagado",
            description="El servidor está offline.\n\n👉 Escribe **`!encender`** para iniciarlo.",
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
