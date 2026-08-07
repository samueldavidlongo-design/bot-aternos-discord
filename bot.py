import os
import time
import asyncio
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands
import requests
from playwright.async_api import async_playwright

# --- 1. MANTENER VIVO EN RENDER 24/7 ---
app = Flask("")

@app.route("/")
def home():
    return "¡Zundabot Activo con Playwright! 🟢🌱"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- 2. CONFIGURACIÓN DE ZUNDABOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

BOT_START_TIME = time.time()
ZUNDA_GREEN = discord.Color.from_rgb(120, 210, 110)

# --- HELPER: RESOLVER TURNSTILE EN PLAYWRIGHT ---
async def intentar_resolver_turnstile(page):
    try:
        # 1. Buscar frame de Cloudflare Turnstile
        for frame in page.frames:
            if "cloudflare" in frame.url or "turnstile" in frame.url:
                checkbox = await frame.query_selector("input[type='checkbox'], .mark, #challenge-stage")
                if checkbox:
                    await checkbox.click()
                    await asyncio.sleep(2)
                    return True
        
        # 2. Si es un selector general en la página principal
        turnstile_element = await page.query_selector("iframe[src*='challenges.cloudflare.com']")
        if turnstile_element:
            box = await turnstile_element.bounding_box()
            if box:
                # Clic en el centro de la casilla Turnstile
                await page.mouse.click(box["x"] + 35, box["y"] + (box["height"] / 2))
                await asyncio.sleep(2)
                return True
    except Exception:
        pass
    return False

# --- HELPER: LIMPIADOR DE POPUPS Y ADBLOCK ---
async def limpiar_popups_y_adblock(page):
    inicio = time.time()
    while time.time() - inicio < 4:
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

