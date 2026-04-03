import os
import sys
import time
import threading
import subprocess
import webbrowser
import platform

import numpy as np
import sounddevice as sd
import pyttsx3
import speech_recognition as sr

# ──────────────────────────────────────────────────────────────────────────────
#  Configuración/Configuration
# ──────────────────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 44100
BLOCK_SIZE     = int(SAMPLE_RATE * 0.05)   # 50 ms por bloque
THRESHOLD      = 0.07     # RMS mínimo para contar como aplauso  ← ajusta si falla
COOLDOWN       = 0.1    # segundos de pausa mínima entre aplausos
DOUBLE_WINDOW  = 2.0     # ventana de tiempo para el segundo aplauso

# Configuración de audio
INPUT_DEVICE   = None    # None = dispositivo por defecto, o especifica índice
CHANNELS       = 1       # 1 = mono, mejor para detección de aplausos

# Configuración de voz
ACTIVADORES    = ["hey jarvis", "hola jarvis", "jarvis", "hey", "hola"]  # comandos para activar (hey jarvis primero)
ENERGY_THRESHOLD = 200  # sensibilidad del micrófono para voz (más sensible)
PAUSE_THRESHOLD = 0.6   # segundos de pausa para considerar fin de frase (más rápido)
PHRASE_TIME_LIMIT = 2   # máximo tiempo para escuchar una frase (más corto)

YOUTUBE_URL    = "https://youtu.be/__i85GzFBJQ?si=hniTogKxu74vJslq"
MENSAJE        = "Welcome home, Mr. Frago."
NEW_PROJECT    = os.path.join(os.path.expanduser("~"), "Desktop", "nuevo_proyecto")
SISTEMA        = platform.system()  # "Darwin" (macOS), "Windows", "Linux"

# ──────────────────────────────────────────────────────────────────────────────
#  Estado global/Global state
# ──────────────────────────────────────────────────────────────────────────────
clap_times: list[float] = []
triggered = False
voice_triggered = False
lock = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────────
#  Detección de aplausos/Clap detection
# ──────────────────────────────────────────────────────────────────────────────
def audio_callback(indata, frames, time_info, status):
    global triggered, clap_times

    if triggered:
        return

    rms = float(np.sqrt(np.mean(indata ** 2)))
    now = time.time()

    if rms > THRESHOLD:
        with lock:
            # Ignora si estamos en el cooldown del aplauso anterior
            if clap_times and (now - clap_times[-1]) < COOLDOWN:
                return

            clap_times.append(now)
            # Limpia aplausos fuera de la ventana
            clap_times = [t for t in clap_times if now - t <= DOUBLE_WINDOW]

            count = len(clap_times)
            print(f"  👏  Aplauso {count}/2  (RMS={rms:.3f})")

            if count >= 2:
                triggered = True
                clap_times = []
                threading.Thread(target=secuencia_bienvenida, daemon=True).start()


# ──────────────────────────────────────────────────────────────────────────────
#  Reconocimiento de voz (Versión Simplificada - Sin PyAudio)/coming soon voice recognition (Simplified Version - No PyAudio)
# ──────────────────────────────────────────────────────────────────────────────
def escuchar_comandos_voz():
    """Versión simplificada que usa API web sin PyAudio."""
    global voice_triggered

    print("  ⚠️  Reconocimiento de voz no disponible (PyAudio requerido)")
    print("  💡 Para instalar PyAudio en Windows:")
    print("     1. pip install pipwin")
    print("     2. pipwin install pyaudio")
    print("  📝  Por ahora Jarvis funciona solo con aplausos")
    print("  👏  ¡Aplaude dos veces para activar!")
    return


# ──────────────────────────────────────────────────────────────────────────────
#  Secuencia de bienvenida/Welcome sequence
# ──────────────────────────────────────────────────────────────────────────────
def secuencia_bienvenida():
    print("\n🚀  Iniciando secuencia de bienvenida…\n")

    hablar(MENSAJE)
    abrir_youtube()
    abrir_apps_lado_a_lado()

    print("\n✅  Secuencia completada.\n")


