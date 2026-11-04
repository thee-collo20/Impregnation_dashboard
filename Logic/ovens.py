# This logic handles the six ovens on the impregnation line.


def process_ovens(holding_regs):
    result = {}
    alarms = []
    actuals = []

    for i in range(6):
        actual_index = i
        setpoint_index = i + 10
        actual = holding_regs[actual_index] if len(holding_regs) > actual_index else 0
        setpoint = holding_regs[setpoint_index] if len(holding_regs) > setpoint_index else 145
        actuals.append(actual)

        delta = actual - setpoint
        status = "OK"
        if abs(delta) > 5:
            status = "CRITICAL"
            alarms.append(f"OVEN-{i + 1} {delta:+.1f} Celsius OFF TARGET")
        elif abs(delta) > 2:
            status = "WARNING"

        result[f"oven{i + 1}"] = {
            "actual": actual,
            "setpoint": setpoint,
            "delta": round(delta, 1),
            "status": status,
            "running": actual > 50,
        }

    temperature_spread = max(actuals) - min(actuals)
    result["stats"] = {
        "avg_temp": round(sum(actuals) / len(actuals), 1),
        "delta_max_min": round(temperature_spread, 1),
        "stability": round(100 - temperature_spread / 2, 1),
    }
    result["alarms"] = alarms
    return result
