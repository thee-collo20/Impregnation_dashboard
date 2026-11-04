from datetime import datetime
import time

import streamlit as st

from Logic import alarms, motors, ovens, sensors

try:
    from modbus_client import FactoryPLC
except ImportError:
    FactoryPLC = None


POLL_INTERVAL_SECONDS = 2
MAX_CHART_SAMPLES = 120
MAX_READ_ATTEMPTS = 3
RETRY_BASE_SECONDS = 0.25

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
    """Health-check by reading a snapshot; retry transient failures with backoff."""
    if FactoryPLC is None:
        return None, "pymodbus is unavailable"

    last_error = "PLC read failed"
    for attempt in range(MAX_READ_ATTEMPTS):
        plc = FactoryPLC()
        try:
            if not plc.connect():
                raise ConnectionError("PLC connection failed")
            return plc.read_all(), None
        except Exception as exc:
            last_error = str(exc)
        finally:
            try:
                plc.close()
            except Exception:
                pass
        if attempt + 1 < MAX_READ_ATTEMPTS:
            time.sleep(RETRY_BASE_SECONDS * (2 ** attempt))

    return None, last_error


def render_dashboard():
    snapshot, read_error = read_plc_snapshot()
    now = datetime.now()
    st.markdown("BIASHARA MASTERS SAWMILL")

    if snapshot is None:
        st.session_state.plc_failures = st.session_state.get("plc_failures", 0) + 1
        st.error(f"PLC OFFLINE — live values unavailable. {read_error}")
        st.caption(
            f"SERVER 192.168.1.88:502 | {now:%Y-%m-%d %H:%M:%S} | "
            f"Health: OFFLINE | Consecutive failed polls: {st.session_state.plc_failures}"
        )
        st.info("No simulated readings are shown while the PLC is unavailable.")
        st.markdown("BIASHARA MASTERS CONTROL v1.0.0 | a product of KUTSWAINC.")
        return

    st.session_state.plc_failures = 0
    st.session_state.last_plc_success = now
    st.caption(
        f"SERVER 192.168.1.88:502 | {now:%Y-%m-%d %H:%M:%S} | "
        f"Health: CONNECTED | Poll interval: {POLL_INTERVAL_SECONDS}s"
    )

    oven_data = ovens.process_ovens(snapshot["holding"])
    motor_data = motors.process_motors(snapshot["coils"], snapshot["holding"])
    sensor_data = sensors.process_sensors(snapshot["descrete"], snapshot["input_regs"])
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
            **{
                f"Oven-{i + 1}": oven_data[f"oven{i + 1}"]["actual"]
                for i in range(6)
            }
        }
    )
    st.session_state.ticks = st.session_state.ticks[-MAX_CHART_SAMPLES:]
    st.subheader("Temperature trend — recent PLC polls")
    st.line_chart(st.session_state.ticks, height=300)

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

    st.markdown("BIASHARA MASTERS CONTROL v1.0.0 | a product of KUTSWAINC.")


if hasattr(st, "fragment"):
    @st.fragment(run_every=POLL_INTERVAL_SECONDS)
    def live_dashboard():
        render_dashboard()

    live_dashboard()
else:
    # Older Streamlit versions render once; avoid a blocking sleep/rerun loop.
    render_dashboard()