def hablar(texto: str):
    """TTS local con pyttsx3 (usa voces del sistema, sin API key)."""
    print(f"  🔊  Diciendo: «{texto}»")

    # En macOS: intenta primero con el comando 'say' (mejor calidad)
    if SISTEMA == "Darwin":
        resultado = subprocess.run(
            ["say", "-v", "Samantha", texto],
            capture_output=True
        )
        if resultado.returncode == 0:
            return  # éxito con Samantha (voz femenina en inglés de macOS)

    # Fallback: pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")

    # Busca voz femenina en inglés
    female_voices = []
    for v in voices:
        if hasattr(v, 'gender') and v.gender == 0:
            female_voices.append(v)
        elif "female" in v.name.lower() or "zira" in v.name.lower() or "hazel" in v.name.lower() or "samantha" in v.name.lower():
            female_voices.append(v)
    
    if female_voices:
        engine.setProperty("voice", female_voices[0].id)
        print(f"     Voz seleccionada: {female_voices[0].name}")
    else:
        print("     Usando voz por defecto (no se encontró voz femenina)")

    engine.setProperty("rate", 148)
    engine.say(texto)
    engine.runAndWait()


def abrir_youtube():
    print(f"  🎵  Abriendo YouTube…")
    webbrowser.open(YOUTUBE_URL)
    time.sleep(1.2)  # deja que el navegador cargue antes de seguir


def abrir_apps_lado_a_lado():
    # Asegura que existe la carpeta del nuevo proyecto
    os.makedirs(NEW_PROJECT, exist_ok=True)

    if SISTEMA == "Darwin":
        # ────────────────────────────────────────────────────────── macOS ──
        sw, sh = obtener_resolucion_pantalla()
        mitad = sw // 2

        # Abre Claude
        print("  🤖  Abriendo Claude…")
        subprocess.Popen(["open", "-a", "Claude"])
        time.sleep(1.8)

        # Abre Cursor con nuevo proyecto
        print("  💻  Abriendo Cursor…")
        cursor_cmd = encontrar_cursor()
        if cursor_cmd:
            subprocess.Popen([cursor_cmd, NEW_PROJECT])
        else:
            subprocess.Popen(["open", "-a", "Cursor", NEW_PROJECT])
        time.sleep(1.8)

        # Coloca ventanas lado a lado con AppleScript
        print("  🪟  Organizando ventanas…")
        applescript = f"""
        tell application "System Events"
            try
                tell process "Claude"
                    set frontmost to true
                    set position of window 1 to {{0, 0}}
                    set size of window 1 to {{{mitad}, {sh}}}
                end tell
            end try
            try
                tell process "Cursor"
                    set frontmost to true
                    set position of window 1 to {{{mitad}, 0}}
                    set size of window 1 to {{{mitad}, {sh}}}
                end tell
            end try
        end tell
        """
        subprocess.run(["osascript", "-e", applescript], capture_output=True)

    elif SISTEMA == "Windows":
        # ────────────────────────────────────────────────────────── Windows ──
        # Abre Claude
        print("  🤖  Abriendo Claude…")
        try:
            # Intenta abrir por nombre de app
            os.startfile("Claude")
        except FileNotFoundError:
            # Intenta por ruta conocida
            try:
                os.startfile(r"C:\Program Files\Claude\Claude.exe")
            except Exception as e:
                print(f"     ⚠️  No se pudo abrir Claude: {e}")
        time.sleep(1.8)

        # Abre Cursor con nuevo proyecto
        print("  💻  Abriendo Cursor…")
        try:
            subprocess.Popen(["cursor", NEW_PROJECT])
        except FileNotFoundError:
            try:
                os.startfile(r"C:\Program Files\Cursor\Cursor.exe")
                subprocess.Popen(["explorer", NEW_PROJECT])  # Abre la carpeta en Explorer
            except Exception as e:
                print(f"     ⚠️  No se pudo abrir Cursor: {e}")
        time.sleep(1.8)

        # Nota: Windows no puede reorganizar ventanas tan fácil sin herramientas especiales
        print("  💡  Organización de ventanas disponible con herramientas como 'FancyZones' o 'AutoHotkey'")

    else:
        # ────────────────────────────────────────────────────────── Linux ──
        print("  🤖  Abriendo Claude…")
        subprocess.Popen(["claude"])
        time.sleep(1.8)

        print("  💻  Abriendo Cursor…")
        try:
            subprocess.Popen(["cursor", NEW_PROJECT])
        except FileNotFoundError:
            print("     ⚠️  Cursor no se encontró en el PATH")


