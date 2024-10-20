import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output
import requests

# Flask URL where MQTT data is served
FLASK_URL = 'http://127.0.0.1:5000/data'

# Initialize Dash app with a custom theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])  # Using LUX theme for a modern look

# Initial Values for Air Quality and Smell Sensor Metrics
initial_air_quality = {
    "temperature": 0,
    "humidity": 0,
    "co2": 0,
    "pm2_5": 0,
    "pm10": 0,
    "tvoc": 0,
    "pressure": 0,
    "hcho": 0,
    "light_level": 0,
    "pir": "idle"
}

initial_smell_sensor = {
    "battery": 0,
    "temperature": 0,
    "humidity": 0,
    "nh3": 0,
    "h2s": 0
}

# Initial Values for Restroom Door Statuses (All restrooms are initially available/open)
initial_door_status = {
    "raaspal/TestdoorM1": {"magnet_status": "open"},
    "raaspal/TestdoorM2": {"magnet_status": "open"},
    "raaspal/TestdoorM3": {"magnet_status": "open"},
    "raaspal/TestdoorF1": {"magnet_status": "open"},
    "raaspal/TestdoorF2": {"magnet_status": "open"},
    "raaspal/TestdoorF3": {"magnet_status": "open"},
    "raaspal/TestdoorF4": {"magnet_status": "open"} 
}

def create_door_status(doors_data):
    door_elements = []
    # Define all restrooms to be shown initially
    restrooms = {
        "raaspal/TestdoorM1": "🚹", "raaspal/TestdoorM2": "🚹", "raaspal/TestdoorM3": "🚹",
        "raaspal/TestdoorF1": "🚺", "raaspal/TestdoorF2": "🚺", "raaspal/TestdoorF3": "🚺",
        "raaspal/TestdoorF4": "🚺"  # New female restroom
    }

    # Create icons for male restrooms first
    for door, icon in restrooms.items():
        if icon == "🚹":  # Only male restrooms
            is_open = doors_data.get(door, {}).get("magnet_status", "open") == "open"

            # Apply style for icon
            icon_style = {
                "font-size": "2.8rem",  # Smaller icon size
                "margin": "0.1rem",
                "position": "relative",  # Position relative for overlay
                "display": "inline-block",
            }

            # Animated red line for occupied restrooms
            line_style = {
                "content": '""',
                "position": "absolute",
                "top": "42%",  # Center the line vertically
                "left": "-12%",  # Start slightly inside the icon
                "right": "-10%",  # End slightly inside the icon
                "height": "10px",  # Make the line thinner
                "background-color": "rgba(255, 0, 0, 0.5)",  # 50% transparent red
                "transform": "rotate(-45deg)",  # Rotate the line for a diagonal slash
            }

            # Add animation class if occupied
            class_name = "door-status-icon" + (" occupied" if not is_open else "")

            # Create the icon element with a conditional red line for occupancy
            door_elements.append(
                html.Div(
                    children=[
                        html.Div(icon, style=icon_style, className=class_name),  # Icon
                        html.Div(style=line_style) if not is_open else None  # Red line only if occupied
                    ],
                    style={"position": "relative", "display": "inline-block"}  # Needed for absolute positioning
                )
            )
    
    # Add a line emoji to separate male and female restrooms
    door_elements.append(
        html.Div(
            "|",  # Line emoji
            style={
                "font-size": "3rem",  # Size of the line emoji
                "margin": "0 5px",  # Add space around the divider
                "display": "inline-block",  # Inline to align with icons
            }
        )
    )

    # Create icons for female restrooms
    for door, icon in restrooms.items():
        if icon == "🚺":  # Only female restrooms
            is_open = doors_data.get(door, {}).get("magnet_status", "open") == "open"

            # Apply style for icon
            icon_style = {
                "font-size": "2.8rem",  # Smaller icon size
                "margin": "0.1rem",
                "position": "relative",  # Position relative for overlay
                "display": "inline-block",
            }

            # Animated red line for occupied restrooms
            line_style = {
                "content": '""',
                "position": "absolute",
                "top": "45%",  # Center the line vertically
                "left": "-10%",  # Start slightly inside the icon
                "right": "-10%",  # End slightly inside the icon
                "height": "10px",  # Make the line thinner
                "background-color": "rgba(255, 0, 0, 0.5)",  # 50% transparent red
                "transform": "rotate(-45deg)",  # Rotate the line for a diagonal slash
            }

            # Add animation class if occupied
            class_name = "door-status-icon" + (" occupied" if not is_open else "")

            # Create the icon element with a conditional red line for occupancy
            door_elements.append(
                html.Div(
                    children=[
                        html.Div(icon, style=icon_style, className=class_name),  # Icon
                        html.Div(style=line_style) if not is_open else None  # Red line only if occupied
                    ],
                    style={"position": "relative", "display": "inline-block"}  # Needed for absolute positioning
                )
            )

    return door_elements

