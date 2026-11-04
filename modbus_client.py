from pymodbus.client import ModbusTcpClient
from config import PLC_CONFIG


class FactoryPLC:
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
        data = {}
        try:
            coils = self.client.read_coils(0, 8)
            if not coils.isError():
                data["coils"] = coils.bits[:8]

            discrete = self.client.read_discrete_inputs(0, 8)
            if not discrete.isError():
                data["descrete"] = discrete.bits[:8]

            holding = self.client.read_holding_registers(0, 20)
            if not holding.isError():
                data["holding"] = holding.registers

            input_regs = self.client.read_input_registers(0, 6)
            if not input_regs.isError():
                data["input_regs"] = input_regs.registers
        except Exception as exc:
            data["Error"] = str(exc)

        return data

    def readAll(self):
        return self.read_all()
