from machine import Pin, PWM, I2C, disable_irq, enable_irq, ADC
from ssd1306 import SSD1306_I2C , framebuf
from time import sleep_ms, sleep_us, sleep
from effect_definitions import base_color_effects, special_effects, tail_codes
from ir_rx.nec import NEC_16
import time
import network
import ntptime
import gc
import math # Necesario para el vúmetro radial



#------------------- OLED Y MICROFONO ------------------
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
ledIR = PWM(Pin(4), freq=38000, duty=0)

# Configuración del micrófono (Pin 34, ajustar si usan otro)
mic = ADC(Pin(34))
mic.atten(ADC.ATTN_11DB)
mic.width(ADC.WIDTH_11BIT)

#-------------------CONFIGURACIÓN WIFI------------------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("iPhone de Sara", "sara12345")

print("Conectando WiFi...")
intentos = 0
while not wifi.isconnected() and intentos < 20:
    sleep_ms(500)
    intentos += 1

if wifi.isconnected():
    print("WiFi OK")
    try:
        ntptime.settime()
        print("Hora sincronizada")
    except:
        print("Fallo NTP")
else:
    print("WiFi Falló, continuando sin red")
gc.collect()


#------------FECHA Y HORA-------
def obtener_fecha_hora():
    t = time.localtime(time.time() - 5*3600)
    fecha = "{:02d}/{:02d}/{}".format(t[2], t[1], t[0])
    hora2 = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    return fecha, hora2

def dibujar_hora():
    _, hora2 = obtener_fecha_hora()
    oled.text(hora2, 60, 0)
    
#------------------- PANTALLA INICIAL ------------------
def pantalla_inicial(duracion=5):
    inicio = time.time()
    while time.time() - inicio < duracion:
        fecha, hora2 = obtener_fecha_hora()
        oled.fill(0)
        oled.text("FECHA:", 0, 10)
        oled.text(fecha, 0, 20)
        oled.text("HORA:", 0, 40)
        oled.text(hora2, 0, 50)
        oled.show()
        sleep(1)

# ---------------- SCROLL ----------------
def scroll_texto(texto, velocidad=40):
    for y in range(64, 14, -1):
        oled.fill(0)
        dibujar_hora()
        oled.text(texto, 0, y)
        oled.show()
        sleep_ms(velocidad)
        
y_scroll = 64  
def scroll_nombres_step(textos):
    global y_scroll
    altura = 10
    total = len(textos) * altura
    oled.fill(0)
    dibujar_hora()
    for i, texto in enumerate(textos):
        y_pos = y_scroll + i * altura
        if 0 <= y_pos <= 45:          # ← Solo dibuja si está en pantalla
            oled.text(texto, 0, y_pos)
    oled.show()
    y_scroll -= 1
    if y_scroll < -total:
        y_scroll = 64
        

# ------------------ EFECTOS ------------------
color1 = special_effects["SLOW_WHITE"]
colorSaraM = base_color_effects["TURQUOISE"] 
colorSaraS = base_color_effects["MAGENTA"] 

nuevo1 = [int(bit) * 700 for bit in color1]
nuevo2 = [int(bit) * 700 for bit in colorSaraM]
nuevo3 = [int(bit) * 700 for bit in colorSaraS]

# ------------------ ESTADO ------------------
modo = -1  # 0: TURQUOISE, 1: WHITE, 2: MAGENTA, 3: IMG, 4: ICON, 5: SCROLL, 6: VUMETRO
modo_actual = -2
enviar_ir = False
ultimo_update_oled = 0
tiempo_inicio_animacion = 0
DURACION_ANIMACION = 20000  # 8 segundos, ajusta a gusto
animacion_activa = False
ir_cmd = -1

# ------------------ CONVERSIÓN ------------------
def convertir_trama(data):
    if not data: return []
    resultado = []
    estado_actual = data[0] != 0
    acumulado = 700
    for i in range(1, len(data)):
        estado = data[i] != 0
        if estado == estado_actual:
            acumulado += 700
        else:
            resultado.append(acumulado)
            acumulado = 700
            estado_actual = estado
    resultado.append(acumulado)
    if len(resultado) % 2 != 0:
        resultado.append(700)
    return resultado

