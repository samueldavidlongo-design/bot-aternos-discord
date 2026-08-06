import os
from threading import Thread
import time
from flask import Flask
import discord
from discord.ext import commands
import requests
from playwright.async_api import async_playwright

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
    print(f"¡Bot conectado exitosamente como {bot.user}!")

# --- 3. COMANDO: !encender (Con protecciones anti-anuncios, anti-popups y detector de servidor) ---
@bot.command(name="encender")
async def encender(ctx):
    await ctx.send(f"🔄 **{ctx.author.name}**, abriendo navegador headless para conectar con Aternos... ⏳")

    if not ATERNOS_SESSION:
        await ctx.send("❌ Error: Falta configurar la variable `ATERNOS_SESSION` en Render.")
        return

    browser = None
    try:
        async with async_playwright() as p:
            # Lanzamos Firefox en modo headless
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
                viewport={"width": 1280, "height": 720} # Tamaño de pantalla HD para asegurar que los botones sean visibles
            )

            # 🛡️ PROTECCIÓN ANTI-ANUNCIOS: Bloquear llamadas a Google Ads, AdSense y scripts de publicidad
            await context.route("**/*", lambda route: (
                route.abort() if any(domain in route.request.url for domain in [
                    "googlesyndication", "doubleclick", "adservice", "adnxs", "pagead", "google-analytics"
                ]) else route.continue_()
            ))

            # 1. Inyectar Cookie de Sesión
            cookies = []
            for item in ATERNOS_SESSION.split(";"):
                if "=" in item:
                    name, val = item.strip().split("=", 1)
                    cookies.append({
                        "name": name,
                        "value": val,
                        "domain": ".aternos.org",
                        "path": "/"
                    })
            await context.add_cookies(cookies)

            page = await context.new_page()

            # 2. Entrar a la lista de servidores
            await page.goto("https://aternos.org/servers/", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000)

            # --- DETECTOR 1: Selección de servidor en la lista ---
            if "/servers" in page.url:
                await ctx.send("📋 Seleccionando servidor de la lista...")
                server_card = page.locator(".server-body, .server-card, .server-name").first
                if await server_card.is_visible(timeout=5000):
                    await server_card.click()
                    await page.wait_for_timeout(2000)

            # --- DETECTOR 2: Cerrar Popups de Notificaciones, Cookies o AdBlock ---
            popups_to_close = [
                ".ncmp-btn-accept",            # Aceptar Cookies GDPR
                "#accept-choices",             # Aceptar cookies alternativo
                ".btn-deny",                   # Denegar notificaciones push
                ".alert-dismissible .btn-close",# Avisos flotantes
                "#adblock-dialog .btn-primary" # Diálogo de aviso de AdBlock
            ]
            for selector in popups_to_close:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        await page.wait_for_timeout(500)
                except Exception:
                    pass

            # --- DETECTOR 3: Pulsar el Botón de Iniciar (#start) ---
            start_btn = page.locator("#start")

            if await start_btn.is_visible(timeout=8000):
                # Forzar el clic incluso si hay una capa transparente o anuncio encima
                await start_btn.click(force=True)
                await ctx.send("⌛ Botón **Iniciar** presionado. Verificando si requiere confirmación de cola...")
                await page.wait_for_timeout(3000)

                # --- DETECTOR 4: Confirmación de cola o EULA (#confirm) ---
                try:
                    confirm_btn = page.locator("#confirm")
                    if await confirm_btn.is_visible(timeout=4000):
                        await confirm_btn.click(force=True)
                        await ctx.send("✅ ¡Confirmación de cola aceptada automáticamente!")
                except Exception:
                    pass

                await ctx.send(f"🚀 ¡Orden procesada con éxito por **{ctx.author.name}**! El servidor se está iniciando en Aternos.")
            else:
                # Si no se ve el botón, obtener el estado actual en texto
                try:
                    status_elem = page.locator(".server-status")
                    status_text = await status_elem.text_content(timeout=3000)
                    clean_status = status_text.strip() if status_text else "Desconocido"
                except Exception:
                    clean_status = "No detectado"

                await ctx.send(f"⚠️ No se encontró el botón de inicio. Estado detectado en Aternos: `{clean_status}`.")

            await browser.close()

    except Exception as e:
        if browser:
            await browser.close()
        await ctx.send(f"❌ Error durante la automatización en Aternos:\n`{e}`")

# --- 4. COMANDO: !status (Información de Minecraft) ---
@bot.command(name="status")
async def status(ctx):
    await ctx.send("🔎 Consultando el estado del servidor de Minecraft... 📡")

    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    is_online = False
    online_players = 0
    max_players = 0
    ping = "N/A"
    version = "Desconocida"

    # API Principal
    try:
        res = requests.get(f"https://api.mcstatus.io/v2/status/java/{MINECRAFT_IP}", timeout=10).json()
        if res.get("online"):
            is_online = True
            online_players = res["players"]["online"]
            max_players = res["players"]["max"]
            ping = res.get("roundTripLatency", "N/A")
            version = res.get("version", {}).get("name_clean", "Desconocida")
    except Exception:
        # API de Respaldo
        try:
            res = requests.get(f"https://api.mcsrvstat.us/2/{MINECRAFT_IP}", timeout=10).json()
            if res.get("online"):
                is_online = True
                online_players = res["players"]["online"]
                max_players = res["players"]["max"]
                version = res.get("version", "Desconocida")
        except Exception:
            pass

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
            description="💤 *El servidor está apagado o en proceso de encendido...*\n\n👉 Escribe **`!encender`** para iniciar Aternos.",
            color=discord.Color.red()
        )
        embed.add_field(name="📶 Ping Bot", value=f"**{round(bot.latency * 1000)} ms**", inline=True)

    embed.set_footer(text=f"Bot activo en Render desde hace: {uptime_str} | IP: {MINECRAFT_IP}")
    await ctx.send(embed=embed)

# --- 5. INICIO GENERAL ---
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: Falta la variable DISCORD_TOKEN.")
