"""Root entrypoint for Streamlit cloud platforms (Hugging Face Spaces Streamlit SDK, Streamlit Community Cloud).

Loads secrets into os.environ and running FastAPI backend, starts uvicorn if needed, then launches Streamlit.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "frontend") not in sys.path:
    sys.path.insert(0, str(ROOT / "frontend"))

from app.launcher import (  # noqa: E402
    ensure_backend_running,
    get_secrets_dict,
    is_port_open,
    sync_secrets_to_env,
)


def ensure_backend() -> None:
    """Public helper that can be called from any page to ensure backend is alive."""
    ensure_backend_running()


# Always ensure backend is running when this script executes
ensure_backend_running()

# If running directly (e.g. `streamlit run app.py`), execute the main dashboard page
if __name__ in ("__main__", "streamlit.runtime.scriptrunner.script_runner"):
    runpy.run_path(str(ROOT / "frontend" / "streamlit_app.py"), run_name="__main__")