# Initialize door status elements for initial layout rendering
door_status_elements = create_door_status(initial_door_status)

# Layout for responsive dimensions
app.layout = dbc.Container(
    [
        html.Div(
            className="background",
            children=[
                # Replace text title with an image title from assets folder
                html.Div(
                    html.Img(src='/assets/L-02.png', className="main-title", style={"width": "85%", "height": "auto"}),  # Reduce size
                    style={"text-align": "center", "margin-bottom": "2vh", "margin-top": "0vh"}
                ),
                dcc.Interval(id='interval-component', interval=2 * 1000, n_intervals=0),  # Update every 5 seconds

                # Air Quality Metrics - Moved up closer to the title
                dbc.Row(
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("คุณภาพอากาศในโชว์รูม", style={"font-size": "1rem", "font-weight": "bold"}),  # Smaller font size
                                dbc.CardBody(html.Div(id='airquality-metrics', className="airquality-metrics")),
                            ],
                            className="graph-card",
                            style={"position": "relative", "margin-top": "-5vh", "margin-bottom": "0.5vh", "padding": "-10vh", "width": "100%"}, 
                        ),
                        width=12,
                    ),
                    className="mb-1",
                ),

                # Smell Sensor Metrics for Female and Male in the same row
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Card(
                                [
                                    dbc.CardHeader("คุณภาพอากาศห้องน้ำหญิง", style={"font-size": "1rem", "font-weight": "bold"}),  # Smaller font size
                                    dbc.CardBody(html.Div(id='smell-metrics-female', className="smell-metrics-female")),
                                ],
                                className="graph-card",
                                style={"position": "relative", "margin-top": "0vh", "margin-bottom": "0.5vh", "padding": "-10vh", "width": "100%"}, 
                            ),
                            width=6,  # Adjust the width to 6 for half the row
                        ),
                        dbc.Col(
                            dbc.Card(
                                [
                                    dbc.CardHeader("คุณภาพอากาศห้องน้ำชาย", style={"font-size": "1rem", "font-weight": "bold"}),  # Smaller font size
                                    dbc.CardBody(html.Div(id='smell-metrics-male', className="smell-metrics-male")),
                                ],
                                className="graph-card",
                                style={"position": "relative", "margin-top": "0vh", "margin-bottom": "0.5vh", "padding": "-10vh", "width": "100%"}, 
                            ),
                            width=6,  # Adjust the width to 6 for half the row
                        ),
                    ],
                    className="mb-1",
                ),

                # Restroom Door Status
                dbc.Row(
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("สถานะห้องน้ำ", style={"font-size": "1rem", "font-weight": "bold"}),  # Smaller font size
                                dbc.CardBody(html.Div(door_status_elements, id='door-status', className="door-status")),  # Set initial door status
                            ],
                            className="graph-card",  # Same class as other metric cards
                            style={"position": "relative", "margin-top": "0vh", "margin-bottom": "0.5vh", "padding": "-10vh", "width": "100%"},  # Consistent styling
                        ),
                        width=12,
                    ),
                ),

                # Powered by RaasPal text at the bottom
                html.Div("Powered by RAASPAL", className="powered-by"),  # Moved to bottom
            ],
            style={
                "width": "100%",         # Responsive width
                "height": "100vh",       # Responsive height using viewport height
                "margin": "auto",        # Center the container on the screen
                "padding": "1vh",        # Reduce padding
                "display": "flex",       # Flexbox for alignment
                "flex-direction": "column",  # Arrange items vertically
                "justify-content": "flex-start", # Align items from the top and allow scrolling
                "align-items": "center", # Center content horizontally
                "overflow-y": "auto",    # Allow vertical scrolling
                "overflow-x": "hidden",  # Prevent horizontal scrolling
            },
        )
    ],
    fluid=True,
)

