from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ENV_NAMES = [
    "DATABASE_URL",
    "SECRET_KEY",
    "ADMIN_TOKEN",
    "GUZO_JWT_SECRET",
    "GUZO_DEFAULT_ADMIN_PASSWORD",
    "ENVIRONMENT",
    "PYTHON_VERSION",
]


def main() -> int:
    print("RENDER_STARTUP_CHECK_BEGIN")
    print(f"python_version={sys.version}")
    print(f"cwd={Path.cwd()}")
    print(f"project_root={PROJECT_ROOT}")

    for name in ENV_NAMES:
        status = "present" if os.getenv(name) else "missing"
        print(f"env:{name}={status}")

    try:
        from guzo_backend.main import app

        print(f"routes={len(app.routes)}")
        print("RENDER_STARTUP_CHECK_OK")
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
