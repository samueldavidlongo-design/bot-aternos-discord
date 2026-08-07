import os
import re
import time
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import cloudscraper

# --- 1. SERVIDOR WEB 24/7 ---
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

ATERNOS_SESSION = os.getenv("ATERNOS_SESSION")
MINECRAFT_IP = os.getenv("MINECRAFT_IP", "tu_servidor.aternos.me")
BOT_START_TIME = time.time()

@bot.event
async def on_ready():
    print(f"¡Bot conectado exitosamente como {bot.user}!")

# --- 3. COMANDO: !encender (Con cloudscraper - ~30MB RAM) ---
@bot.command(name="encender")
async def encender(ctx):
    await ctx.send(f"🌱 Dale **{ctx.author.name}**, saltando Cloudflare y enviando orden a Aternos... ⚡")

    if not ATERNOS_SESSION:
        await ctx.send("❌ Uy, falta la cookie de sesión (`ATERNOS_SESSION`) en las variables de Render.")
        return

    try:
        # Crear el scraper que evade Cloudflare automáticamente
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'firefox',
                'platform': 'windows',
                'mobile': False
            }
        )

        # Inyectar la cookie de sesión
        for item in ATERNOS_SESSION.split(";"):
            if "=" in item:
                name, val = item.strip().split("=", 1)
                scraper.cookies.set(name, val, domain=".aternos.org")

        # Paso 1: Cargar la página del panel para extraer el Token SEC interno
        panel_res = scraper.get("https://aternos.org/server/", timeout=15)

        if panel_res.status_code != 200:
            await ctx.send(f"⚠️ Aternos devolvió código de respuesta `{panel_res.status_code}`. Es posible que Cloudflare haya bloqueado la solicitud.")
            return

        # Buscar el token 'SEC' o 'AJAX_TOKEN' en el HTML
        sec_match = (
            re.search(r'window\.AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'SEC\s*:\s*["\']([^"\']+)["\']', panel_res.text) or
            re.search(r'AJAX_TOKEN\s*=\s*["\']([^"\']+)["\']', panel_res.text)
        )

        if not sec_match:
            await ctx.send(
                "⚠️ No pude extraer el token de inicio. La sesión de Aternos puede haber caducado.\n"
                "👉 Si persiste, renueva la variable `ATERNOS_SESSION` copiando la cookie más reciente desde tu navegador."
            )
            return

        sec_token = sec_match.group(1)

        # Paso 2: Enviar la petición de encendido con el token obtenido
        start_url = f"https://aternos.org/panel/ajax/start.php?head={sec_token}"
        start_res = scraper.get(start_url, timeout=15)

        if start_res.status_code == 200:
            try:
                resp_json = start_res.json()
                if resp_json.get("success"):
                    await ctx.send("🚀 **¡Listo!** Enviada la orden de encendido para **BelmoSMP**. En un par de minutos estará online 🎮")
                else:
                    error_msg = resp_json.get("error", "Desconocido")
                    await ctx.send(f"⚠️ Aternos respondió, pero no inició. Mensaje: `{error_msg}`")
            except Exception:
                await ctx.send("✅ Petición enviada exitosamente a Aternos. Revisa el estado con `!status` en un momento.")
        else:
            await ctx.send(f"⚠️ Error al presionar el botón: Código HTTP `{start_res.status_code}`.")

    except Exception as e:
        await ctx.send(f"❌ Ocurrió un error al conectar con Aternos:\n`{e}`")

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
        import requests
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
