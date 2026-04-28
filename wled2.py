import paho.mqtt.client as mqtt
import json
import ssl
import logging
import time

# -------------------------
# Configuración del broker
# -------------------------

BROKER = "fd644c791000408ca8edb1d30c2d5bcb.s1.eu.hivemq.cloud"  # Host de HiveMQ Cloud
PORT = 8883                            # Puerto TLS
#PORT = 1883                            # Puerto TLS
USERNAME = "shidix"                   # Usuario HiveMQ
PASSWORD = "shShidix2005"               # Contraseña HiveMQ
TOPIC_API = "wled/spd/api"           # Topic de comandos
TOPIC_STATUS = "wled/spd/status"    # Topic de estado WLED

# -------------------------
# Habilitar logging para depuración
# -------------------------
logging.basicConfig(level=logging.DEBUG)

# -------------------------
# Mensaje JSON ejemplo
# -------------------------
payload = {
    "on": True,
    "bri": 180,
    "seg": [
        {
            "id": 0,
            "col": [[0, 255, 0]],  # Azul sólido
            "fx": 0
        }
    ]
}

# -------------------------
# Callbacks de MQTT
# -------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado al broker correctamente")
        client.subscribe(TOPIC_STATUS)
        print(f"Suscrito a topic de estado: {TOPIC_STATUS}")
    else:
        print(f"Fallo al conectar, código: {rc}")

def on_publish(client, userdata, mid):
    print(f"Mensaje publicado con ID: {mid}")

def on_message(client, userdata, msg):
    print(f"Mensaje recibido en {msg.topic}: {msg.payload.decode()}")

def on_log(client, userdata, level, buf):
    print(f"LOG: {buf}")

# -------------------------
# Crear cliente MQTT
# -------------------------
client = mqtt.Client(client_id="python_wled_trace")  # Client ID único
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(ca_certs="hivemq-ca.pem", tls_version=ssl.PROTOCOL_TLSv1_2)

client.on_connect = on_connect
client.on_publish = on_publish
client.on_message = on_message
client.on_log = on_log

# -------------------------
# Conectar y enviar mensaje
# -------------------------
client.connect(BROKER, PORT, 60)
client.loop_start()

time.sleep(1)  # Esperar a conectar

print(f"Enviando mensaje a WLED en topic {TOPIC_API}: {payload}")
result = client.publish(TOPIC_API, json.dumps(payload))

# Comprobar estado del envío
status = result[0]
if status == 0:
    print("Mensaje enviado correctamente")
else:
    print("Error al enviar mensaje")

# Mantener script activo unos segundos para recibir estado
time.sleep(5)
client.loop_stop()
client.disconnect()
print("Script finalizado")

