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

*{
box-sizing:border-box;
margin:0;
padding:0;
font-family:Arial,sans-serif;
}

body{
background:#f3f4f6;
padding:12px;
height:100vh;
overflow:hidden;
}

/* MAIN PAGE LAYOUT */
.page{
display:grid;

grid-template-columns:470px 1fr;

justify-content:center;

gap:14px;

height:calc(100vh - 24px);

max-width:1750px;

margin:auto;

overflow:hidden;
}

/* LEFT CONTROLS */
.left-panel{
display:flex;
flex-direction:column;
gap:10px;
overflow:hidden;
padding-right:2px;
}

/* RIGHT CHARTS */
.right-panel{
display:flex;
flex-direction:column;

gap:10px;

width:900px;

min-width:900px;

overflow:hidden;
}

/* GENERAL CARD */
.card{
background:white;
border-radius:12px;
padding:12px;
box-shadow:0 2px 8px rgba(0,0,0,0.08);
flex-shrink:0;
}

.double-card-row{
display:grid;
grid-template-columns:1fr 1fr;
gap:10px;
}

.half-card{
height:100%;
}

/* TITLE */
.title{
font-size:24px;
font-weight:bold;
line-height:1.05;
}

/* SECTION LABEL */
.section-title{
font-size:18px;
font-weight:bold;
margin-bottom:10px;
}

/* FAN/VENT GRID */
.control-grid{
display:grid;
grid-template-columns:1fr 1fr;
gap:10px;
width:100%;
}

/* INDIVIDUAL CONTROL */
.control-card{
background:#fafafa;
border-radius:10px;
padding:10px;
border:1px solid #e5e7eb;
min-width:0;
}

.control-card h3{

font-size:15px;

margin-bottom:8px;

white-space:nowrap;
overflow:hidden;
text-overflow:ellipsis;
}

/* SLIDER ROW */
.slider-row{
display:flex;
align-items:center;
gap:8px;
margin-bottom:10px;
}

.slider-row input[type=range]{
flex:1;
min-width:0;
}

/* VALUES */
.value{
min-width:52px;
font-weight:bold;
font-size:14px;
text-align:right;
}

/* BUTTONS */
button{
border:none;
padding:7px 10px;
border-radius:8px;
cursor:pointer;
font-weight:bold;
font-size:14px;
transition:0.15s;
}

button:hover{
opacity:0.92;
}

.apply-btn{
background:#7c3aed;
color:white;
width:100%;
}

.green{
background:#16a34a;
color:white;
}

.red{
background:#dc2626;
color:white;
}

.gray{
background:#d1d5db;
}

/* CHART CARDS */
.chart-card{

background:white;

border-radius:12px;

padding:14px;

box-shadow:0 2px 8px rgba(0,0,0,0.08);

height:280px;

max-height:280px;

display:flex;
flex-direction:column;

overflow:hidden;
}

/* CHART TITLES */
.chart-card h3{
margin-bottom:6px;
font-size:16px;
flex-shrink:0;
}

/* CHART AREA */
.chart-container{

position:relative;

height:220px;

width:100%;

flex:1;

min-height:0;
}

/* IMPORTANT */
canvas{
width:100% !important;
height:100% !important;
}

/* STATUS GRID */
.status-grid{
display:grid;
grid-template-columns:repeat(6,1fr);
gap:6px;
}

.status-item{
background:#fafafa;
padding:6px;
border-radius:10px;
text-align:center;
border:1px solid #e5e7eb;
}

.status-item h4{
font-size:12px;
margin-bottom:4px;
color:#555;
}

.status-item p{
font-size:14px;
font-weight:bold;
}

/* TEST BUTTONS */
.test-buttons{
display:flex;
gap:8px;
margin-top:10px;
}

/* AIRFLOW INPUT */
.airflow-row{
display:flex;
align-items:center;
gap:8px;
}

.airflow-row input{
flex:1;
padding:8px;
border-radius:8px;
border:1px solid #ccc;
font-size:14px;
min-width:0;
}

/* SMALL TEXT */
.small-text{
font-size:13px;
margin-top:10px;
color:#555;
}

/* SCROLLBAR */
.left-panel::-webkit-scrollbar{
width:6px;
}

.left-panel::-webkit-scrollbar-thumb{
background:#d1d5db;
border-radius:10px;
}

/* LAPTOP SCALING */
@media (max-width:1400px){

.page{
grid-template-columns:430px 1fr;
}

.chart-card{
height:300px;
max-height:300px;
}

.chart-container{
height:245px;
}

.title{
font-size:22px;
}

}

/* SMALLER LAPTOPS */
@media (max-width:1200px){

.page{
grid-template-columns:380px 1fr;
}

.control-grid{
grid-template-columns:1fr;
}

.status-grid{
grid-template-columns:1fr 1fr;
}

.chart-card{
height:270px;
max-height:270px;
}

.chart-container{
height:210px;
}

}

</style>
</head>

<body>

<div class="page">

<!-- LEFT SIDE -->
<div class="left-panel">

<div class="card">
<div class="title">Airflow & CO₂ Control</div>
</div>

