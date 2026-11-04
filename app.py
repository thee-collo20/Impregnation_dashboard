import random
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from Logic import alarms, motors, ovens, sensors

try:
    from modbus_client import FactoryPLC
except ImportError:
    FactoryPLC = None


POLL_INTERVAL_SECONDS = 2
MAX_CHART_SAMPLES = 200

st.set_page_config(
    page_title="BIASHARA MASTERS IMPREGNATION LINE MONITOR",
    layout="wide",
)
st.markdown(
    """
    <style>
    .stApp { background: #f5f7fa; }
    h1, h2, h3 { color: #0d47a1 !important; font-family: monospace; }
    div[data-testid="stMetric"] { background: white; border-radius: 12px;
        border-left: 4px solid #0d47a1; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=POLL_INTERVAL_SECONDS, show_spinner=False)
def read_plc_snapshot():
    """Cache a short-lived PLC snapshot so simultaneous viewers share polling."""
    if FactoryPLC is None:
        return None, "pymodbus is unavailable"

    plc = FactoryPLC()
    try:
        if not plc.connect():
            return None, "PLC connection failed"
        return plc.read_all(), None
    except Exception as exc:
        return None, str(exc)
    finally:
        plc.close()


def simulated_snapshot():
    return {
        "coils": [True, True, True, True],
        "descrete": [random.choice([True, False]), True, True, False],
        "holding": [145 + random.uniform(-2, 2) for _ in range(6)]
        + [0] * 4
        + [22, 22, 35]
        + [0] * 7,
        "input_regs": [320, 85],
    }


def render_dashboard():
    snapshot, read_error = read_plc_snapshot()
    is_live = snapshot is not None
    raw = snapshot if is_live else simulated_snapshot()

    st.markdown("BIASHARA MASTERS SAWMILL")
    mode = "LIVE" if is_live else "SIMULATION"
    st.caption(
        f"SERVER 192.168.1.88:502 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EAT | {mode}"
        + (f" | PLC: {read_error}" if read_error else "")
    )

    oven_data = ovens.process_ovens(raw["holding"])
    motor_data = motors.process_motors(raw["coils"], raw["holding"])
    sensor_data = sensors.process_sensors(raw["descrete"], raw["input_regs"])
    alert_list = alarms.evaluate_alarms(oven_data, motor_data, sensor_data)

    cols = st.columns(3)
    for i in range(6):
        oven = oven_data[f"oven{i + 1}"]
        cols[i % 3].metric(
            f"Oven-{i + 1} {oven['status']}",
            f"{oven['actual']} Celsius",
            f"{oven['delta']:+.1f} Celsius vs {oven['setpoint']} Celsius",
        )

    if "ticks" not in st.session_state:
        st.session_state.ticks = []
    st.session_state.ticks.append(
        {
            "time": datetime.now(),
            **{
                f"oven{i + 1}": oven_data[f"oven{i + 1}"]["actual"]
                for i in range(6)
            },
        }
    )
    st.session_state.ticks = st.session_state.ticks[-MAX_CHART_SAMPLES:]

    history = pd.DataFrame(st.session_state.ticks)
    colors = ["#0d47a1", "#1976d2", "#ef6c00", "#6a1b9a", "#c62828", "#f9a825"]
    fig = go.Figure()
    for i, color in enumerate(colors):
        fig.add_trace(
            go.Scatter(
                x=history["time"],
                y=history[f"oven{i + 1}"],
                name=f"OVEN-{i + 1}",
                line={"color": color},
            )
        )
    fig.update_layout(
        template="plotly_white",
        height=380,
        title="TEMPERATURE TREND",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    st.plotly_chart(fig, use_container_width=True)

    _, state_col = st.columns([2, 1])
    with state_col:
        st.markdown("### SYSTEM STATE")
        st.write(f"FEED RATE: {sensor_data.get('resin_weight', 0)} kg/hr")
        st.write(
            f"MAIN DRIVE: {'RUNNING' if motor_data.get('main_drive', {}).get('run') else 'STOPPED'}"
        )
        st.write(f"E-STOP OK: {sensor_data.get('e_stop_ok')}")
        st.markdown("### ALERTS")
        for alert in alert_list:
            if alert["level"] == "CRIT":
                st.error(alert["msg"])
            else:
                st.warning(alert["msg"])

    st.markdown(
        "BIASHARA MASTERS CONTROL v1.0.0 | a product of KUTSWAINC."
    )


# A fragment refreshes the dashboard without blocking the Streamlit server with
# time.sleep() or forcing a full-app st.rerun() loop.
if hasattr(st, "fragment"):
    @st.fragment(run_every=POLL_INTERVAL_SECONDS)
    def live_dashboard():
        render_dashboard()

    live_dashboard()
else:
    # Compatibility with older Streamlit releases: render once rather than
    # introducing a blocking rerun loop.
    render_dashboard()
