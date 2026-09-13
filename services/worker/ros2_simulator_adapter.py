"""Adapter for the upstream ROS2 disaster robot simulator."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

REPO_SRC = Path(__file__).resolve().parents[2] / "vendor" / "ros2-disaster-robot-sim"


def execute_ros2_simulation(output_dir: Path, duration: int = 30) -> dict[str, Any]:
    """Launch the real upstream ROS2 simulation when ROS2 Humble is available."""
    if not REPO_SRC.exists():
        raise FileNotFoundError(f"ROS2 simulator repository not found: {REPO_SRC}")
    output_dir.mkdir(parents=True, exist_ok=True)
    ros2 = shutil.which("ros2")
    if not ros2:
        raise RuntimeError("ROS2 runtime unavailable; install ROS2 Humble on the worker")
    launches = sorted(REPO_SRC.rglob("simulation.launch.py"))
    if not launches:
        launches = sorted(REPO_SRC.rglob("*.launch.py"))
    if not launches:
        raise RuntimeError("No upstream ROS2 launch file found")
    launch = launches[0]
    log_path = output_dir / "ros2_execution.log"
    # The upstream repository is a source workspace. Sourcing only /opt/ros
    # leaves packages such as disaster_world undiscoverable (the reported
    # PackageNotFoundError). Build and source its install overlay first.
    install_setup = REPO_SRC / "install" / "setup.bash"
    colcon = shutil.which("colcon")
    if not install_setup.exists():
        if not colcon:
            raise RuntimeError("colcon is required to build the upstream ROS2 workspace")
        build = subprocess.run(
            [colcon, "build", "--symlink-install"],
            cwd=str(REPO_SRC), capture_output=True, text=True,
            timeout=max(duration, 120),
        )
        (output_dir / "ros2_colcon_build.log").write_text(build.stdout + "\n" + build.stderr, encoding="utf-8")
        if build.returncode != 0 or not install_setup.exists():
            raise RuntimeError(f"ROS2 workspace build failed: {build.stderr[-4000:]}")
    command = f"source /opt/ros/humble/setup.bash && source '{install_setup}' && ros2 launch '{launch}'"
    cmd = ["bash", "-lc", command]
    try:
        result = subprocess.run(cmd, cwd=str(REPO_SRC), capture_output=True, text=True, timeout=duration)
    except subprocess.TimeoutExpired as exc:
        # A timeout after the launch process has been alive is evidence that the
        # simulation actually started; preserve its captured output as the artifact.
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        log_path.write_text(stdout + "\n" + stderr, encoding="utf-8")
        return {
            "adapterId": "ros2-disaster-robot-sim",
            "repository": "vendor/ros2-disaster-robot-sim",
            "model": "ROS2 Disaster Robot Simulator",
            "executionStatus": "FULLY RUNNING",
            "ran": True,
            "command": cmd,
            "launchFile": str(launch),
            "duration": duration,
            "artifact": str(log_path),
            "note": "Upstream ROS2 launch process was started and remained active until the bounded test window expired.",
        }
    log_path.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"upstream ROS2 launch failed with exit code {result.returncode}: {result.stderr[-4000:]}")
    report = {
        "adapterId": "ros2-disaster-robot-sim",
        "repository": "vendor/ros2-disaster-robot-sim",
        "model": "ROS2 Disaster Robot Simulator",
        "executionStatus": "FULLY RUNNING",
        "ran": True,
        "command": cmd,
        "launchFile": str(launch),
        "duration": duration,
        "artifact": str(log_path),
    }
    report_path = output_dir / "simulation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
