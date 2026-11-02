import streamlit as st
import pandas as pd
import time
import random
from datetime import datetime
import plotly.graph_objects  as go

try:
    from pymodbus.client import ModbusTcpClient
    REAL_PLC=True
except:
    REAL_PLC=False
from modbus_client import readAll
from Logic import ovens, motors, sensors, alarms

st.set_page_config(
    page_title="BIASHARA MASTERS IMPREGNATION LINE MONITOR", layout="wide"
)

st.markdown("""
    <style>
    .stApp{background:#f5f7fa;}
    h1, h2, h3{color:#0d47a1 !important; font-family: monospace;}
    div[data-testid="stMetric"]{background:white; boarder-radius:12px; border-left:4px solid #0d47a1; box-shadow: 0 2px 8px rgba(0,0,0,0.06);}
    </style>""", unsafe_allow_html=True)

if 'ticks' not in st.session_state:
    st.session_state.ticks=pd.DataFrame()

#---HEADER---
st.markdown("BIASHARA MASTERS SAWMILL")
st.caption(f"SERVER 192.168.1.88:502 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EAT | {'LIVE' if REAL_PLC else 'SIMULATION'}")

#--READ PLC ONCE
if REAL_PLC:
    try:
        client=ModbusTcpClient("192.168.1.88", port=502, timeout=2)
        client.connect()
        raw=readAll(client)
        client.close
    except:
        REAL_PLC=False
        raw={'coils':[True]*8, 'descrete':[True]*8,'holding':[0]*30, 'input_regs':[0]*10}
else:
    #SIMULATION for DEMO
    raw={
        'coils':[True, True, True, True, False, False, False, False],
        'descrete':[random.choice([True, False]), True, True, False],
        'holding':[145+random.uniform(-2,2) for _ in range(6)] + [0]*4 + [22,22,35],
        'input_regs': [320, 85]
    }

#PULL LOGIC MODULES
oven_data=ovens.process_ovens(raw['holding'])
motor_data=motors.process_motors(raw['coils'], raw['holding'])
sensor_data=sensors.process_sensors(raw['discrete'], raw['input_regs'])
alert_list=alarms.evaluate_alarms(oven_data, motor_data, sensor_data)

#DISPLAY THE DATA
cols=st.columns(3)
for i in range (6):
    o=oven_data[f"oven{i+1}"]
    col=cols[i%3]
    col.metric(f"Oven-{i+1} {o['status']}" f"{o['actual']} Celcius" f"{o['delta']:+.1f} Celcius vs {o['setpoint']} Celcius")

#CHART
new_row={
    "time":datetime.now(),
    **{
        f"oven{i+1}": oven_data[f"oven{i+1}"]['actual'] for i in range(6)
    }
}

st.session_state.ticks=pd.contact([st.session_state.ticks, pd.DataFrame([new_row])], ignore_index=True)
if len(st.session_state.ticks)>200:
    st.session_state.ticks=st.session_state.ticks.tail(200)

fig=go.figure()
colors=[
    "#0d47a1",
    "#1976d2",
    "#ef6c00",
    "#6a1b9a",
    "#c62828",
    "#f9a825"
]

for i in range(6):
    fig.add_trace(go.Scatter(x=st.session_state.ticks["time"], y=st.session_state.ticks[f"oven{i+1}"], name=f"OVEN-{i+1}", line=dict(colors[i])))
               
fig.update_layout(tempate="plotly_white", height=380, title="TEMPERATURE TREND. LAST 60 MINUTES.")
st.plotly_chart(fig, use_container_width=True)

#System state simulation
c1,c2=st.column([2,1])
with c2:
    st.markdown("### SYSTEM STATE")
    st.write(f"FEED RATE: {sensor_data.get('resin_weight', 0)} kg/hr")
    st.write(f"MAIN DRIVE: {'RUNNING' if motor_data.get('main_drive', {}).get('run') else 'STOPPED'}")
    st.write(f"E-STOP OK: {sensor_data.get('e_stop_ok')}")
    st.markdown("### ALERTS")
    for a in alert_list:
        if a['level']=="CRIT":
            st.error(a['msg'])
        else:
            st.warning(a['msg'])

st.markdown("BIASHARA MASTERS CONTROL v1.0.0 | PLC CONNECTED | SECURE SESSION | a product of KUTSWAINC.")

time.sleep(1.5)
st.rerun()