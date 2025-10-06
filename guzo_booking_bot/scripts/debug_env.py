# scripts/debug_env.py

from guzo_booking_bot import config as cfg



print("— DEBUG ENV —")

print("Loaded from:", cfg.__file__)

cfg._debug_dump()