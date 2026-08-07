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

# --- HELPER: LIMPIADOR DE POPUPS Y ADBLOCK ---
async def limpiar_popups_y_adblock(page):
    inicio = time.time()
    while time.time() - inicio < 5:
        try:
            btn_adblock = await page.query_selector(".btn-continue, #btn-continue, .fc-button-label, #accept-choices, .btn-accept")
            if btn_adblock and await btn_adblock.is_visible():
                await btn_adblock.click()
                await asyncio.sleep(1)

            await page.evaluate("""
                () => {
                    const selectors = [
                        '.adblock-overlay', '.fc-ab-root', '#adblock-overlay', 
                        '.modal-backdrop', '.adblock-box', '.adblock-notice'
                    ];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    });
                }
            """)
        except Exception:
            pass
        await asyncio.sleep(0.5)

# --- 3. NAVEGACIÓN CON DETECCIÓN DE TÍTULO ---
async def encender_aternos_playwright():
    session_cookie = os.getenv("ATERNOS_SESSION")
    server_id = os.getenv("ATERNOS_SERVER_ID", "TG467pziBQ20JxmN")

    if not session_cookie:
        return False, "Falta la variable `ATERNOS_SESSION` en Render."

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-gpu"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"'
            }
        )

        await context.add_cookies([{
            "name": "ATERNOS_SESSION",
            "value": session_cookie,
            "domain": ".aternos.org",
            "path": "/"
        }])

        page = await context.new_page()

        # Ocultar marca de automatización
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        async def block_resources(route):
            if route.request.resource_type in ["image", "media"]:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", block_resources)

        try:
            target_url = f"https://aternos.org/server/{server_id}/"
            await page.goto(target_url, wait_until="domcontentloaded", timeout=40000)

            # Espera estratégica para que resuelva peticiones
            await asyncio.sleep(4)
            await limpiar_popups_y_adblock(page)

            # Obtener el título de la página donde se quedó
            page_title = await page.title()

            # 1. ¿El servidor YA se está encendiendo o está Online?
            estado_encendido = await page.query_selector("#stop, .statuslabel-pre-starting, .statuslabel-starting, .statuslabel-online")
            if estado_encendido:
                return True, "¡El servidor ya se encuentra encendiéndose o ya está Online! 🟢"

            # 2. ¿Existe el botón #start en el código?
            start_exists = await page.evaluate("() => !!document.querySelector('#start')")
            
            if start_exists:
                await page.evaluate("""
                    () => {
                        document.querySelectorAll('.adblock-overlay, .fc-ab-root').forEach(el => el.remove());
                        const btn = document.querySelector('#start');
                        if (btn) btn.click();
                    }
                """)
                await asyncio.sleep(2)

                try:
                    await page.evaluate("""
                        () => {
                            const confirm = document.querySelector('#confirm, .btn-accept, .btn-confirm');
                            if (confirm) confirm.click();
                        }
                    """)
                except Exception:
                    pass

                return True, "¡Orden enviada con éxito! BelmoSMP se está encendiendo en Aternos."

            # Si no encuentra nada, devuelve el TÍTULO de la página para saber exacto qué ocurrió
            return False, f"Página cargada: **'{page_title}'** (`{page.url}`). No se vio `#start`."

        except Exception as e:
            return False, f"Error durante la navegación (`{page.url}`): {str(e)}"
        
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
        await ctx.send(f"🚀 **{message}** 🎮")
    else:
        await ctx.send(f"❌ **Error al intentar encender:** {message}")

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
