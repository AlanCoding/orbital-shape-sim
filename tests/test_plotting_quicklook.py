import numpy as np
from pathlib import Path
from tskb import plotting

def test_quicklook_saves_png(tmp_path: Path) -> None:
    log = {
        "t": np.linspace(0, 86400, 5),
        "r": np.tile([6378e3, 0.0, 0.0], (5, 1)),
        "v": np.tile([0.0, 7784.0, 0.0], (5, 1)),
    }
    out = tmp_path / "fig.png"
    plotting.quicklook(log, out)
    assert out.exists()
