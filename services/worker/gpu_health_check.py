#!/usr/bin/env python3
"""GPU Worker Health Check - verifies GPU availability and configuration.

This script checks:
- CUDA availability
- GPU name and VRAM
- CUDA version
- Model cache directory
- Object storage connectivity
- Required dependencies
"""
from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Any

def check_cuda_availability() -> dict[str, Any]:
    """Check CUDA availability and GPU information."""
    result = {
        "cudaAvailable": False,
        "gpuName": None,
        "vramTotal": None,
        "vramFree": None,
        "cudaVersion": None,
        "error": None
    }
    
    try:
        import torch
        result["cudaAvailable"] = torch.cuda.is_available()
        
        if result["cudaAvailable"]:
            result["gpuName"] = torch.cuda.get_device_name(0)
            result["vramTotal"] = f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB"
            result["vramFree"] = f"{torch.cuda.memory_allocated(0) / 1024**3:.2f} GB used"
            result["cudaVersion"] = torch.version.cuda
        else:
            result["error"] = "CUDA not available via PyTorch"
            
    except ImportError:
        result["error"] = "PyTorch not installed"
    except Exception as e:
        result["error"] = f"CUDA check failed: {str(e)}"
    
    return result


def check_onnxruntime_gpu() -> dict[str, Any]:
    """Check ONNX Runtime GPU availability."""
    result = {
        "onnxRuntimeGpuAvailable": False,
        "providers": [],
        "error": None
    }
    
    try:
        import onnxruntime as ort
        result["providers"] = ort.get_available_providers()
        result["onnxRuntimeGpuAvailable"] = "CUDAExecutionProvider" in result["providers"]
        
        if not result["onnxRuntimeGpuAvailable"]:
            result["error"] = "CUDAExecutionProvider not available in ONNX Runtime"
            
    except ImportError:
        result["error"] = "ONNX Runtime not installed"
    except Exception as e:
        result["error"] = f"ONNX Runtime check failed: {str(e)}"
    
    return result


def check_model_cache() -> dict[str, Any]:
    """Check model cache directory."""
    model_cache_dir = Path(os.environ.get("MODEL_CACHE_DIR", "/models"))
    
    result = {
        "modelCacheDir": str(model_cache_dir),
        "exists": model_cache_dir.exists(),
        "writable": False,
        "diskSpace": None,
        "cachedModels": [],
        "error": None
    }
    
    try:
        if result["exists"]:
            result["writable"] = os.access(model_cache_dir, os.W_OK)
            
            # Get disk space
            stat = os.statvfs(model_cache_dir) if hasattr(os, 'statvfs') else None
            if stat:
                result["diskSpace"] = f"{stat.f_bavail * stat.f_frsize / 1024**3:.2f} GB free"
            
            # List cached models
            if model_cache_dir.exists():
                result["cachedModels"] = [f.name for f in model_cache_dir.iterdir() if f.is_file()]
        else:
            result["error"] = f"Model cache directory does not exist: {model_cache_dir}"
            
    except Exception as e:
        result["error"] = f"Model cache check failed: {str(e)}"
    
    return result


def check_object_storage() -> dict[str, Any]:
    """Check object storage connectivity."""
    result = {
        "objectStorageConfigured": False,
        "endpoint": os.environ.get("OBJECT_STORAGE_ENDPOINT"),
        "bucket": os.environ.get("OBJECT_STORAGE_BUCKET"),
        "connectivity": False,
        "error": None
    }
    
    if result["endpoint"] and result["bucket"]:
        result["objectStorageConfigured"] = True
        
        try:
            import boto3
            s3_client = boto3.client(
                's3',
                endpoint_url=result["endpoint"],
                aws_access_key_id=os.environ.get("OBJECT_STORAGE_ACCESS_KEY"),
                aws_secret_access_key=os.environ.get("OBJECT_STORAGE_SECRET_KEY")
            )
            
            # Test connectivity by listing buckets
            s3_client.list_buckets()
            result["connectivity"] = True
            
        except ImportError:
            result["error"] = "boto3 not installed"
        except Exception as e:
            result["error"] = f"Object storage connectivity failed: {str(e)}"
    else:
        result["error"] = "Object storage not configured (missing endpoint or bucket)"
    
    return result


def check_dependencies() -> dict[str, Any]:
    """Check required dependencies."""
    required_packages = [
        "torch",
        "ultralytics", 
        "onnxruntime",
        "opencv-python",
        "numpy",
        "redis",
        "boto3",
        "huggingface_hub"
    ]
    
    result = {
        "dependencies": {},
        "allInstalled": True
    }
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            result["dependencies"][package] = "installed"
        except ImportError:
            result["dependencies"][package] = "missing"
            result["allInstalled"] = False
    
    return result