# ------------------ ENVIAR (BLINDADO) ------------------
def enviar(trama):
    # ¡Mejora inyectada! Apagar interrupciones para asegurar el Pixmob
    estado_irq = disable_irq()
    try:
        for i, duracion in enumerate(trama):
            if i % 2 == 0:
                ledIR.duty(512)
            else:
                ledIR.duty(0)
            sleep_us(duracion)
    finally:
        ledIR.duty(0)
        enable_irq(estado_irq)
#-------------------MICROFONO--------------
x_ecg = 0
y_prev_ecg = 0
baseline_ecg = None
Y_TOP = 12
Y_BOTTOM = 63
Y_CENTER = (Y_TOP + Y_BOTTOM) // 2
GAIN = 0.6
ALPHA = 0.99
#-------------------ICONO------------------
peace_sign = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,1,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,0,0,0,0,0,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,1,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,1,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,1,1,1,1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,1,1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,0,0,1,1,1,0,0,0,1,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,1,0,0,1,1,0,0,0,0,0,0,1,1,1,1,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,1,0,0,0,0,0,0,0,0,0,1,1,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,1,1,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,1,1,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,1,1,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1,1,1,0,0,0,1,1,1,1,1,0,0,1,1,1,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
]

def mostrar_icono():
    oled.fill(0)
    for y in range(64):
        for x in range(64):
            if peace_sign[y][x] == 1:
                oled.pixel(x+32, y, 1)  # centrado
    dibujar_hora()
    oled.show()


# ------------------ IMAGEN (MEJORADA MEMORIA) ------------------
def mostrar_imagen():
    oled.fill(0)
    try:
        # Abre, dibuja y destruye para salvar RAM
        with open("spiderman.pbm", 'rb') as f:
            f.readline()
            f.readline()
            bitmap_data = bytearray(f.read())
        
        fbuf = framebuf.FrameBuffer(bitmap_data, 64, 64, framebuf.MONO_HLSB)
        oled.blit(fbuf, 32, 0)
        
        del fbuf
        del bitmap_data
        gc.collect()
        
    except Exception as e:
        oled.text("IMG ERR", 30, 30)
        
    dibujar_hora()
    oled.show()
#-------------------GATICO-----------------------
def dibujar_gatito():
    oled.fill(0)
    # Cabeza
    oled.rect(34, 18, 60, 35, 1)
    # Orejas
    oled.line(34, 18, 20, 5, 1)
    oled.line(20, 5, 45, 18, 1)
    oled.line(94, 18, 110, 5, 1)
    oled.line(110, 5, 80, 18, 1)
    # Ojos
    oled.fill_rect(50, 30, 4, 4, 1)
    oled.fill_rect(75, 30, 4, 4, 1)
    # Nariz
    oled.fill_rect(62, 40, 6, 4, 1)
    # Boca
    oled.line(65, 44, 55, 50, 1)
    oled.line(65, 44, 75, 50, 1)
    # Bigotes
    oled.hline(40, 42, 10, 1)
    oled.hline(80, 42, 10, 1)
    # Cuerpo
    oled.rect(40, 53, 50, 10, 1)
    # Patas
    oled.vline(45, 63, 5, 1)
    oled.vline(55, 63, 5, 1)
    oled.vline(75, 63, 5, 1)
    oled.vline(85, 63, 5, 1)
    # Cola
    oled.line(90, 55, 105, 45, 1)
    dibujar_hora()   # ← hora estática encima
    oled.show()
# ------------------ VÚMETRO RADIAL (NUEVO DISEÑO) ------------------
def dibujar_linea(x0, y0, longitud, angulo_grados):
    # Convierte grados a radianes y calcula el punto final
    angulo_rad = math.radians(angulo_grados)
    x1 = int(x0 + longitud * math.cos(angulo_rad))
    # Restamos y porque en la pantalla la Y crece hacia abajo
    y1 = int(y0 - longitud * math.sin(angulo_rad)) 
    oled.line(x0, y0, x1, y1, 1)

def dibujar_ecg():
    global x_ecg, y_prev_ecg, baseline_ecg
    val = mic.read()
    if baseline_ecg is None:
        baseline_ecg = val
    else:
        baseline_ecg = ALPHA * baseline_ecg + (1 - ALPHA) * val
    ac = (val - baseline_ecg) * GAIN
    umbral =12
    if abs(ac)< umbral:
        ac=0
    half_range = (Y_BOTTOM - Y_TOP) // 2
    ac = max(-half_range, min(half_range, ac))
    y = int(Y_CENTER - ac)
    oled.vline(x_ecg, Y_TOP, Y_BOTTOM - Y_TOP, 0)
    if x_ecg > 0:
        oled.line(x_ecg - 1, y_prev_ecg, x_ecg, y, 1)
    y_prev_ecg = y
    x_ecg += 1
    if x_ecg >= 128:
        x_ecg = 0

