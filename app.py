import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State
import requests
import plotly.graph_objs as go
from datetime import datetime
import collections
import random
import time

FLASK_URL = 'http://127.0.0.1:5000/data'

# Keep historical buffer for live trend charts (up to 30 timestamps)
MAX_HISTORY = 30
history_timestamps = collections.deque(maxlen=MAX_HISTORY)
history_temp = collections.deque(maxlen=MAX_HISTORY)
history_co2 = collections.deque(maxlen=MAX_HISTORY)
history_pm25 = collections.deque(maxlen=MAX_HISTORY)
history_nh3_male = collections.deque(maxlen=MAX_HISTORY)
history_nh3_female = collections.deque(maxlen=MAX_HISTORY)

# Initial Fallback Data
initial_air_quality = {
    "temperature": 24.2,
    "humidity": 54.0,
    "co2": 415,
    "pm2_5": 11.5,
    "pm10": 22.0,
    "tvoc": 80,
    "pressure": 1013.2,
    "hcho": 0.015,
    "light_level": 480,
    "pir": "idle"
}

initial_smell_sensor_female = {
    "battery": 98,
    "temperature": 23.5,
    "humidity": 56.0,
    "nh3": 0.35,
    "h2s": 0.04
}

initial_smell_sensor_male = {
    "battery": 94,
    "temperature": 24.0,
    "humidity": 58.0,
    "nh3": 0.65,
    "h2s": 0.07
}

initial_door_status = {
    "raaspal/TestdoorM1": {"magnet_status": "open"},
    "raaspal/TestdoorM2": {"magnet_status": "open"},
    "raaspal/TestdoorM3": {"magnet_status": "closed"},
    "raaspal/TestdoorF1": {"magnet_status": "open"},
    "raaspal/TestdoorF2": {"magnet_status": "open"},
    "raaspal/TestdoorF3": {"magnet_status": "open"},
    "raaspal/TestdoorF4": {"magnet_status": "open"} 
}

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)
app.title = "RaasPal Smart Restroom Telemetry"
server = app.server

def create_stall_card(label, icon, is_open):
    status_text = "AVAILABLE" if is_open else "OCCUPIED"
    status_class = "available" if is_open else "occupied"
    
    return html.Div(
        className=f"stall-card {status_class}",
        children=[
            html.Div(icon, className="stall-icon"),
            html.Div(label, className="stall-label"),
            html.Div(status_text, className=f"stall-status-badge {status_class}"),
            html.Div(className="stall-occupied-slash") if not is_open else None
        ]
    )

app.layout = dbc.Container(
    [
        dcc.Interval(id='interval-component', interval=2500, n_intervals=0),

        html.Div(
            className="background",
            children=[
                # Top Header Bar
                html.Div(
                    className="dashboard-header",
                    children=[
                        html.Div(
                            className="brand-container",
                            children=[
                                html.Img(src='/assets/L-02.png', className="brand-logo", alt="RaasPal Logo"),
                                html.H1("SMART RESTROOM & SHOWROOM TELEMETRY", className="brand-title")
                            ]
                        ),
                        html.Div(
                            children=[
                                html.Div(
                                    children=[
                                        html.Div(className="live-dot"),
                                        html.Span("MQTT FEED LIVE", id="mqtt-status-text")
                                    ],
                                    className="header-status-badge"
                                ),
                                html.Span(id="live-clock", style={"margin-left": "1rem", "color": "#94a3b8", "font-weight": "500", "font-size": "0.9rem"})
                            ],
                            style={"display": "flex", "align-items": "center"}
                        )
                    ]
                ),

                # Section 1: Air Quality Telemetry
                dbc.Row(
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.Span("🌿 Quality Assessment — Showroom Environment"),
                                        html.Span("10 Sensors Active", className="card-header-badge")
                                    ]
                                ),
                                dbc.CardBody(html.Div(id='airquality-metrics-grid')),
                            ],
                            className="graph-card",
                        ),
                        width=12,
                    ),
                    className="mb-3",
                    style={"width": "100%", "max-width": "1400px"}
                ),

                # Section 2: Smell & Comfort Sensors (Female vs Male)
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.Span("🚺 Quality Assessment — Female Restroom"),
                                            html.Span(id="female-smell-badge", className="card-header-badge status-good", children="FRESH AIR")
                                        ]
                                    ),
                                    dbc.CardBody(html.Div(id='smell-metrics-female-grid')),
                                ],
                                className="graph-card",
                            ),
                            width=12, lg=6,
                        ),
                        dbc.Col(
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.Span("🚹 Quality Assessment — Male Restroom"),
                                            html.Span(id="male-smell-badge", className="card-header-badge status-good", children="FRESH AIR")
                                        ]
                                    ),
                                    dbc.CardBody(html.Div(id='smell-metrics-male-grid')),
                                ],
                                className="graph-card",
                            ),
                            width=12, lg=6,
                        ),
                    ],
                    className="mb-3",
                    style={"width": "100%", "max-width": "1400px"}
                ),

                # Section 3: Restroom Stall Occupancy Floor Map
                dbc.Row(
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.Span("🚻 Real-time Stall Occupancy Status"),
                                        html.Span(id="occupancy-summary-badge", className="card-header-badge", children="0 / 7 Occupied")
                                    ]
                                ),
                                dbc.CardBody(html.Div(id='door-status-grid', className="door-grid-container")),
                            ],
                            className="graph-card",
                        ),
                        width=12,
                    ),
                    className="mb-3",
                    style={"width": "100%", "max-width": "1400px"}
                ),

                # Section 4: Real-time Telemetry Trend Graph
                dbc.Row(
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.Span("📈 Live Telemetry Trends (Real-time Timeline)"),
                                        html.Span("30s Window", className="card-header-badge")
                                    ]
                                ),
                                dbc.CardBody(
                                    dcc.Graph(
                                        id='live-trend-graph',
                                        config={'displayModeBar': False},
                                        style={"height": "320px"}
                                    )
                                ),
                            ],
                            className="graph-card",
                        ),
                        width=12,
                    ),
                    className="mb-3",
                    style={"width": "100%", "max-width": "1400px"}
                ),

                # Footer
                html.Div("POWERED BY RAASPAL IOT PLATFORM", className="powered-by"),
            ],
        )
    ],
    fluid=True,
    style={"padding": "0"}
)