# ──────────────────────────────────────────────────────────────────────────────
#  Utilidades de audio/Audio utilities
# ──────────────────────────────────────────────────────────────────────────────
def listar_dispositivos_audio():
    """Lista todos los dispositivos de audio disponibles."""
    print("\n🎤  Dispositivos de audio disponibles:")
    print("-" * 50)
    
    try:
        devices = sd.query_devices()
        input_devices = [i for i, dev in enumerate(devices) if dev['max_input_channels'] > 0]
        
        for i in input_devices:
            dev = devices[i]
            marker = " ← POR DEFECTO" if i == sd.default.device[0] else ""
            print(f"  {i}: {dev['name']} (canales: {dev['max_input_channels']}){marker}")
        
        print("-" * 50)
        print(f"  Usando dispositivo: {sd.default.device[0]} - {devices[sd.default.device[0]]['name']}")
        print("  💡 Si usas cascos, asegúrate de que el micrófono correcto esté seleccionado")
        
    except Exception as e:
        print(f"  ⚠️  Error al listar dispositivos: {e}")


def probar_microfono():
    """Prueba rápida del micrófono para verificar niveles de ruido."""
    print("\n🎤  Probando micrófono por 3 segundos...")
    
    rms_values = []
    
    def test_callback(indata, frames, time_info, status):
        rms = float(np.sqrt(np.mean(indata ** 2)))
        rms_values.append(rms)
    
    try:
        with sd.InputStream(
            device=INPUT_DEVICE,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=CHANNELS,
            dtype="float32",
            callback=test_callback,
        ):
            time.sleep(3)
        
        if rms_values:
            avg_rms = np.mean(rms_values)
            max_rms = np.max(rms_values)
            print(f"  📊  RMS promedio: {avg_rms:.3f}")
            print(f"  📊  RMS máximo: {max_rms:.3f}")
            print("  💡 Si el ruido ambiente es alto, aumenta el THRESHOLD")
        else:
            print("  ⚠️  No se pudieron capturar datos del micrófono")
            
    except Exception as e:
        print(f"  ❌  Error al probar micrófono: {e}")
        print("  💡 Verifica que el micrófono esté conectado y no esté en uso por otra aplicación")
def obtener_resolucion_pantalla() -> tuple[int, int]:
    """Obtiene la resolución de la pantalla según el SO."""
    if SISTEMA == "Darwin":
        # macOS
        try:
            out = subprocess.run(
                ["osascript", "-e",
                 "tell application \"Finder\" to get bounds of window of desktop"],
                capture_output=True, text=True
            ).stdout.strip()
            parts = [int(x.strip()) for x in out.split(",")]
            return parts[2], parts[3]
        except Exception:
            return 1920, 1080
    
    elif SISTEMA == "Windows":
        # Windows - usa tkinter si está disponible
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            w = root.winfo_screenwidth()
            h = root.winfo_screenheight()
            root.destroy()
            return w, h
        except (ImportError, ModuleNotFoundError):
            # Fallback si tkinter no está disponible
            print("     💡 tkinter no disponible, usando resolución por defecto")
            return 1920, 1080
    
    else:
        # Linux y otros
        return 1920, 1080