def check_redis_connectivity() -> dict[str, Any]:
    """Check Redis connectivity."""
    result = {
        "redisConfigured": False,
        "redisUrl": os.environ.get("REDIS_URL"),
        "connectivity": False,
        "error": None
    }
    
    if result["redisUrl"]:
        result["redisConfigured"] = True
        
        try:
            import redis
            client = redis.from_url(result["redisUrl"], decode_responses=True)
            client.ping()
            result["connectivity"] = True
            
        except ImportError:
            result["error"] = "redis not installed"
        except Exception as e:
            result["error"] = f"Redis connectivity failed: {str(e)}"
    else:
        result["error"] = "Redis URL not configured"
    
    return result


def main_health_check() -> dict[str, Any]:
    """Run comprehensive health check."""
    print("="*60)
    print("GPU Worker Health Check")
    print("="*60)
    
    health_report = {
        "timestamp": "2026-09-13T00:00:00Z",
        "workerStatus": "UNKNOWN",
        "gpuStatus": "UNKNOWN",
        "overallHealth": "UNKNOWN",
        "checks": {}
    }
    
    # Run all checks
    print("\n[1/6] Checking CUDA availability...")
    cuda_check = check_cuda_availability()
    health_report["checks"]["cuda"] = cuda_check
    print(f"  CUDA Available: {cuda_check['cudaAvailable']}")
    if cuda_check['cudaAvailable']:
        print(f"  GPU: {cuda_check['gpuName']}")
        print(f"  VRAM: {cuda_check['vramTotal']}")
    else:
        print(f"  Error: {cuda_check['error']}")
    
    print("\n[2/6] Checking ONNX Runtime GPU...")
    onnx_check = check_onnxruntime_gpu()
    health_report["checks"]["onnxRuntime"] = onnx_check
    print(f"  ONNX GPU Available: {onnx_check['onnxRuntimeGpuAvailable']}")
    print(f"  Providers: {onnx_check['providers']}")
    
    print("\n[3/6] Checking model cache...")
    cache_check = check_model_cache()
    health_report["checks"]["modelCache"] = cache_check
    print(f"  Cache Dir: {cache_check['modelCacheDir']}")
    print(f"  Exists: {cache_check['exists']}")
    print(f"  Writable: {cache_check['writable']}")
    print(f"  Cached Models: {len(cache_check['cachedModels'])}")
    
    print("\n[4/6] Checking object storage...")
    storage_check = check_object_storage()
    health_report["checks"]["objectStorage"] = storage_check
    print(f"  Configured: {storage_check['objectStorageConfigured']}")
    print(f"  Connectivity: {storage_check['connectivity']}")
    
    print("\n[5/6] Checking dependencies...")
    dep_check = check_dependencies()
    health_report["checks"]["dependencies"] = dep_check
    print(f"  All Installed: {dep_check['allInstalled']}")
    for pkg, status in dep_check['dependencies'].items():
        print(f"  {pkg}: {status}")
    
    print("\n[6/6] Checking Redis connectivity...")
    redis_check = check_redis_connectivity()
    health_report["checks"]["redis"] = redis_check
    print(f"  Configured: {redis_check['redisConfigured']}")
    print(f"  Connectivity: {redis_check['connectivity']}")
    
    # Determine overall health
    gpu_available = cuda_check['cudaAvailable'] or onnx_check['onnxRuntimeGpuAvailable']
    storage_ready = storage_check['objectStorageConfigured'] and storage_check['connectivity']
    deps_ready = dep_check['allInstalled']
    redis_ready = redis_check['redisConfigured'] and redis_check['connectivity']
    
    if gpu_available and storage_ready and deps_ready and redis_ready:
        health_report["workerStatus"] = "READY"
        health_report["gpuStatus"] = "GPU_WORKER_AVAILABLE"
        health_report["overallHealth"] = "HEALTHY"
    elif not gpu_available:
        health_report["workerStatus"] = "GPU_UNAVAILABLE"
        health_report["gpuStatus"] = "GPU_WORKER_UNAVAILABLE"
        health_report["overallHealth"] = "UNHEALTHY"
    else:
        health_report["workerStatus"] = "PARTIAL"
        health_report["gpuStatus"] = "GPU_WORKER_PARTIAL"
        health_report["overallHealth"] = "DEGRADED"
    
    print("\n" + "="*60)
    print("Health Check Summary")
    print("="*60)
    print(f"Worker Status: {health_report['workerStatus']}")
    print(f"GPU Status: {health_report['gpuStatus']}")
    print(f"Overall Health: {health_report['overallHealth']}")
    
    if health_report['gpuStatus'] == "GPU_WORKER_UNAVAILABLE":
        print("\n[CRITICAL] GPU WORKER UNAVAILABLE - Heavy models cannot run on this machine")
        print("This worker should only be used for lightweight tasks.")
    
    return health_report


if __name__ == "__main__":
    health_report = main_health_check()
    
    # Save health report
    output_path = Path("/tmp/gpu_worker_health.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(health_report, f, indent=2)
    
    print(f"\nHealth report saved to: {output_path}")
    
    # Exit with appropriate code
    sys.exit(0 if health_report['overallHealth'] == "HEALTHY" else 1)