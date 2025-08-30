import csv
import importlib.util
import os
from pathlib import Path

def test_leo_derived_csv(tmp_path):
    cfg_path = Path("configs/leo_100km.yaml").resolve()
    spec = importlib.util.spec_from_file_location(
        "run_leo_100km", Path("sims/run_leo_100km.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        module.main(cfg_path.as_posix(), t_final=60.0)
        out_dir = tmp_path / "outputs"
        out = out_dir / "leo_100km_derived.csv"
        assert out.exists()
        with out.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == [
            "t",
            "altitude",
            "omega",
            "theta",
            "length",
            "accel",
            "eccentricity",
            "semimajor_axis",
        ]
        assert (out_dir / "semi_major_axis.png").exists()
        assert (out_dir / "tether_length.png").exists()
        assert (out_dir / "angular_velocity.png").exists()
        assert (out_dir / "eccentricity.png").exists()
        html = out_dir / "html" / "run_summary.html"
        assert html.exists()
        text = html.read_text(encoding="utf-8")
        assert "Duration:" in text
        assert "Outcome:" in text
    finally:
        os.chdir(cwd)
