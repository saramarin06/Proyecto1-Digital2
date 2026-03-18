from machine import mem32, ADC, Pin, PWM 
import time


#FUNCIONES SEMAFORO 
def esperar_aplauso():

    print("Esperando aplauso para iniciar...")

    while True:

        valor = mic.read()

        if valor > UMBRAL_APLAUSO:
            print("Aplauso detectado!")
            time.sleep(1)
            break

def titilar_verde(pin_verde, estado_base):
    
    for i in range(3):

        mem32[GPIO_OUT] = estado_base
        time.sleep(0.3)

        mem32[GPIO_OUT] = estado_base & ~pin_verde
        time.sleep(0.3)

def ISR_boton(pin):
    global boton_peaton, tiempo_boton
    print("Boton presionado")
    boton_peaton = True
    tiempo_boton = time.time()


def cruce_peatonal():

    mem32[GPIO_OUT] = PEATON_VERDE

    contador_peatonal(23)

    mem32[GPIO_OUT] = ROJO_PEATON

def revisar_peaton():

    global boton_peaton

    if boton_peaton and (time.time() - tiempo_boton) >= 5:

        cruce_peatonal()
        boton_peaton = False
        return True

    return False

# Esta función espera un número determinado de segundos, pero si el botón de peatón es presionado durante ese tiempo, retorna True inmediatamente. Revisa la bandera cada cierto tiempo (en este caso, cada 0.1 segundos) para no bloquear completamente el programa. Si el tiempo se agota sin que se presione el botón, retorna False.
def esperar(segundos):

    global boton_peaton

    pasos = int(segundos * 10)

    for i in range(pasos):

        if boton_peaton and (time.time() - tiempo_boton) >= 5:
            return True

        time.sleep(0.1)

    return False


#FUNCIONES DEL DISPLAY
#para mostar cada display 
def set_segments(pattern):

    for i in range(7):
        segments[i].value(pattern[i])

#para la multiplexacion de los displays
def mostrar_numero(num):

    dec = num // 10
    uni = num % 10

    # DECENAS
    disp_dec.duty(VALORPOT)
    disp_uni.duty(0)
    set_segments(DIGITOS[dec])
    time.sleep_ms(5)

    # UNIDADES
    disp_dec.duty(0)
    disp_uni.duty(VALORPOT)
    set_segments(DIGITOS[uni])
    time.sleep_ms(5)

def contador_peatonal(segundos):

    for i in range(segundos, -1, -1):

        inicio = time.time()

        while time.time() - inicio < 1:

            mostrar_numero(i)



#-----------------------------------------

#microfono
UMBRAL_APLAUSO = 2000 #para microfono 
mic = ADC(Pin(34))
mic.atten(ADC.ATTN_11DB)
mic.width(ADC.WIDTH_12BIT)

#boton
boton_peaton = False #para pulsador, interruptor
tiempo_boton = 0
boton = Pin(39, Pin.IN, Pin.PULL_DOWN)   
boton.irq(trigger=Pin.IRQ_FALLING, handler=ISR_boton)

#potenciometro
#VALORPOT=  queda pendiente esta parte del poitemciometro
GPIO_ENABLE = 0x3FF44020
GPIO_OUT = 0x3FF44004

#macaras binarias para cada luz del semaforo, cada una en un bit diferente para poder combinarlas facilmente con operaciones bit a bit
ROJO_CALLE =      0b00000000000001000000000000000000
AMARILLO_CALLE =  0b00000000000010000000000000000000
VERDE_CALLE =     0b00000000001000000000000000000000

ROJO_CARRERA =    0b00000000010000000000000000000000
AMARILLO_CARRERA =0b00000000100000000000000000000000
VERDE_CARRERA =   0b00000010000000000000000000000000

ROJO_PEATON =     0b00000100000000000000000000000000
VERDE_PEATON =    0b00001000000000000000000000000000

#mascaras binarias para cada segmento 
a = Pin(12, Pin.OUT)
b = Pin(14, Pin.OUT)
c = Pin(2, Pin.OUT)
d = Pin(13, Pin.OUT)
e = Pin(16, Pin.OUT)
f = Pin(17, Pin.OUT)
g = Pin(4, Pin.OUT)

segments = [a,b,c,d,e,f,g]

disp_dec = PWM(5, Pin.OUT)
disp_uni = PWM(0, Pin.OUT)


mem32[GPIO_ENABLE] |= (
ROJO_CALLE |
AMARILLO_CALLE |
VERDE_CALLE |
ROJO_CARRERA |
AMARILLO_CARRERA |
VERDE_CARRERA |
ROJO_PEATON |
VERDE_PEATON 
)

#numeros display 
DIGITOS = [

[1,1,1,1,1,1,0], #0
[0,1,1,0,0,0,0], #1
[1,1,0,1,1,0,1], #2
[1,1,1,1,0,0,1], #3
[0,1,1,0,0,1,1], #4
[1,0,1,1,0,1,1], #5
[1,0,1,1,1,1,1], #6
[1,1,1,0,0,0,0], #7
[1,1,1,1,1,1,1], #8
[1,1,1,1,0,1,1]  #9

]

#estados
PEATON_VERDE = VERDE_PEATON | ROJO_CALLE | ROJO_CARRERA
CALLE_VERDE = VERDE_CALLE | ROJO_CARRERA | ROJO_PEATON
CALLE_AMARILLO = AMARILLO_CALLE | ROJO_CARRERA | ROJO_PEATON
CARRERA_VERDE = ROJO_CALLE | VERDE_CARRERA | ROJO_PEATON
CARRERA_AMARILLO = ROJO_CALLE | AMARILLO_CARRERA | ROJO_PEATON


#INICIALIZACIÓN
esperar_aplauso()

#CICLO PRINCIPAL
while True:

    mem32[GPIO_OUT] = CALLE_VERDE

    if esperar(5):

        if boton_peaton and (time.time() - tiempo_boton) >= 5:
            cruce_peatonal()
            boton_peaton = False
            continue


    titilar_verde(VERDE_CALLE, CALLE_VERDE)

    mem32[GPIO_OUT] = CALLE_AMARILLO

    if esperar(5):

        if boton_peaton and (time.time() - tiempo_boton) >= 5:
            cruce_peatonal()
            boton_peaton = False
            continue


    mem32[GPIO_OUT] = CARRERA_VERDE

    if esperar(5):

        if boton_peaton and (time.time() - tiempo_boton) >= 5:
            cruce_peatonal()
            boton_peaton = False
            continue


    titilar_verde(VERDE_CARRERA, CARRERA_VERDE)

    mem32[GPIO_OUT] = CARRERA_AMARILLO

    if esperar(5):

        if boton_peaton and (time.time() - tiempo_boton) >= 5:
            cruce_peatonal()
            boton_peaton = False
            continue

