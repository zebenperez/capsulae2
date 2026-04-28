import json
import paho.mqtt.publish as publish

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "wled/livingroom/api"

payload = {
    "on": True,
    "bri": 255,
    "seg": [{"col": [[255, 0, 0]]}]  # verde
}

publish.single(TOPIC, json.dumps(payload), hostname=BROKER, port=PORT)
print("Comando enviado a WLED.")

