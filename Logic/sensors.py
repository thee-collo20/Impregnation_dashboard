#Descrete inputs Logic
#Safety, Board-present, E-STOP, Resin level.

def process_sensors(descrete_inputs, input_regs):
    result={}

    try:
        result["board_present"]=bool(descrete_inputs[0]) if len(descrete_inputs)>0 else False
        result["safety_door"]=bool(descrete_inputs[1]) if len(descrete_inputs)>1 else True
        result["e_stop_ok"]=bool(descrete_inputs[2]) if len(descrete_inputs)>2 else True
        result["resin_low"]=not bool(descrete_inputs[3]) if len(descrete_inputs)>3 else False

        result["resin_weight"]=input_regs[0] if len(input_regs)>0 else 0
        result["moisture"]=input_regs[1] if len(input_regs)>1 else 0

        result["system_ok"]=result["e_stop_ok"] and result["safety_door"]

    except Exception as e:
        result["error"]=str(e)
    return result