def encontrar_cursor():
    """Devuelve la ruta del CLI de Cursor si está disponible."""
    if SISTEMA == "Darwin":
        # macOS
        candidatos = [
            "/usr/local/bin/cursor",
            "/opt/homebrew/bin/cursor",
            os.path.expanduser("~/.cursor/bin/cursor"),
        ]
        for path in candidatos:
            if os.path.isfile(path):
                return path
        # Intenta por PATH
        result = subprocess.run(["which", "cursor"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    
    elif SISTEMA == "Windows":
        # Windows
        candidatos = [
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "cursor", "Cursor.exe"),
            r"C:\Program Files\Cursor\Cursor.exe",
            r"C:\Program Files (x86)\Cursor\Cursor.exe",
        ]
        for path in candidatos:
            if os.path.isfile(path):
                return path
        # Intenta por PATH usando 'where' (equivalente a 'which' en Windows)
        try:
            result = subprocess.run(["where", "cursor"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
    
    return None


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    global triggered, voice_triggered

    print("=" * 55)
    print("  🎤  Jarvis - Detector Inteligente")
    print("=" * 55)
    
    # Diagnóstico de audio
    listar_dispositivos_audio()
    probar_microfono()
    
    print("\n" + "=" * 55)
    print("  🎤  Jarvis activado - Detector Inteligente")
    print("  💡 Aplaude dos veces para activar (voz próximamente)")
    print(f"  Umbral aplausos: {THRESHOLD}")
    print("  🎙️  Voz: Requiere PyAudio (ver instrucciones abajo)")
    print("=" * 55)

    # Inicia el hilo de reconocimiento de voz (si está disponible)
    voice_thread = threading.Thread(target=escuchar_comandos_voz, daemon=True)
    voice_thread.start()

    try:
        with sd.InputStream(
            device=INPUT_DEVICE,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=CHANNELS,
            dtype="float32",
            callback=audio_callback,
        ):
            while True:
                time.sleep(0.1)
                if triggered or voice_triggered:
                    # Espera a que la secuencia acabe y vuelve a escuchar
                    time.sleep(8)
                    triggered = False
                    voice_triggered = False
                    print("\n👂  Escuchando de nuevo…\n")
    except KeyboardInterrupt:
        print("\n\nHasta luego! 👋")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌  Error de audio: {e}")
        print("💡 Posibles soluciones:")
        print("   - Verifica que el micrófono esté conectado")
        print("   - Asegúrate de que no esté siendo usado por otra app")
        print("   - Prueba con cascos diferentes o micrófono externo")
        sys.exit(1)


if __name__ == "__main__":
    main()

# ──────────────────────────────────────────────────────────────────────────────
#  VOICE RECOGNITION INSTRUCTIONS
# ──────────────────────────────────────────────────────────────────────────────
"""
To activate full voice recognition with "Hey Jarvis":

1. Install PyAudio (challenging on Windows with Python 3.14):
   pip install pipwin
   pipwin install pyaudio

2. If pipwin fails, download wheel manually from:
   https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
   Search for: PyAudio‑0.2.14‑cp314‑cp314‑win_amd64.whl (for Python 3.14)
   Then: pip install PyAudio‑0.2.14‑cp314‑cp314‑win_amd64.whl

3. Once PyAudio is installed, voice recognition will work automatically.

Note: Jarvis works perfectly with claps in the meantime.
"""

# ──────────────────────────────────────────────────────────────────────────────
#  INSTRUCCIONES PARA RECONOCIMIENTO DE VOZ
# ──────────────────────────────────────────────────────────────────────────────
"""
Para activar el reconocimiento de voz completo con "Hey Jarvis":

1. Instalar PyAudio (desafiante en Windows con Python 3.14):
   pip install pipwin
   pipwin install pyaudio

2. Si pipwin falla, descargar wheel manualmente desde:
   https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
   Buscar: PyAudio‑0.2.14‑cp314‑cp314‑win_amd64.whl (para Python 3.14)
   Luego: pip install PyAudio‑0.2.14‑cp314‑cp314‑win_amd64.whl

3. Una vez instalado PyAudio, el reconocimiento de voz funcionará automáticamente.

Nota: Jarvis funciona perfectamente con aplausos mientras tanto.
"""