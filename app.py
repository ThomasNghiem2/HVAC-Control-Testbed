from flask import Flask, request, jsonify, Response
import json
import threading
import serial
import time
from datetime import datetime
import logging
import csv
import os

#log = logging.getLogger('werkzeug')
#log.setLevel(logging.ERROR)

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 5000

app = Flask(__name__)


# ------------------------------
# SENSOR DATA + SYSTEM STATE STORAGE
# ------------------------------

MAX_POINTS = 300
TIMESTAMP_INTERVAL = 2
SENSOR_IDS = ["sensor1","sensor2","sensor3","sensor4"]

timestamp = []
sensor_data = {sid: {"co2": [], "temp": []} for sid in SENSOR_IDS}
latest_sensor_values = {sid: {"co2": None, "temp": None} for sid in SENSOR_IDS}

test_running = False
current_airflow = None

system_state = {
    "inlet_fan": 0,
    "outlet_fan": 0,
    "inlet_vent": 0,
    "outlet_vent": 0,
    "co2": 0
}

# ------------------------------
# CSV SETUP
# ------------------------------
'''CSV_FILE = f"data/sensor_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"

with open(CSV_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    headers = ["timestamp","co2_state","inlet_fan","outlet_fan","inlet_vent","outlet_vent"]
    for sid in SENSOR_IDS:
        headers += [f"{sid}_co2", f"{sid}_temp"]
    writer.writerow(headers)
'''
CSV_FILE = None

# ------------------------------
# WEB UI 
# ------------------------------

@app.route("/")
def index():

    html = """
<!DOCTYPE html>
<html>

<head>
<title>Building Testbed Control</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

body{
font-family:Arial;
display:flex;
justify-content:center;
align-items:flex-start;
background:#f5f5f5;
padding-top:20px;
}

.page{
width:100%;
max-width:1100px;
}

.grid{
display:grid;
grid-template-columns:repeat(2,1fr);
grid-gap:40px;
}

.card{
background:#fff;
border-radius:12px;
padding:25px;
box-shadow:0 4px 8px rgba(0,0,0,0.1);
text-align:center;
}

.slider-container{
display:flex;
gap:12px;
align-items:center;
margin:15px 0;
}

.value{
min-width:40px;
font-weight:bold;
}

.chart-card{
margin-top:40px;
background:#fff;
padding:20px;
border-radius:12px;
box-shadow:0 4px 8px rgba(0,0,0,0.1);
}

canvas{
max-height:300px;
}

</style>
</head>


<body>

<div class="page">

<h1>Airflow & CO₂ Control Panel</h1>

<div class="grid">

<div class="card">
<h3>Inlet Fan</h3>

<div class="slider-container">
<input type="range" min="0" max="100" id="inletFan" value="0">
<span class="value" id="inletFanValue">0%</span>
</div>

<button onclick="setFan('inlet')">Apply</button>
</div>


<div class="card">
<h3>Outlet Fan</h3>

<div class="slider-container">
<input type="range" min="0" max="100" id="outletFan" value="0">
<span class="value" id="outletFanValue">0%</span>
</div>

<button onclick="setFan('outlet')">Apply</button>
</div>


<div class="card">
<h3>Inlet Vent</h3>

<div class="slider-container">
<input type="range" min="0" max="70" id="inletVent" value="0">
<span class="value" id="inletVentValue">0deg</span>
</div>

<button onclick="setVent('inlet')">Apply</button>
</div>


<div class="card">
<h3>Outlet Vent</h3>

<div class="slider-container">
<input type="range" min="0" max="70" id="outletVent" value="0">
<span class="value" id="outletVentValue">0deg</span>
</div>

<button onclick="setVent('outlet')">Apply</button>
</div>

</div>

<div class="card">
<h3>CO₂ Valve</h3>

<button onclick="setCO2(1)">ON</button>
<button onclick="setCO2(0)">OFF</button>

<p id="co2Status">Status: OFF</p>
</div>

<div class="card">

<h3>Test Control</h3>

<div class="slider-container">
<input type="number" id="airflowValue" step="0.1" placeholder="Enter airflow rate">
<span class="value">CFM</span>
</div>

<button onclick="startTest()">Start Test</button>
<button onclick="stopTest()">Stop Test</button>

<p id="testStatus">Test: STOPPED</p>

</div>

<div class="chart-card">

<h3>CO₂ vs Time</h3>
<canvas id="co2Chart"></canvas>

</div>


<div class="chart-card">

<h3>Temperature vs Time</h3>
<canvas id="tempChart"></canvas>

</div>

</div>



<script>

const SENSORS = ["sensor1","sensor2","sensor3","sensor4"];
const COLORS = ["red","green","blue","purple"];

function initSlider(id,unit){

const s=document.getElementById(id)
const label=document.getElementById(id+"Value")

s.value=0
label.textContent="0"+unit

s.oninput=()=>{
label.textContent=s.value+unit
}

}


function setFan(fan){

const speed=document.getElementById(fan+"Fan").value

fetch("/fan",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({fan:fan,speed:Number(speed)})
})

}


function setVent(vent){

const angle=document.getElementById(vent+"Vent").value

fetch("/vent",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({vent:vent,angle:Number(angle)})
})

}

function setCO2(state){

fetch("/co2",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({state:state})
})

document.getElementById("co2Status").textContent =
"Status: " + (state ? "ON" : "OFF")

}


initSlider("inletFan","%")
initSlider("outletFan","%")
initSlider("inletVent","deg")
initSlider("outletVent","deg")


function createDatasets() {
    return SENSORS.map((s, i) => ({
        label: s,
        data: [],
        borderColor: COLORS[i % COLORS.length],
        fill: false
    }));
}

const co2Chart=new Chart(document.getElementById("co2Chart"),{

type:"line",

data:{
labels:[],
datasets: createDatasets()
},

options:{
animation:false
}

})


const tempChart=new Chart(document.getElementById("tempChart"),{

type:"line",

data:{
labels:[],
datasets: createDatasets()
},

options:{
animation:false
}

})

function updateGraphs() {
    fetch("/data")
    .then(r => r.json())
    .then(data => {

        let t = data.time;

        // Only keep last 200 points
        const MAX_POINTS = 200;
        const start = Math.max(0, t.length - MAX_POINTS);

        const slicedTime = t.slice(start);

        co2Chart.data.labels = slicedTime;
        tempChart.data.labels = slicedTime;

        SENSORS.forEach((s, j) => {
            co2Chart.data.datasets[j].data = data[s].co2.slice(start);
            tempChart.data.datasets[j].data = data[s].temp.slice(start);
        });

        co2Chart.update("none");
        tempChart.update("none");
    });
}

setInterval(updateGraphs,1000)

function startTest(){

    const airflow = Number(document.getElementById("airflowValue").value)

    if(!airflow){
        alert("Enter airflow value first")
        return
    }

    co2Chart.data.labels = []
    tempChart.data.labels = []

    co2Chart.data.datasets.forEach(d => d.data = [])
    tempChart.data.datasets.forEach(d => d.data = [])

    co2Chart.update()
    tempChart.update()

    fetch("/start_test",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({airflow:airflow})
    })

    document.getElementById("testStatus").textContent =
    "Test: RUNNING"
}

function stopTest(){

    fetch("/stop_test",{
        method:"POST"
    })

    document.getElementById("testStatus").textContent =
    "Test: STOPPED"

    document.getElementById("airflowValue").value=""
}

</script>

</body>
</html>
"""

    return Response(html, mimetype="text/html")