@app.callback(
    [
        Output('airquality-metrics-grid', 'children'),
        Output('smell-metrics-female-grid', 'children'),
        Output('smell-metrics-male-grid', 'children'),
        Output('door-status-grid', 'children'),
        Output('live-trend-graph', 'figure'),
        Output('live-clock', 'children'),
        Output('occupancy-summary-badge', 'children'),
        Output('female-smell-badge', 'children'),
        Output('female-smell-badge', 'className'),
        Output('male-smell-badge', 'children'),
        Output('male-smell-badge', 'className'),
    ],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard_data(n):
    # Attempt REST call to local MQTT Flask server; fallback if offline
    try:
        res = requests.get(FLASK_URL, timeout=1.5)
        if res.status_code == 200:
            data = res.json()
        else:
            raise Exception("Invalid status code")
    except Exception:
        # Fallback simulation values
        sim_temp = round(24.0 + random.uniform(-1.0, 1.0), 1)
        sim_co2 = random.randint(400, 480)
        sim_pm25 = round(10.0 + random.uniform(0, 5.0), 1)
        data = {
            "airquality": {**initial_air_quality, "temperature": sim_temp, "co2": sim_co2, "pm2_5": sim_pm25},
            "smellfamale": initial_smell_sensor_female,
            "smellmale": initial_smell_sensor_male,
            "doors": initial_door_status
        }

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Air Quality Cards
    aq = data.get('airquality', initial_air_quality)
    aq_metrics = [
        ("🌡️", "TEMP", f"{aq.get('temperature', 0)}°C", "status-good"),
        ("💧", "HUMIDITY", f"{aq.get('humidity', 0)}%", "status-good"),
        ("🌫️", "CO2", f"{aq.get('co2', 0)} ppm", "status-warning" if aq.get('co2', 0) > 800 else "status-good"),
        ("🌁", "PM2.5", f"{aq.get('pm2_5', 0)} µg/m³", "status-warning" if aq.get('pm2_5', 0) > 25 else "status-good"),
        ("🏭", "PM10", f"{aq.get('pm10', 0)} µg/m³", "status-good"),
        ("🧪", "TVOC", f"{aq.get('tvoc', 0)} ppb", "status-good"),
        ("🌬️", "PRESSURE", f"{aq.get('pressure', 0)} hPa", "status-good"),
        ("⚗️", "HCHO", f"{aq.get('hcho', 0)} mg/m³", "status-good"),
        ("💡", "LIGHT", f"{aq.get('light_level', 0)} Lux", "status-good"),
        ("🚶", "MOTION", f"{str(aq.get('pir', 'idle')).upper()}", "status-warning" if aq.get('pir') == 'motion_detected' else "status-good"),
    ]

    aq_grid_cols = [
        dbc.Col(
            html.Div(
                className="metric-card-box",
                children=[
                    html.Div(icon, className="metric-icon-val"),
                    html.Div(label, className="metric-label-text"),
                    html.Div(val, className=f"metric-val-text {status_cls}")
                ]
            ),
            xs=6, sm=4, md=3, lg=2, className="mb-2"
        )
        for icon, label, val, status_cls in aq_metrics
    ]
    aq_grid = dbc.Row(aq_grid_cols, className="g-2")

    # Female Smell Cards
    sf = data.get('smellfamale', initial_smell_sensor_female)
    nh3_f = sf.get('nh3', 0)
    female_status_text = "WARNING: HIGH NH3" if nh3_f > 1.2 else "FRESH AIR"
    female_status_cls = "card-header-badge status-danger" if nh3_f > 1.2 else "card-header-badge status-good"

    sf_metrics = [
        ("🔋", "BATTERY", f"{sf.get('battery', 0)}%", "status-good"),
        ("🌡️", "TEMP", f"{sf.get('temperature', 0)}°C", "status-good"),
        ("💧", "HUMIDITY", f"{sf.get('humidity', 0)}%", "status-good"),
        ("💨", "NH3", f"{nh3_f} ppm", "status-warning" if nh3_f > 0.8 else "status-good"),
        ("💀", "H2S", f"{sf.get('h2s', 0)} ppm", "status-good"),
    ]
    sf_grid_cols = [
        dbc.Col(
            html.Div(
                className="metric-card-box",
                children=[
                    html.Div(icon, className="metric-icon-val"),
                    html.Div(label, className="metric-label-text"),
                    html.Div(val, className=f"metric-val-text {status_cls}")
                ]
            ),
            xs=6, sm=4, className="mb-2"
        )
        for icon, label, val, status_cls in sf_metrics
    ]
    sf_grid = dbc.Row(sf_grid_cols, className="g-2")

    # Male Smell Cards
    sm = data.get('smellmale', initial_smell_sensor_male)
    nh3_m = sm.get('nh3', 0)
    male_status_text = "WARNING: HIGH NH3" if nh3_m > 1.2 else "FRESH AIR"
    male_status_cls = "card-header-badge status-danger" if nh3_m > 1.2 else "card-header-badge status-good"

    sm_metrics = [
        ("🔋", "BATTERY", f"{sm.get('battery', 0)}%", "status-good"),
        ("🌡️", "TEMP", f"{sm.get('temperature', 0)}°C", "status-good"),
        ("💧", "HUMIDITY", f"{sm.get('humidity', 0)}%", "status-good"),
        ("💨", "NH3", f"{nh3_m} ppm", "status-warning" if nh3_m > 0.8 else "status-good"),
        ("💀", "H2S", f"{sm.get('h2s', 0)} ppm", "status-good"),
    ]
    sm_grid_cols = [
        dbc.Col(
            html.Div(
                className="metric-card-box",
                children=[
                    html.Div(icon, className="metric-icon-val"),
                    html.Div(label, className="metric-label-text"),
                    html.Div(val, className=f"metric-val-text {status_cls}")
                ]
            ),
            xs=6, sm=4, className="mb-2"
        )
        for icon, label, val, status_cls in sm_metrics
    ]
    sm_grid = dbc.Row(sm_grid_cols, className="g-2")

    # Door Stall Occupancy Status
    doors_data = data.get('doors', initial_door_status)
    door_mappings = [
        ("raaspal/TestdoorM1", "M1 Stall", "🚹"),
        ("raaspal/TestdoorM2", "M2 Stall", "🚹"),
        ("raaspal/TestdoorM3", "M3 Stall", "🚹"),
        ("raaspal/TestdoorF1", "F1 Stall", "🚺"),
        ("raaspal/TestdoorF2", "F2 Stall", "🚺"),
        ("raaspal/TestdoorF3", "F3 Stall", "🚺"),
        ("raaspal/TestdoorF4", "F4 Stall", "🚺"),
    ]

    occupied_count = 0
    stall_cards = []
    
    for key, label, icon in door_mappings:
        door_info = doors_data.get(key, {})
        status_val = door_info.get("magnet_status", "open") if isinstance(door_info, dict) else str(door_info)
        is_open = (status_val == "open")
        if not is_open:
            occupied_count += 1
        stall_cards.append(create_stall_card(label, icon, is_open))

    total_stalls = len(door_mappings)
    occupancy_summary = f"{occupied_count} / {total_stalls} OCCUPIED"

    # Append to History Buffer for Graphs
    history_timestamps.append(datetime.now().strftime("%H:%M:%S"))
    history_temp.append(aq.get('temperature', 24.0))
    history_co2.append(aq.get('co2', 400))
    history_pm25.append(aq.get('pm2_5', 10.0))

    # Plotly Live Trend Figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(history_timestamps), y=list(history_temp),
        mode='lines+markers', name='Temp (°C)',
        line=dict(color='#38bdf8', width=3, shape='spline'),
        marker=dict(size=6, color='#38bdf8')
    ))
    fig.add_trace(go.Scatter(
        x=list(history_timestamps), y=list(history_pm25),
        mode='lines+markers', name='PM2.5 (µg/m³)',
        line=dict(color='#a855f7', width=2, dash='dot', shape='spline'),
        marker=dict(size=5, color='#a855f7')
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0.15)',
        font=dict(color='#94a3b8', family='Inter'),
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(gridcolor='rgba(255,255,255,0.06)', showgrid=True),
        yaxis=dict(gridcolor='rgba(255,255,255,0.06)', showgrid=True),
        legend=dict(orientation='h', y=1.1, x=0.01, font=dict(color='#f8fafc'))
    )

    return (
        aq_grid,
        sf_grid,
        sm_grid,
        stall_cards,
        fig,
        now_str,
        occupancy_summary,
        female_status_text,
        female_status_cls,
        male_status_text,
        male_status_cls
    )

if __name__ == '__main__':
    print("Starting RaasPal Smart Restroom Telemetry Dashboard on http://0.0.0.0:8080...")
    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    except AttributeError:
        app.run_server(host='0.0.0.0', port=8080, debug=False)

