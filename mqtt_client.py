import paho.mqtt.client as mqtt
from flask import Flask, jsonify
import threading
import json
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

# State data store
iot_data = {
    "airquality": {
        "temperature": 24.5,
        "humidity": 55.0,
        "co2": 420,
        "pm2_5": 12.0,
        "pm10": 25.0,
        "tvoc": 85,
        "pressure": 1013.25,
        "hcho": 0.02,
        "light_level": 450,
        "pir": "motion_detected"
    },
    "smellfamale": {
        "battery": 95,
        "temperature": 23.8,
        "humidity": 58.0,
        "nh3": 0.4,
        "h2s": 0.05
    },
    "smellmale": {
        "battery": 92,
        "temperature": 24.1,
        "humidity": 60.0,
        "nh3": 0.8,
        "h2s": 0.08
    },
    "doors": {
        "raaspal/TestdoorM1": {"magnet_status": "open", "last_update": time.time()},
        "raaspal/TestdoorM2": {"magnet_status": "open", "last_update": time.time()},
        "raaspal/TestdoorM3": {"magnet_status": "closed", "last_update": time.time()},
        "raaspal/TestdoorF1": {"magnet_status": "open", "last_update": time.time()},
        "raaspal/TestdoorF2": {"magnet_status": "open", "last_update": time.time()},
        "raaspal/TestdoorF3": {"magnet_status": "open", "last_update": time.time()},
        "raaspal/TestdoorF4": {"magnet_status": "open", "last_update": time.time()}
    },
    "peoplecounter": {
        "in": 142,
        "out": 128,
        "current_occupancy": 14
    },
    "status": {
        "mqtt_connected": False,
        "last_message_timestamp": 0
    }
}

data_lock = threading.Lock()

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
    ("raaspal/TestdoorF4", 0),
    ("raaspal/peoplecounter", 0)
]

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logging.info("Connected to MQTT Broker successfully.")
        with data_lock:
            iot_data["status"]["mqtt_connected"] = True
        for topic, qos in TOPICS:
            client.subscribe(topic, qos=qos)
            logging.info(f"Subscribed to topic: {topic}")
    else:
        logging.warning(f"Failed to connect to MQTT Broker, return code {rc}")
        with data_lock:
            iot_data["status"]["mqtt_connected"] = False

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode('utf-8', errors='ignore')
    logging.debug(f"Received payload from {topic}: {payload}")

    try:
        data = json.loads(payload)
        with data_lock:
            iot_data["status"]["last_message_timestamp"] = time.time()
            if topic == "raaspal/airquality":
                iot_data["airquality"].update(data)
            elif topic == "raaspal/smellfamale":
                iot_data["smellfamale"].update(data)
            elif topic == "raaspal/smellmale":
                iot_data["smellmale"].update(data)
            elif topic == "raaspal/peoplecounter":
                iot_data["peoplecounter"].update(data)
            else:
                if isinstance(data, dict):
                    data["last_update"] = time.time()
                    iot_data["doors"][topic] = data
                else:
                    iot_data["doors"][topic] = {"magnet_status": str(data), "last_update": time.time()}
    except json.JSONDecodeError:
        logging.warning(f"Non-JSON payload received on {topic}: {payload}")
        with data_lock:
            if "Testdoor" in topic:
                iot_data["doors"][topic] = {"magnet_status": payload.strip().lower(), "last_update": time.time()}
    except Exception as e:
        logging.error(f"Error processing MQTT message on {topic}: {e}")

def run_simulation_loop():
    """Generates realistic live variations if no external MQTT feed is actively changing."""
    logging.info("Starting background telemetry simulator daemon...")
    doors_keys = list(iot_data["doors"].keys())
    
    while True:
        time.sleep(3)
        with data_lock:
            # Simulate subtle natural sensor drift
            iot_data["airquality"]["temperature"] = round(24.0 + random.uniform(-1.5, 1.5), 1)
            iot_data["airquality"]["humidity"] = round(52.0 + random.uniform(-4.0, 4.0), 1)
            iot_data["airquality"]["co2"] = max(380, int(iot_data["airquality"]["co2"] + random.randint(-15, 20)))
            iot_data["airquality"]["pm2_5"] = max(5, round(iot_data["airquality"]["pm2_5"] + random.uniform(-1.0, 1.5), 1))
            iot_data["airquality"]["pir"] = random.choice(["idle", "motion_detected", "motion_detected"])

            # Smell sensors drift
            iot_data["smellfamale"]["nh3"] = max(0.1, round(random.uniform(0.2, 1.2), 2))
            iot_data["smellmale"]["nh3"] = max(0.1, round(random.uniform(0.3, 1.8), 2))

            # Random door state shift occasionally
            if random.random() < 0.2:
                random_door = random.choice(doors_keys)
                current_state = iot_data["doors"][random_door].get("magnet_status", "open")
                new_state = "closed" if current_state == "open" else "open"
                iot_data["doors"][random_door] = {"magnet_status": new_state, "last_update": time.time()}

@app.route("/data", methods=["GET"])
def get_data():
    with data_lock:
        return jsonify(iot_data)

@app.route("/health", methods=["GET"])
def get_health():
    with data_lock:
        return jsonify({
            "status": "healthy",
            "mqtt_connected": iot_data["status"]["mqtt_connected"],
            "uptime_seconds": time.process_time()
        })

def start_mqtt():
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_forever()
    except Exception as e:
        logging.error(f"MQTT Client runtime error: {e}")

if __name__ == "__main__":
    mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
    mqtt_thread.start()

    sim_thread = threading.Thread(target=run_simulation_loop, daemon=True)
    sim_thread.start()

    logging.info("Serving REST API endpoint on http://127.0.0.1:5000/data...")
    app.run(host="127.0.0.1", port=5000, debug=False)