<div class="card">

<div class="section-title">Fan & Vent Controls</div>

<div class="control-grid">

<div class="control-card">
<h3>Inlet Fan</h3>

<div class="slider-row">
<input type="range" min="0" max="100" id="inletFan">
<span class="value" id="inletFanValue">0%</span>
</div>

<button class="apply-btn" onclick="setFan('inlet')">
Apply
</button>
</div>

<div class="control-card">
<h3>Outlet Fan</h3>

<div class="slider-row">
<input type="range" min="0" max="100" id="outletFan">
<span class="value" id="outletFanValue">0%</span>
</div>

<button class="apply-btn" onclick="setFan('outlet')">
Apply
</button>
</div>

<div class="control-card">
<h3>Inlet Vent</h3>

<div class="slider-row">
<input type="range" min="0" max="70" id="inletVent">
<span class="value" id="inletVentValue">0°</span>
</div>

<button class="apply-btn" onclick="setVent('inlet')">
Apply
</button>
</div>

<div class="control-card">
<h3>Outlet Vent</h3>

<div class="slider-row">
<input type="range" min="0" max="70" id="outletVent">
<span class="value" id="outletVentValue">0°</span>
</div>

<button class="apply-btn" onclick="setVent('outlet')">
Apply
</button>
</div>

</div>
</div>

<div class="double-card-row">

<div class="card half-card">

<div class="section-title">CO₂ Valve</div>

<div class="test-buttons">
<button class="green" onclick="setCO2(1)">ON</button>
<button class="gray" onclick="setCO2(0)">OFF</button>
</div>

<p class="small-text" id="co2Status">
Status: OFF
</p>

</div>

<div class="card half-card">

<div class="section-title">Test Control</div>

<div class="airflow-row">
<input type="number" id="airflowValue" step="0.1" placeholder="Airflow">
<span>CFM</span>
</div>

<div class="test-buttons">
<button class="green" onclick="startTest()">Start</button>
<button class="red" onclick="stopTest()">Stop</button>
</div>

<p class="small-text" id="testStatus">
Test: STOPPED
</p>

</div>

</div>

<div class="card">

<div class="section-title">System Status</div>

<div class="status-grid">

<div class="status-item">
<h4>Inlet Fan</h4>
<p id="statusInletFan">0%</p>
</div>

<div class="status-item">
<h4>Outlet Fan</h4>
<p id="statusOutletFan">0%</p>
</div>

<div class="status-item">
<h4>CO₂</h4>
<p id="statusCO2">OFF</p>
</div>

<div class="status-item">
<h4>Inlet Vent</h4>
<p id="statusInletVent">0°</p>
</div>

<div class="status-item">
<h4>Outlet Vent</h4>
<p id="statusOutletVent">0°</p>
</div>

<div class="status-item">
<h4>Airflow</h4>
<p id="statusAirflow">--</p>
</div>

</div>

</div>

</div>

<!-- RIGHT SIDE -->
<div class="right-panel">

<div class="chart-card">
<h3>CO₂ vs Time</h3>

<div class="chart-container">
<canvas id="co2Chart"></canvas>
</div>
</div>

<div class="chart-card">
<h3>Temperature vs Time</h3>

<div class="chart-container">
<canvas id="tempChart"></canvas>
</div>
</div>

</div>
</div>

<script>

const SENSORS = ["Inlet Vent","Outlet Vent","Window Wall","Floor"];
const SENSOR_KEYS = ["sensor1","sensor2","sensor3","sensor4"];
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

document.getElementById(
fan === "inlet" ? "statusInletFan" : "statusOutletFan"
).textContent = speed + "%"

}


function setVent(vent){

const angle=document.getElementById(vent+"Vent").value

fetch("/vent",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({vent:vent,angle:Number(angle)})
})

document.getElementById(
vent === "inlet" ? "statusInletVent" : "statusOutletVent"
).textContent = angle + "°"

}

function setCO2(state){

fetch("/co2",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({state:state})
})

document.getElementById("statusCO2").textContent =
state ? "ON" : "OFF"

document.getElementById("co2Status").textContent =
"Status: " + (state ? "ON" : "OFF")

}

initSlider("inletFan","%")
initSlider("outletFan","%")
initSlider("inletVent","deg")
initSlider("outletVent","deg")

function createDatasets() {
    return SENSORS.map((label, i) => ({
        label: label,
        data: [],
        borderColor: COLORS[i],
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.25,
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
responsive:true,
maintainAspectRatio:false,
animation:false,

plugins:{
legend:{
position:"top"
}
},

scales:{
x:{
ticks:{
maxTicksLimit:10
}
}
}

}

})


const tempChart=new Chart(document.getElementById("tempChart"),{

type:"line",

data:{
labels:[],
datasets:createDatasets()
},

options:{
responsive:true,
maintainAspectRatio:false,
animation:false,

plugins:{
legend:{
position:"top"
}
},

scales:{
x:{
ticks:{
maxTicksLimit:10
}
}
}

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

        SENSOR_KEYS.forEach((s, j) => {
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

    document.getElementById("statusAirflow").textContent = airflow + " CFM"

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
