import os
import time
import asyncio
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests
from playwright.async_api import async_playwright

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

# --- 3. NAVEGACIÓN DIRECTA Y SELECCIÓN DE SERVIDOR ---
async def encender_aternos_playwright():
    session_cookie = os.getenv("ATERNOS_SESSION")

    if not session_cookie:
        return False, "Falta la variable `ATERNOS_SESSION` en las Environment Variables de Render."

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-gpu"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )

        # Inyectar la Cookie de Sesión activa
        await context.add_cookies([{
            "name": "ATERNOS_SESSION",
            "value": session_cookie,
            "domain": ".aternos.org",
            "path": "/"
        }])

        page = await context.new_page()

        # Bloquear imágenes/medios para máxima velocidad
        async def block_resources(route):
            if route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", block_resources)

        try:
            # 1. Entrar a Aternos
            await page.goto("https://aternos.org/servers/", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(2)

            # 2. Si hay lista de servidores, seleccionar la tarjeta del servidor
            server_card = await page.wait_for_selector(".server-body, .server-card, .servercard", timeout=10000)
            if server_card:
                await server_card.click()
                await page.wait_for_url("**/server/**", timeout=15000)

            # 3. Buscar el botón de encender (#start o botón verde con texto Iniciar)
            start_btn = await page.wait_for_selector("#start, .btn-success", timeout=20000)
            if start_btn:
                await start_btn.click()
                
                # Aceptar EULA / Confirmaciones / Notificaciones si aparecen
                try:
                    confirm_btn = await page.wait_for_selector("#confirm, .btn-accept", timeout=5000)
                    if confirm_btn:
                        await confirm_btn.click()
                except Exception:
                    pass

                return True, "¡Servidor encendido con éxito!"

            return False, "No se encontró el botón de encendido (es posible que el servidor ya se esté iniciando)."

        except Exception as e:
            return False, f"Error durante la navegación: {str(e)}"
        
        finally:
            await browser.close()

@bot.event
async def on_ready():
    print(f"🤖 Bot encendido correctamente como: {bot.user}")

# --- 4. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    await ctx.send(f"Entendido **{ctx.author.display_name}**, conectando a Aternos e iniciando **BelmoSMP**... ⚡")

    success, message = await encender_aternos_playwright()

    if success:
        await ctx.send("🚀 **¡Orden enviada con éxito!** BelmoSMP se está encendiendo en Aternos. 🎮")
    else:
        await ctx.send(f"❌ **Error al intentar encender:** `{message}`")

# --- 5. COMANDO: !status ---
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

# --- 6. INICIALIZACIÓN ---
if __name__ == "__main__":
    keep_alive()
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token:
        bot.run(discord_token)
    else:
        print("❌ ERROR: Falta DISCORD_TOKEN.")
