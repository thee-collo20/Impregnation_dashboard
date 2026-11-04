import time

from pymodbus.client import ModbusTcpClient

from config import PLC_CONFIG


class FactoryPLC:
    """Read-only client for the impregnation-line PLC."""

    def __init__(self):
        self.client = ModbusTcpClient(
            PLC_CONFIG["ip"],
            port=PLC_CONFIG["port"],
            timeout=PLC_CONFIG["timeout"],
        )

    def connect(self):
        return self.client.connect()

    def close(self):
        self.client.close()

    def read_all(self):
        """Read only dashboard values, grouping contiguous holding registers."""
        data = {}
        reads = (
            ("coils", self.client.read_coils(0, 4), lambda r: r.bits[:4]),
            (
                "descrete",
                self.client.read_discrete_inputs(0, 4),
                lambda r: r.bits[:4],
            ),
            # Six oven actuals/setpoints and three drive values.
            ("holding", self.client.read_holding_registers(0, 23), lambda r: r.registers),
            ("input_regs", self.client.read_input_registers(0, 2), lambda r: r.registers),
        )
        for name, response, get_values in reads:
            if response is None or response.isError():
                raise RuntimeError(f"PLC returned an error reading {name}")
            data[name] = get_values(response)
        return data

    def readAll(self):
        """Backward-compatible alias."""
        return self.read_all()
