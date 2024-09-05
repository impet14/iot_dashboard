import paho.mqtt.client as mqtt
from flask import Flask, jsonify
import threading
import json  # Import json for safe JSON handling

app = Flask(__name__)

# Initialize data storage
iot_data = {
    "airquality": {},
    "smellfamale": {},
    "smellmale": {},
    "doors": {}
}

# MQTT settings
BROKER = 'broker.emqx.io'
PORT = 1883
TOPICS = [
    ("raaspal/airquality", 0),
    ("raaspal/smellfamale", 0),
    ("raaspal/smellmale", 0),
    ("raaspal/TestdoorM1", 0),
    ("raaspal/TestdoorM2", 0),
    ("raaspal/TestdoorM3", 0),
    ("raaspal/TestdoorF1", 0),
    ("raaspal/TestdoorF2", 0),
    ("raaspal/TestdoorF3", 0),
    ("raaspal/TestdoorF4", 0)
]

# MQTT Callback when connecting to the broker
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    for topic in TOPICS:
        client.subscribe(topic)

# MQTT Callback when receiving a message
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"Received `{payload}` from `{topic}` topic")

    try:
        # Parse the payload as JSON safely
        data = json.loads(payload)
        
        # Update the appropriate part of the data store
        if topic == "raaspal/airquality":
            iot_data["airquality"] = data
        elif topic == "raaspal/smellfamale":
            iot_data["smellfamale"] = data
        elif topic == "raaspal/smellmale":
            iot_data["smellmale"] = data
        else:
            iot_data["doors"][topic] = data

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from topic `{topic}`: {e}")
    except Exception as e:
        print(f"Unexpected error processing message from `{topic}`: {e}")

# Flask endpoint to get IoT data
@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(iot_data)

# Start MQTT Client
def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    # Run MQTT client in a separate thread
    mqtt_thread = threading.Thread(target=start_mqtt)
    mqtt_thread.start()

    # Run Flask app
    app.run(debug=True, use_reloader=False)
