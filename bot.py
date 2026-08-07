import os
import re
import time
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests

# --- 1. MANTENER VIVO EN RENDER (FLASK 24/7) ---
app = Flask("")

@app.route("/")
def home():
    return "¡BelmoSMP Bot está online!"

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

def scraper_request(target_url, cookies=None):
    """Petición a través de ScraperAPI para esquivar el bloqueo de Cloudflare"""
    api_key = os.getenv("SCRAPER_API_KEY", "9b8f9cb65f804598be72dd323213327559006dbca70").strip()
    
    params = {
        'api_key': api_key,
        'url': target_url,
        'keep_headers': 'true'
    }
    
    headers = {}
    if cookies:
        headers['Cookie'] = cookies
        
    return requests.get('http://api.scraperapi.com', params=params, headers=headers, timeout=35)

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado con éxito como: {bot.user}")

# --- 3. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    # Mensaje amigable de inicio
    await ctx.send(f"¡Entendido, **{ctx.author.display_name}**! 🚀 Prendiendo el servidor **BelmoSMP**, dame unos segundos...")

    session_cookie = os.getenv("ATERNOS_SESSION")
    if not session_cookie:
        await ctx.send("❌ **[Debug Error]:** Falta la variable `ATERNOS_SESSION` en el panel de Render.")
        return

    try:
        # Darle el formato adecuado a la cookie
        cookie_header = session_cookie if "ATERNOS_SESSION=" in session_cookie else f"ATERNOS_SESSION={session_cookie.strip()}"

        # Paso 1: Leer el panel de Aternos
        panel_res = scraper_request("https://aternos.org/server/", cookies=cookie_header)

        if panel_res.status_code == 401:
            await ctx.send("⚠️ **[Debug Error 401]:** ScraperAPI rechaza la API Key. Revisa si confirmaste el correo de ScraperAPI o si la clave tiene un espacio extra.")
            return
        elif panel_res.status_code != 200:
            await ctx.send(f"⚠️ **[Debug Error HTTP {panel_res.status_code}]:** Aternos o ScraperAPI no respondieron correctamente.")
            return

        # Extraer el token de seguridad interno
        sec_match = (
            re.search(r'window\.AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'SEC\s*:\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text)
        )

        if not sec_match:
            await ctx.send(
                "⚠️ **[Debug Error]:** No pude extraer el token de inicio.\n"
                "👉 Tu sesión de Aternos expiró. Actualiza la variable `ATERNOS_SESSION` en Render con la cookie más reciente de tu navegador."
            )
            return

        sec_token = sec_match.group(1)

        # Paso 2: Enviar la orden de encendido
        start_url = f"https://aternos.org/panel/ajax/start.php?head={sec_token}"
        start_res = scraper_request(start_url, cookies=cookie_header)

        if start_res.status_code == 200:
            try:
                resp_json = start_res.json()
                if resp_json.get("success"):
                    await ctx.send("✅ **¡Listo! La orden de encendido fue enviada.** En un par de minutos **BelmoSMP** estará online. 🎮✨")
                else:
                    error_msg = resp_json.get("error", "Desconocido")
                    await ctx.send(f"⚠️ Aternos respondió, pero no inició. Mensaje de Aternos: `{error_msg}`")
            except Exception:
                await ctx.send("✅ **¡Petición enviada!** Revisa el estado del server con `!status` en un momento.")
        else:
            await ctx.send(f"⚠️ **[Debug Error HTTP {start_res.status_code}]:** Falló el envío del botón de inicio.")

    except Exception as e:
        await ctx.send(f"❌ **[Debug Error Excepción]:** Ocurrió una falla en la ejecución:\n`{e}`")

# --- 4. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
    await ctx.send("🔎 Consultando el estado de **BelmoSMP**... 📡")

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
            description=f"El servidor está listo para jugar. ¡Conéctate ya!\n📌 **IP:** `{minecraft_ip}` ⚔️",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 Jugadores", value=f"**{online_players}/{max_players}**", inline=True)
        embed.add_field(name="⚡ Ping", value=f"**{ping} ms**", inline=True)
        embed.add_field(name="📌 Versión", value=f"`{version}`", inline=False)
    else:
        embed = discord.Embed(
            title="😴 BelmoSMP está Apagado",
            description="El servidor se encuentra descansando...\n\n👉 Escribe **`!encender`** para iniciar el servidor.",
            color=discord.Color.red()
        )

    embed.set_footer(text=f"Bot encendido desde hace: {uptime_str} | IP: {minecraft_ip}")
    await ctx.send(embed=embed)

# --- 5. INICIALIZACIÓN ---
if __name__ == "__main__":
    keep_alive()
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token:
        bot.run(discord_token)
    else:
        print("❌ ERROR: Falta la variable DISCORD_TOKEN.")
