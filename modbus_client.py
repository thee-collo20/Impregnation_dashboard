from pymodbus.client import ModbusTcpClient

from config import PLC_CONFIG


class FactoryPLC:
    """Small read-only client for the impregnation-line PLC."""

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
        """Read only the values used by the dashboard, batching holding registers."""
        reads = {
            "coils": (self.client.read_coils(0, 4), lambda response: response.bits[:4]),
            "descrete": (
                self.client.read_discrete_inputs(0, 4),
                lambda response: response.bits[:4],
            ),
            # Oven values use registers 0-15; motor values use 20-22.
            "holding": (
                self.client.read_holding_registers(0, 23),
                lambda response: response.registers,
            ),
            "input_regs": (
                self.client.read_input_registers(0, 2),
                lambda response: response.registers,
            ),
        }

        data = {}
        for name, (response, get_values) in reads.items():
            if response.isError():
                raise RuntimeError(f"PLC returned an error reading {name}")
            data[name] = get_values(response)
        return data

    # Keep the older method spelling available for any existing callers.
    def readAll(self):
        return self.read_all()
