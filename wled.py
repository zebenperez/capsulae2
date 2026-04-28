import paho.mqtt.client as mqtt
import json
import ssl

# -------------------------
# Configuración del broker
# -------------------------
BROKER = "fd644c791000408ca8edb1d30c2d5bcb.s1.eu.hivemq.cloud"  # Host de HiveMQ Cloud
PORT = 8883                            # Puerto TLS
USERNAME = "shidix"                   # Usuario HiveMQ
PASSWORD = "shShidix2005"               # Contraseña HiveMQ
TOPIC = "wled/spd/api"               # Topic base + /api

# -------------------------
# Mensaje JSON para WLED
# -------------------------
payload = {
    "on": True,
    "bri": 180,
    "seg": [{"id": 0, "col": [[255, 0, 0]], "fx": 0}]  # Azul sólido
}

def on_connect(client, userdata, flags, rc):
    print("Conectado al broker, código de resultado:", rc)

def on_publish(client, userdata, mid):
    print("Mensaje publicado con ID:", mid)

def on_log(client, userdata, level, buf):
    print("LOG:", buf)

# -------------------------
# Crear cliente MQTT
# -------------------------
client = mqtt.Client(client_id="python_wled_cloud")  # Client ID único

# Configurar usuario y password
client.username_pw_set(USERNAME, PASSWORD)

# Configurar TLS
client.tls_set(ca_certs="hivemq-ca.pem", tls_version=ssl.PROTOCOL_TLSv1_2)


client.on_connect = on_connect
client.on_publish = on_publish
client.on_log = on_log

# -------------------------
# Conectar al broker
# -------------------------
client.connect(BROKER, PORT, 60)

# -------------------------
# Publicar el mensaje
# -------------------------
client.publish(TOPIC, json.dumps(payload))
print("Mensaje enviado a WLED:", payload)

# -------------------------
# Cerrar conexión
# -------------------------
client.disconnect()

