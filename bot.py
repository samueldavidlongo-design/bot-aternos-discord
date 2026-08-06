import os
import time
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
from playwright.async_api import async_playwright
import requests

# --- 1. SERVIDOR WEB 24/7 ---
app = Flask("")

@app.route('/')
def home():
    return "¡El bot de BelmoSMP está activo!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

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

# --- 3. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    await ctx.send(f"🌱 Dale **{ctx.author.name}**, abriendo navegador ligero para prender **BelmoSMP**... ⏳")
    
    if not ATERNOS_SESSION:
        await ctx.send("❌ Uy, parece que falta la cookie de sesión (`ATERNOS_SESSION`) en la configuración.")
        return

    browser = None
    try:
        async with async_playwright() as p:
            # Firefox optimizado para bajo consumo de RAM
            browser = await p.firefox.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ],
                firefox_user_prefs={
                    "browser.sessionhistory.max_entries": 2,
                    "dom.ipc.processCount": 1,
                    "image.animation_mode": "none"
                }
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
                viewport={"width": 1280, "height": 720}
            )

            # Bloquear multimedia/ads para no saturar memoria
            await context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] or any(
                domain in route.request.url for domain in [
                    "googlesyndication", "doubleclick", "adservice", "adnxs", "pagead", "google-analytics", "fontawesome"
                ]
            ) else route.continue_())

            # Cargar cookies
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

            # Ir a Aternos
            await page.goto("https://aternos.org/server/", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(3000)

            # Si nos manda a la lista de servidores, seleccionar BelmoSMP
            if "servers" in page.url or "server" not in page.url:
                await ctx.send("📋 Seleccionando **BelmoSMP**...")
                try:
                    belmo_card = page.locator("text=BelmoSMP").first
                    if await belmo_card.is_visible(timeout=3000):
                        await belmo_card.click()
                        await page.wait_for_timeout(3000)
                    else:
                        await page.locator(".server-body, .server-card, .server-name").first.click()
                        await page.wait_for_timeout(3000)
                except Exception:
                    pass

            # Manejo agresivo de emergentes/cookies de Aternos
            popups = [
                ".ncmp-btn-accept", "#accept-choices", ".btn-deny", 
                "#adblock-dialog .btn-primary", ".intro-banner-btn"
            ]
            for sel in popups:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        await page.wait_for_timeout(500)
                except Exception:
                    pass

            # Forzar un pequeño scroll por si el botón no está en viewport
            await page.evaluate("window.scrollTo(0, 300)")
            await page.wait_for_timeout(1000)

            # Buscar botón de encendido con múltiples selectores
            start_selectors = [
                "#start", 
                "#start-button", 
                "a#start", 
                "div#start", 
                "text=Start", 
                "text=Iniciar"
            ]

            start_btn = None
            for sel in start_selectors:
                loc = page.locator(sel).first
                try:
                    if await loc.is_visible(timeout=1500):
                        start_btn = loc
                        break
                except Exception:
                    continue

            if start_btn:
                await start_btn.click(force=True)
                await ctx.send("⚡ ¡Botón presionado! Revisa si entra en cola...")
                await page.wait_for_timeout(3000)

                # Confirmar cola si salta el botón verde (#confirm)
                try:
                    confirm_btn = page.locator("#confirm, .btn-confirm, text=Confirmar, text=Confirm").first
                    if await confirm_btn.is_visible(timeout=4000):
                        await confirm_btn.click(force=True)
                        await ctx.send("✅ ¡Cola/Confirmación aceptada automáticamente!")
                except Exception:
                    pass

                await ctx.send("🚀 **¡Listo!** **BelmoSMP** se está encendiendo. En breve estará listo 🎮")
            else:
                # Si no vio el botón, intentamos leer el estado
                try:
                    status_elem = page.locator(".server-status, .status-label-has-status").first
                    status_text = await status_elem.text_content(timeout=3000)
                    clean_status = status_text.strip() if status_text else "No detectado"
                except Exception:
                    clean_status = "No detectado"

                await ctx.send(f"⚠️ No vi el botón de inicio. Estado actual de BelmoSMP: `{clean_status}`.\n*(Si dice 'En línea' o 'En cola', es que ya se estaba encendiendo)*.")

            # Cerrar navegador para liberar recursos
            await context.close()
            await browser.close()

    except Exception as e:
        if browser:
            await browser.close()
        await ctx.send(f"❌ Ocurrió un detalle al encender:\n`{e}`")

# --- 4. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
    await ctx.send("🔎 Revisando cómo está **BelmoSMP**... 📡")
    
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
        try:
            res = requests.get(f"https://api.mcsrvstat.us/2/{MINECRAFT_IP}", timeout=8).json()
            if res.get("online"):
                is_online = True
                online_players = res["players"]["online"]
                max_players = res["players"]["max"]
                version = res.get("version", "Desconocida")
        except Exception:
            pass

    if is_online:
        embed = discord.Embed(
            title="🎮 BelmoSMP está Online",
            description=f"¡El servidor ya está listo! Pueden conectarse a `{MINECRAFT_IP}` ⚔️",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 Jugadores", value=f"**{online_players}/{max_players}**", inline=True)
        embed.add_field(name="⚡ Ping MC", value=f"**{ping} ms**", inline=True)
        embed.add_field(name="📶 Ping Bot", value=f"**{round(bot.latency * 1000)} ms**", inline=True)
        embed.add_field(name="📌 Versión", value=f"`{version}`", inline=False)
    else:
        embed = discord.Embed(
            title="😴 BelmoSMP está Apagado",
            description="💤 El servidor está durmiendo o cargando el mundo...\n\n👉 Pon **`!encender`** para prenderlo.",
            color=discord.Color.red()
        )
        embed.add_field(name="📶 Ping Bot", value=f"**{round(bot.latency * 1000)} ms**", inline=True)
    
    embed.set_footer(text=f"Bot activo desde hace: {uptime_str} | IP: {MINECRAFT_IP}")
    await ctx.send(embed=embed)

# --- 5. INICIO GENERAL ---
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: Falta la variable DISCORD_TOKEN en el entorno.")
