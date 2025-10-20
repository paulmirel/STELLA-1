# Get the unique identifier from the microcontroller cpu"


import microcontroller

UID = int.from_bytes(microcontroller.cpu.uid, "big") % 10000

print("unique identifier (UID) : {0}".format( UID ))