# ------------------------------
# BLUETOOTH PORTS
# ------------------------------
FAN_PORT = "COM5"
VENT_PORT = "COM7"
CO2_PORT = "COM8"

bt_fan = None
bt_vent = None
bt_co2 = None

# ------------------------------
# FAN CONTROL
# ------------------------------
@app.route("/fan", methods=["POST"])
def set_fan():
    global bt_fan
    data = request.get_json(force=True, silent=True) or {}
    fan = data.get("fan")
    speed = int(data.get("speed"))
    speed = max(0, min(speed, 100))

    cmd = {"fan": fan, "speed": speed}
    msg = json.dumps(cmd) + "\n"
    
    if fan == "inlet":
        system_state["inlet_fan"] = speed
    elif fan == "outlet":
        system_state["outlet_fan"] = speed

    if bt_fan:
        bt_fan.write(msg.encode())
    return jsonify(status="ok")


# ------------------------------
# VENT CONTROL
# ------------------------------
@app.route("/vent", methods=["POST"])
def set_vent():
    global bt_vent
    data = request.get_json(force=True, silent=True) or {}
    vent = data.get("vent")
    angle = int(data.get("angle"))
    angle = max(0, min(angle, 70))
   
    cmd = {"vent": vent, "angle": angle}
    msg = json.dumps(cmd) + "\n"

    if vent == "inlet":
        system_state["inlet_vent"] = angle
    elif vent == "outlet":
        system_state["outlet_vent"] = angle

    if bt_vent:
        bt_vent.write(msg.encode())
    return jsonify(status="ok")