# --- 3. NAVEGACIÓN PLAYWRIGHT ---
async def encender_aternos_playwright(status_callback=None):
    session_cookie = os.getenv("ATERNOS_SESSION")
    user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    server_id = os.getenv("ATERNOS_SERVER_ID", "TG467pziBQ20JxmN")

    async def reportar(texto):
        if status_callback:
            try:
                await status_callback(texto)
            except Exception:
                pass

    if not session_cookie:
        return False, "Falta la variable `ATERNOS_SESSION` en Render. ❌", None

    await reportar("🟢 Inicializando el navegador Zundabot... 🍃")

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
            user_agent=user_agent,
            viewport={"width": 1366, "height": 768},
            locale="es-ES"
        )

        await context.add_cookies([{
            "name": "ATERNOS_SESSION",
            "value": session_cookie,
            "domain": ".aternos.org",
            "path": "/"
        }])

        page = await context.new_page()

        # Stealth JS Script
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en-US', 'en']});
            window.chrome = { runtime: {} };
        """)

        screenshot_path = "error_screenshot.png"

        try:
            await reportar("🌱 Conectando con Aternos...")
            target_url = f"https://aternos.org/server/{server_id}/"
            await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)

            await reportar("🛡️ Verificando y superando Cloudflare... ⏳")
            
            # Reintentar interactuar con Turnstile durante unos segundos
            for _ in range(10):
                title = await page.title()
                if "Un momento" not in title and "Just a moment" not in title and title != "":
                    break
                await intentar_resolver_turnstile(page)
                await asyncio.sleep(2)

            await reportar("🧹 Preparando la interfaz...")
            await limpiar_popups_y_adblock(page)

            page_title = await page.title()

            # 1. Comprobar si ya se está encendiendo o está Online
            estado_encendido = await page.query_selector("#stop, .statuslabel-pre-starting, .statuslabel-starting, .statuslabel-online")
            if estado_encendido:
                return True, "¡El servidor ya se encuentra en proceso de encendido o ya está en línea! 🟢", None

            # 2. Intentar buscar botón #start
            await reportar("⚡ Localizando el botón de encendido (`#start`)...")
            start_exists = await page.evaluate("() => !!document.querySelector('#start')")
            
            if start_exists:
                await reportar("🟢 Presionando el botón de inicio...")
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

                return True, "¡Solicitud enviada correctamente! BelmoSMP se está encendiendo. 🟢🎮", None

            # Si vuelve a fallar, tomar captura
            await page.screenshot(path=screenshot_path, full_page=True)
            return False, f"No se encontró el botón. Título de página: **'{page_title}'**.", screenshot_path

        except Exception as e:
            try:
                await page.screenshot(path=screenshot_path, full_page=True)
            except Exception:
                screenshot_path = None
            return False, f"Error durante la conexión: `{str(e)}`", screenshot_path
        
        finally:
            await browser.close()

@bot.event
async def on_ready():
    print(f"🤖 Zundabot encendido correctamente como: {bot.user} 🟢🌱")

# --- 4. COMANDO: !encender ---
@bot.command(name="encender")
async def encender(ctx):
    msg = await ctx.send(f"🟢 **[Zundabot]** Entendido **{ctx.author.display_name}**, inicializando servidor... Por favor espera. 🍃")

    async def actualizar_mensaje(texto_nuevo):
        try:
            await msg.edit(content=f"🟢 **[Zundabot]** {texto_nuevo}")
        except Exception:
            pass

    success, result_message, screenshot_file = await encender_aternos_playwright(status_callback=actualizar_mensaje)

    if success:
        await msg.edit(content=f"🚀 **[Zundabot]** {result_message} 🍃")
    else:
        await msg.edit(content=f"❌ **[Zundabot Error]:** {result_message}")
        
        if screenshot_file and os.path.exists(screenshot_file):
            try:
                await ctx.send(
                    content="📸 **[Zundabot Capture]** Captura del estado actual:",
                    file=discord.File(screenshot_file)
                )
                os.remove(screenshot_file)
            except Exception as e:
                print(f"Error al enviar captura: {e}")

# --- 5. COMANDO: !status ---
@bot.command(name="status")
async def status(ctx):
    msg = await ctx.send("🔎 **[Zundabot]** Consultando estado del servidor... Por favor espera. 🍃")

    minecraft_ip = os.getenv("MINECRAFT_IP", "belmosmp.aternos.me")
    
    uptime_seconds = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    try:
        res = requests.get(f"https://api.mcsrvstat.us/3/{minecraft_ip}", timeout=7).json()
        
        is_online = res.get("online", False)
        
        if is_online:
            online_players = res.get("players", {}).get("online", 0)
            max_players = res.get("players", {}).get("max", 0)
            version = res.get("version", "Java Edition")
            
            player_list = res.get("players", {}).get("list", [])
            if player_list:
                players_formatted = ", ".join([p.get("name", "Jugador") for p in player_list])
            else:
                players_formatted = "Sin jugadores conectados actualmente."

            motd_raw = res.get("motd", {}).get("clean", ["¡Servidor BelmoSMP!"])
            motd_text = " ".join(motd_raw).strip() if motd_raw else "¡BelmoSMP Minecraft!"

            embed = discord.Embed(
                title="🟢 BelmoSMP está en línea",
                description=f"```{motd_text}```",
                color=ZUNDA_GREEN
            )
            embed.set_thumbnail(url="https://api.mcsrvstat.us/icon/" + minecraft_ip)
            embed.add_field(name="📌 Dirección IP", value=f"`{minecraft_ip}`", inline=True)
            embed.add_field(name="👥 Jugadores", value=f"**{online_players}/{max_players}**", inline=True)
            embed.add_field(name="⚙️ Versión", value=f"`{version}`", inline=True)
            embed.add_field(name="🎮 Jugadores en línea", value=f"{players_formatted}", inline=False)
            embed.set_footer(text=f"Zundabot activo hace: {uptime_str} 🟢 | BelmoSMP", icon_url=bot.user.display_avatar.url)
            
            await msg.edit(content="✨ **El servidor está listo para jugar.** 🟢", embed=embed)

        else:
            embed = discord.Embed(
                title="🔴 BelmoSMP está apagado",
                description="El servidor se encuentra **offline** actualmente.\n\n👉 Puedes usar **`!encender`** para iniciarlo. 🍃",
                color=discord.Color.red()
            )
            embed.add_field(name="📌 Dirección IP", value=f"`{minecraft_ip}`", inline=True)
            embed.set_footer(text=f"Zundabot activo hace: {uptime_str} 🟢", icon_url=bot.user.display_avatar.url)
            
            await msg.edit(content="🔴 **Estado del servidor:**", embed=embed)

    except Exception as e:
        await msg.edit(content=f"⚠️ **Error al consultar el estado:** `{str(e)}`")

# --- 6. INICIALIZACIÓN ---
if __name__ == "__main__":
    keep_alive()
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token:
        bot.run(discord_token)
    else:
        print("❌ ERROR: Falta DISCORD_TOKEN.")
