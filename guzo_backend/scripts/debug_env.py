# scripts/debug_env.py

from guzo_backend import config as cfg



print("ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ DEBUG ENV ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ")

print("Loaded from:", cfg.__file__)

cfg._debug_dump()