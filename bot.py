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
    return "¡El bot de BelmoSMP está activo!"

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

# --- 3. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    await ctx.send(f"🌱 Dale **{ctx.author.name}**, ya estoy entrando a Aternos para prender **BelmoSMP**... dame unos segundos ⏳")

    if not ATERNOS_SESSION:
        await ctx.send("❌ Uy, parece que falta la cookie de sesión (`ATERNOS_SESSION`) en la configuración.")
        return

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
                viewport={"width": 1280, "height": 720}
            )

            # Bloquear publicidad molesta para que cargue más rápido
            await context.route("**/*", lambda route: (
                route.abort() if any(domain in route.request.url for domain in [
                    "googlesyndication", "doubleclick", "adservice", "adnxs", "pagead", "google-analytics"
                ]) else route.continue_()
            ))

            # Cargar la sesión
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

            # Entrar directamente al panel del servidor
            await page.goto("https://aternos.org/server/", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(3000)

            # Si salta la pantalla de elegir servidor, seleccionar BelmoSMP
            if "/servers" in page.url:
                await ctx.send("📋 Seleccionando **BelmoSMP**...")
                belmo_card = page.locator("text=BelmoSMP").first
                if await belmo_card.is_visible(timeout=5000):
                    await belmo_card.click()
                    await page.wait_for_timeout(3000)
                else:
                    await page.locator(".server-body, .server-card").first.click()
                    await page.wait_for_timeout(3000)

            # Cerrar avisos o ventanas emergentes si salen
            popups = [".ncmp-btn-accept", "#accept-choices", ".btn-deny", "#adblock-dialog .btn-primary"]
            for sel in popups:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                except Exception:
                    pass

            # Buscar y pulsar el botón de encender
            start_btn = page.locator("#start")

            if await start_btn.is_visible(timeout=8000):
                await start_btn.click(force=True)
                await ctx.send("⚡ Ya le di al botón de encender, revisando si hay cola de espera...")
                await page.wait_for_timeout(3000)

                # Si pide confirmar cola o algo extra
                try:
                    confirm_btn = page.locator("#confirm")
                    if await confirm_btn.is_visible(timeout=4000):
                        await confirm_btn.click(force=True)
                        await ctx.send("✅ ¡Confirmé la cola de espera automáticamente!")
                except Exception:
                    pass

                await ctx.send(f"🚀 **¡Listo!** **BelmoSMP** se está inicializando. En un ratito ya pueden entrar a jugar 🎮")
            else:
                # Si no sale el botón, ver qué estado marca la página
                try:
                    status_elem = page.locator(".server-status")
                    status_text = await status_elem.text_content(timeout=3000)
                    clean_status = status_text.strip() if status_text else "Desconocido"
                except Exception:
                    clean_status = "No detectado"

                await ctx.send(f"⚠️ No pude pulsar el botón. Parece que el servidor está en estado: `{clean_status}` (o tal vez ya se está encendiendo).")

            await browser.close()

    except Exception as e:
        if browser:
            await browser.close()
        await ctx.send(f"❌ Ocurrió un detalle al intentar encender el servidor:\n`{e}`")

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

    # Intentar consultar el estado con la API principal
    try:
        res = requests.get(f"https://api.mcstatus.io/v2/status/java/{MINECRAFT_IP}", timeout=10).json()
        if res.get("online"):
            is_online = True
            online_players = res["players"]["online"]
            max_players = res["players"]["max"]
            ping = res.get("roundTripLatency", "N/A")
            version = res.get("version", {}).get("name_clean", "Desconocida")
    except Exception:
        # API de respaldo por si acaso
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
            title=f"🎮 BelmoSMP está Online",
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
