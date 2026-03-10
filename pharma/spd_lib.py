import json
import paho.mqtt.publish as publish

BROKER = "broker.hivemq.com"
PORT = 1883
#TOPIC = "wled/livingroom/api"
TOPIC = "wled/"

#payload = {
#    "on": True,
#    "bri": 255,
#    "seg": [{"col": [[255, 0, 0]]}]  # verde
#}

def send_spd_values(payload, spd_name):
    print(f"{TOPIC}{spd_name}/api")
    publish.single(f"{TOPIC}{spd_name}/api", json.dumps(payload), hostname=BROKER, port=PORT)
    print("Comando enviado a WLED.")

