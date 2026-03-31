from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional, Sequence, Union
import argparse
import re
import subprocess

try:
    from ..geometry.load_plant import load_surface_container, clone_surface_container
    from ..geometry.modify_leaf_traits import create_modified_plant_obj
    from ..geometry.build_field import build_field
    from .prepare_configs import prepare_helios_config
except ImportError:  # pragma: no cover
    from geometry.load_plant import load_surface_container, clone_surface_container
    from geometry.modify_leaf_traits import create_modified_plant_obj
    from geometry.build_field import build_field
    from prepare_configs import prepare_helios_config

PathLike = Union[str, Path]
PAR_VALUE_RE = re.compile(r"PAR_VALUE:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")



def run_command(cmd: Sequence[str], cwd: Optional[PathLike] = None) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"CMD: {' '.join(cmd)}\n"
            f"Return code: {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    return result



def resolve_helios_executable(build_dir: PathLike, executable_name: str = "par_parallel") -> Path:
    build_dir = Path(build_dir)
    candidates = [
        build_dir / executable_name,
        build_dir / "bin" / executable_name,
        build_dir / "par_parallel" / executable_name,
    ]
    for exe in candidates:
        if exe.exists() and exe.is_file():
            return exe
    raise FileNotFoundError(
        f"Could not find executable '{executable_name}' under build directory: {build_dir}"
    )



def extract_par_value(stdout_text: str) -> Optional[float]:
    match = PAR_VALUE_RE.search(stdout_text)
    if match:
        return float(match.group(1))
    return None



def expected_helios_log_paths(field_obj_path: PathLike) -> dict[str, Path]:
    field_obj_path = Path(field_obj_path)
    log_dir = field_obj_path.parent / "helios_logs"
    stem = field_obj_path.stem
    return {
        "log_dir": log_dir,
        "hourly_csv": log_dir / f"{stem}_hourly.csv",
        "total_csv": log_dir / f"{stem}_total.csv",
    }



def create_canopy_and_field(
    base_plant_json: PathLike,
    lengths: Sequence[float],
    widths: Sequence[float],
    theta: Sequence[float],
    phi: Sequence[float],
    plant_obj_output: PathLike,
    field_obj_output: PathLike,
    row_spacing_m: float,
    plant_spacing_m: float,
    rotation_log_csv: Optional[PathLike] = None,
):
    base_surface = load_surface_container(base_plant_json)
    working_surface = clone_surface_container(base_surface)

    plant_obj_output = create_modified_plant_obj(
        surface_container=working_surface,
        lengths=lengths,
        widths=widths,
        theta=theta,
        phi=phi,
        output_path=plant_obj_output,
    )

    field_obj_output = build_field(
        plant_obj_path=plant_obj_output,
        row_spacing_m=row_spacing_m,
        plant_spacing_m=plant_spacing_m,
        rotation_log_csv=rotation_log_csv,
        output_path=field_obj_output,
    )
    return Path(plant_obj_output), Path(field_obj_output)



def run_helios_simulation(
    helios_build_dir: PathLike,
    ini_path: PathLike,
    executable_name: str = "par_parallel",
):
    exe = resolve_helios_executable(helios_build_dir, executable_name=executable_name)
    cmd = [str(exe), str(Path(ini_path).resolve())]
    return run_command(cmd, cwd=exe.parent)



def run_full_pipeline(
    base_plant_json: PathLike,
    lengths: Sequence[float],
    widths: Sequence[float],
    theta: Sequence[float],
    phi: Sequence[float],
    plant_obj_output: PathLike,
    field_obj_output: PathLike,
    row_spacing_m: float,
    plant_spacing_m: float,
    helios_ini_template: PathLike,
    helios_ini_output: PathLike,
    helios_build_dir: PathLike,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    utc_offset: Optional[int] = None,
    helios_overrides: Optional[Mapping[str, Mapping[str, object]]] = None,
    rotation_log_csv: Optional[PathLike] = None,
    executable_name: str = "par_parallel",
):
    plant_obj_path, field_obj_path = create_canopy_and_field(
        base_plant_json=base_plant_json,
        lengths=lengths,
        widths=widths,
        theta=theta,
        phi=phi,
        plant_obj_output=plant_obj_output,
        field_obj_output=field_obj_output,
        row_spacing_m=row_spacing_m,
        plant_spacing_m=plant_spacing_m,
        rotation_log_csv=rotation_log_csv,
    )

    ini_path = prepare_helios_config(
        template_path=helios_ini_template,
        output_path=helios_ini_output,
        field_obj_path=field_obj_path,
        latitude=latitude,
        longitude=longitude,
        utc_offset=utc_offset,
        additional_overrides=helios_overrides,
    )

    result = run_helios_simulation(
        helios_build_dir=helios_build_dir,
        ini_path=ini_path,
        executable_name=executable_name,
    )

    log_paths = expected_helios_log_paths(field_obj_path)
    return {
        "plant_obj": plant_obj_path,
        "field_obj": field_obj_path,
        "helios_ini": Path(ini_path),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "par_value_stdout": extract_par_value(result.stdout),
        **log_paths,
    }



def _parse_float_list(raw: str):
    return [float(x.strip()) for x in raw.split(",") if x.strip()]



def main():
    parser = argparse.ArgumentParser(description="Run one canopy + Helios par_parallel simulation.")
    parser.add_argument("--base-plant-json", required=True)
    parser.add_argument("--lengths", required=True, help="Comma-separated leaf lengths")
    parser.add_argument("--widths", required=True, help="Comma-separated leaf widths")
    parser.add_argument("--theta", required=True, help="Comma-separated z-rotation angles")
    parser.add_argument("--phi", required=True, help="Comma-separated y-rotation angles")
    parser.add_argument("--plant-obj-output", required=True)
    parser.add_argument("--field-obj-output", required=True)
    parser.add_argument("--row-spacing-m", type=float, required=True)
    parser.add_argument("--plant-spacing-m", type=float, required=True)
    parser.add_argument("--helios-ini-template", required=True)
    parser.add_argument("--helios-ini-output", required=True)
    parser.add_argument("--helios-build-dir", required=True, help="Example: src/cpp/par_parallel/build")
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--utc-offset", type=int)
    parser.add_argument("--rotation-log-csv")
    parser.add_argument("--executable-name", default="par_parallel")

    args = parser.parse_args()

    result = run_full_pipeline(
        base_plant_json=args.base_plant_json,
        lengths=_parse_float_list(args.lengths),
        widths=_parse_float_list(args.widths),
        theta=_parse_float_list(args.theta),
        phi=_parse_float_list(args.phi),
        plant_obj_output=args.plant_obj_output,
        field_obj_output=args.field_obj_output,
        row_spacing_m=args.row_spacing_m,
        plant_spacing_m=args.plant_spacing_m,
        helios_ini_template=args.helios_ini_template,
        helios_ini_output=args.helios_ini_output,
        helios_build_dir=args.helios_build_dir,
        latitude=args.latitude,
        longitude=args.longitude,
        utc_offset=args.utc_offset,
        rotation_log_csv=args.rotation_log_csv,
        executable_name=args.executable_name,
    )

    print("Plant OBJ:", result["plant_obj"])
    print("Field OBJ:", result["field_obj"])
    print("Helios INI:", result["helios_ini"])
    print("Helios log dir:", result["log_dir"])
    print("Hourly CSV:", result["hourly_csv"])
    print("Total CSV:", result["total_csv"])
    if result["par_value_stdout"] is not None:
        print("PAR_VALUE:", result["par_value_stdout"])
    print(result["stdout"])


if __name__ == "__main__":
    main()
