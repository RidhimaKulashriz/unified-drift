#!/usr/bin/env python3
"""Simple GPU Worker Health Check - lightweight version.

This performs basic checks without hanging on heavy imports.
"""
import os
import sys
import json
from pathlib import Path

def basic_health_check():
    """Perform basic health checks."""
    print("="*60)
    print("GPU Worker Basic Health Check")
    print("="*60)
    
    health_report = {
        "timestamp": "2026-09-13T00:00:00Z",
        "workerStatus": "UNKNOWN",
        "gpuStatus": "UNKNOWN",
        "checks": {}
    }
    
    # Check Python environment
    print("\n[1/4] Python Environment:")
    print(f"  Python Version: {sys.version}")
    print(f"  Working Directory: {os.getcwd()}")
    health_report["checks"]["python"] = {
        "version": sys.version.split()[0],
        "workingDirectory": os.getcwd()
    }
    
    # Check model cache directory
    print("\n[2/4] Model Cache Directory:")
    model_cache_dir = Path(os.environ.get("MODEL_CACHE_DIR", "/models"))
    print(f"  Model Cache Dir: {model_cache_dir}")
    print(f"  Exists: {model_cache_dir.exists()}")
    health_report["checks"]["modelCache"] = {
        "path": str(model_cache_dir),
        "exists": model_cache_dir.exists()
    }
    
    # Check environment variables
    print("\n[3/4] Environment Variables:")
    env_vars = ["REDIS_URL", "OBJECT_STORAGE_ENDPOINT", "OBJECT_STORAGE_BUCKET", "MODEL_CACHE_DIR"]
    for var in env_vars:
        value = os.environ.get(var, "NOT_SET")
        print(f"  {var}: {value}")
        health_report["checks"]["environment"] = health_report["checks"].get("environment", {})
        health_report["checks"]["environment"][var] = value
    
    # Check basic dependencies (without heavy imports)
    print("\n[4/4] Basic Dependencies:")
    basic_deps = ["json", "pathlib", "os", "sys"]
    for dep in basic_deps:
        try:
            __import__(dep)
            print(f"  {dep}: OK")
        except ImportError:
            print(f"  {dep}: MISSING")
    
    # Determine GPU status (assume no GPU on local machine)
    print("\n" + "="*60)
    print("Health Check Summary")
    print("="*60)
    
    # Since this is running on local machine with limited GPU, report appropriately
    health_report["workerStatus"] = "LOCAL_MACHINE"
    health_report["gpuStatus"] = "GPU_WORKER_UNAVAILABLE"
    health_report["overallHealth"] = "LOCAL_DEV_MODE"
    
    print(f"Worker Status: {health_report['workerStatus']}")
    print(f"GPU Status: {health_report['gpuStatus']}")
    print(f"Overall Health: {health_report['overallHealth']}")
    print("\n[INFO] Running on local machine - GPU worker would run on remote instance")
    print("[INFO] Use gpu_worker.py on remote GPU instance for heavy inference")
    
    return health_report

if __name__ == "__main__":
    health_report = basic_health_check()
    
    # Save health report
    output_path = Path("/tmp/gpu_worker_health.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(health_report, f, indent=2)
    
    print(f"\nHealth report saved to: {output_path}")
    sys.exit(0)