def animar_ecg_step():
    print(mic.read())
    dibujar_hora()
    dibujar_ecg()
    oled.show()

# ------------------ RECEPCIÓN IR ------------------

def ir_callback(data, addr, ctrl):
    global ir_cmd
    if data is None or data < 0:
        return
    ir_cmd = data
        
def procesar_boton(data):
    global modo, enviar_ir
    if data == 0x01: modo, enviar_ir = 0, True
    elif data == 0x02: modo, enviar_ir = 1, True
    elif data == 0x03: modo, enviar_ir = 2, True
    elif data == 0x04: modo = 3 # Imagen
    elif data == 0x05: modo = 4 # Icono
    elif data == 0x06: modo = 5 # Scroll
    elif data == 0x07: modo = 6 # Vumetro Radial
    elif data == 0x08: modo = 7
    


# ------------------ INICIALIZAR RECEPTOR IR ------------------
ir = NEC_16(Pin(17), ir_callback)

# ------------------ LOOP PRINCIPAL ------------------
pantalla_inicial(5)
scroll_texto("Dios te bendiga", 40)
oled.fill(0)
dibujar_hora()
oled.show()

while True:
    
    # 1. PROCESAR IR
    if ir_cmd != -1:
        cmd = ir_cmd
        ir_cmd = -1       # Limpiar primero antes de procesar
        procesar_boton(cmd)
        modo_actual = -2  # Forzar refresco
    
    if enviar_ir:
       
        if modo == 0:
            print("IR TURQUOISE")
            for _ in range(10):
                enviar(convertir_trama(nuevo2))
                sleep_ms(1000)
            enviar_ir = False
        elif modo == 1:
            print("IR WHITE")
            for _ in range(10):
                enviar(convertir_trama(nuevo1))
                sleep_ms(1000)
            enviar_ir = False
        elif modo == 2:
            print("IR MAGENTA")
            for _ in range(10):
                enviar(convertir_trama(nuevo3))
                sleep_ms(1000)
            enviar_ir = False
        
    # 2. OLED (Manejo de pantallas estáticas)
    if modo != modo_actual:
        modo_actual = modo
        print("Mostrar modo:", modo)
        
        if modo in [0,1,2]:
            oled.fill(0)
            dibujar_hora()
            oled.show()
        elif modo == 3:
            mostrar_imagen()
        elif modo == 4:
            mostrar_icono()
        elif modo == 5:
            y_scroll = 64
            tiempo_inicio_animacion = time.ticks_ms()
            animacion_activa = True
        elif modo == 6:
            tiempo_inicio_animacion = time.ticks_ms()
            animacion_activa = True
            x_ecg = 0
            y_prev_ecg = Y_CENTER
            baseline_ecg = None
            oled.fill(0)   # Limpia una sola vez al entrar
            oled.show()
        elif modo == 7:
            dibujar_gatito()
        
    # 3. ANIMACIONES CONTINUAS
    if modo == 5 and animacion_activa:
        if time.ticks_diff(time.ticks_ms(), tiempo_inicio_animacion) > DURACION_ANIMACION:
            modo = -1       # Volver al modo base
            modo_actual = -2  # Forzar refresco de pantalla
            animacion_activa = False
        else:
            scroll_nombres_step(["Sara Salamanca", "Sara Marin"])

    elif modo == 6 and animacion_activa:
        if time.ticks_diff(time.ticks_ms(), tiempo_inicio_animacion) > DURACION_ANIMACION:
            modo = -1
            modo_actual = -2
            animacion_activa = False
        else:
            animar_ecg_step()

    # 4. MODO BASE (SIN BOTÓN)
    if modo == -1:
        ahora = time.ticks_ms()
        if time.ticks_diff(ahora, ultimo_update_oled) >= 1000:  # Solo cada 500ms
            ultimo_update_oled = ahora
            oled.fill(0)
            dibujar_hora()
            oled.show()

    # Pequeña pausa para no saturar I2C y permitir escuchar Infrarrojo
    sleep_ms(10)