# ------------------------------
# CO2 CONTROL
# ------------------------------
@app.route("/co2", methods=["POST"])
def set_co2():
    global bt_co2
    data = request.get_json(force=True, silent=True) or {}
    state = int(data.get("state", 0))
    state = 1 if state else 0

    cmd = {"co2": state}
    msg = json.dumps(cmd) + "\n"

    system_state["co2"] = state

    if bt_co2:
        bt_co2.write(msg.encode())
    return jsonify(status="ok")


# ------------------------------
# BACKGROUND TIMESTAMP THREAD AND CSV WRITER
# ------------------------------
def timestamp_updater():
    while True:
        if not test_running:
            time.sleep(TIMESTAMP_INTERVAL)
            continue

        now = datetime.now().strftime("%H:%M:%S")
        timestamp.append(now)

        row = [now,system_state["co2"],system_state["inlet_fan"],system_state["outlet_fan"],
               system_state["inlet_vent"],system_state["outlet_vent"]]

        for sid in SENSOR_IDS:
            # append latest known value or None
            co2_val = latest_sensor_values[sid]["co2"]
            temp_val = latest_sensor_values[sid]["temp"]
            sensor_data[sid]["co2"].append(co2_val)
            sensor_data[sid]["temp"].append(temp_val)

            row += [co2_val, temp_val]

            # trim to MAX_POINTS
            if len(sensor_data[sid]["co2"]) > MAX_POINTS:
                sensor_data[sid]["co2"].pop(0)
                sensor_data[sid]["temp"].pop(0)

        if len(timestamp) > MAX_POINTS:
            timestamp.pop(0)

        # Append to CSV
        if CSV_FILE:
            with open(CSV_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(row)

        time.sleep(TIMESTAMP_INTERVAL)

threading.Thread(target=timestamp_updater, daemon=True).start()


# ------------------------------
# SENSOR DATA RECEIVER 
# ------------------------------
@app.route("/sensor", methods=["POST"])
def receive_sensor():
    data = request.get_json(force=True, silent=True) or {}

    try:
        sid = data.get("sensor_id", "sensor1")
        if sid not in sensor_data:
            return jsonify(status="error", msg="Unknown sensor"), 400

        latest_sensor_values[sid]["co2"] = float(data.get("co2"))
        latest_sensor_values[sid]["temp"] = float(data.get("temp"))

        return jsonify(status="ok")

    except Exception as e:
        print("Sensor parse error:", e)
        return jsonify(status="error"), 400


# ------------------------------
# SENSOR DATA API 
# ------------------------------
@app.route("/data")
def data():
    return jsonify({
        "time": timestamp,
        **sensor_data
    })

# ------------------------------
# START/STOP 
# ------------------------------
@app.route("/start_test", methods=["POST"])
def start_test():

    global test_running
    global current_airflow
    global CSV_FILE

    data = request.get_json(force=True, silent=True) or {}

    airflow = float(data.get("airflow"))

    timestamp.clear()
    for sid in SENSOR_IDS:
        sensor_data[sid]["co2"].clear()
        sensor_data[sid]["temp"].clear()

    current_airflow = airflow
    test_running = True

    # Create NEW csv for each run
    CSV_FILE = f"data/test_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["Airflow Rate", airflow])
        writer.writerow(["Start Time", datetime.now()])
        writer.writerow([])

        headers = ["timestamp","co2_state","inlet_fan","outlet_fan","inlet_vent","outlet_vent"]

        for sid in SENSOR_IDS:
            headers += [f"{sid}_co2", f"{sid}_temp"]

        writer.writerow(headers)

    return jsonify(status="ok")

@app.route("/stop_test", methods=["POST"])
def stop_test():
    global test_running
    test_running = False
    return jsonify(status="ok")

# ------------------------------
# MAIN
# ------------------------------

if __name__ == "__main__":
    try:
        #bt_fan = serial.Serial(FAN_PORT, 115200)
        print("Fan controller connected:")
    except:
        print("Fan controller NOT connected")
    try:
        #bt_vent = serial.Serial(VENT_PORT, 115200)
        print("Vent controller connected:")
    except:
        print("Vent controller NOT connected")
    try:
        #bt_co2 = serial.Serial(CO2_PORT, 115200)
        print("CO2 controller connected:")
    except:
        print("CO2 controller NOT connected")

    print("Starting WiFi server...")
    print("Make sure ESP32 sends to: http://192.168.137.1:5000/sensor")
    app.run(host=HTTP_HOST, port=HTTP_PORT)