@app.callback(
    [Output('airquality-metrics', 'children'),
     Output('smell-metrics-female', 'children'),
     Output('smell-metrics-male', 'children'),
     Output('door-status', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    # Fetch data from Flask server
    try:
        data = requests.get(FLASK_URL).json()
    except:
        # In case of connection error, use initial values
        data = {"airquality": initial_air_quality, "smellfamale": initial_smell_sensor, "smellmale": initial_smell_sensor, "doors": initial_door_status}
    
    # Extract data for air quality
    airquality = data['airquality']
    airquality_metrics = []
    metric_data = [
        ("🌡️", f"อุณหภูมิ: {airquality['temperature']}°C"),
        ("💧", f"ความชื้น: {airquality['humidity']}%"),
        ("🌫️", f"CO2: {airquality['co2']} ppm"),
        ("🌁", f"PM2.5: {airquality['pm2_5']} µg/m³"),
        ("🏭", f"PM10: {airquality['pm10']} µg/m³"),
        ("🧪", f"TVOC: {airquality['tvoc']} ppb"),
        ("🌬️", f"ความดัน: {airquality['pressure']} hPa"),
        ("⚗️", f"HCHO: {airquality['hcho']} mg/m³"),
        ("💡", f"แสงสว่าง: {airquality['light_level']}"),
        ("🚶", f"PIR: {airquality['pir']}")
    ]

    for i in range(0, len(metric_data), 2):  # Adjust to fit more metrics per row
        row_data = metric_data[i:i+2]
        num_columns = len(row_data)
        row = dbc.Row(
            [
                dbc.Col(
                    html.Div([
                        html.Div(icon, className="metric-icon", style={"font-size": "1.2rem", "margin": "0"}),  # Much smaller font size for icons
                        html.H6(value, className="metric-value", style={"font-size": "0.6rem", "margin": "0.1rem 0", "letter-spacing": "0.1rem"})  # Label and value, smaller font
                    ], className="metric-card", style={"text-align": "center", "padding": "0.3rem"}),  # Center text, smaller padding
                    width=12 // num_columns,
                ) 
                for icon, value in row_data
            ],
            className="mb-1",
            justify="center"
        )
        airquality_metrics.append(row)
    
    # Extract data for smell sensors - Female
    smell_female = data['smellfamale']
    smell_metrics_female = []
    metric_data_female = [
        ("🔋", f"แบตเตอรี่: {smell_female.get('battery', 0)}%"),  # Using .get() to safely access dictionary keys
        ("🌡️", f"อุณหภูมิ: {smell_female.get('temperature', 0)}°C"),
        ("💧", f"ความชื้น: {smell_female.get('humidity', 0)}%"),
        ("💨", f"แอมโมเนีย (NH3): {smell_female.get('nh3', 0)} ppm"),
        ("💀", f"H2S: {smell_female.get('h2s', 0)} ppm"),
    ]

    for i in range(0, len(metric_data_female), 2):  # Adjust to fit more metrics per row
        row_data = metric_data_female[i:i+2]
        num_columns = len(row_data)
        row = dbc.Row(
            [
                dbc.Col(
                    html.Div([
                        html.Div(icon, className="metric-icon", style={"font-size": "1.2rem", "margin": "0"}),  # Much smaller font size for icons
                        html.H6(value, className="metric-value", style={"font-size": "0.6rem", "margin": "0.1rem 0", "letter-spacing": "0.1rem"})  # Label and value, smaller font
                    ], className="metric-card", style={"text-align": "center", "padding": "0.3rem"}),  # Center text, smaller padding
                    width=12 // num_columns,
                ) 
                for icon, value in row_data
            ],
            className="mb-1",
            justify="center"
        )
        smell_metrics_female.append(row)

    # Extract data for smell sensors - Male
    smell_male = data['smellmale']
    smell_metrics_male = []
    metric_data_male = [
        ("🔋", f"แบตเตอรี่: {smell_male.get('battery', 0)}%"),  # Using .get() to safely access dictionary keys
        ("🌡️", f"อุณหภูมิ: {smell_male.get('temperature', 0)}°C"),
        ("💧", f"ความชื้น: {smell_male.get('humidity', 0)}%"),
        ("💨", f"แอมโมเนีย (NH3): {smell_male.get('nh3', 0)} ppm"),
        ("💀", f"H2S: {smell_male.get('h2s', 0)} ppm"),
    ]

    for i in range(0, len(metric_data_male), 2):  # Adjust to fit more metrics per row
        row_data = metric_data_male[i:i+2]
        num_columns = len(row_data)
        row = dbc.Row(
            [
                dbc.Col(
                    html.Div([
                        html.Div(icon, className="metric-icon", style={"font-size": "1.2rem", "margin": "0"}),  # Much smaller font size for icons
                        html.H6(value, className="metric-value", style={"font-size": "0.6rem", "margin": "0.1rem 0", "letter-spacing": "0.1rem"})  # Label and value, smaller font
                    ], className="metric-card", style={"text-align": "center", "padding": "0.3rem"}),  # Center text, smaller padding
                    width=12 // num_columns,
                ) 
                for icon, value in row_data
            ],
            className="mb-1",
            justify="center"
        )
        smell_metrics_male.append(row)
    
    # Extract door statuses and create animated icons
    door_status_elements = create_door_status(data['doors'])

    return airquality_metrics, smell_metrics_female, smell_metrics_male, door_status_elements

# if __name__ == '__main__':
#     app.run_server(host='0.0.0.0', port=80, debug=True)
if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8080, debug=True, dev_tools_ui=False, dev_tools_props_check=False)
