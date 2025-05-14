"""
Resource monitoring for exo nodes.
Tracks and reports RAM and GPU utilization.
"""

import os
import sys
import time
import platform
import psutil
from typing import Dict, Optional, Tuple, List
import asyncio
from exo import DEBUG

class ResourceMonitor:
    """
    Monitors system resources including RAM and GPU utilization.
    Provides methods to collect resource usage and format it for display.
    """
    
    def __init__(self):
        self.last_update_time = 0
        self.update_interval = 2.0  # Update at most every 2 seconds
        self.is_tty = sys.stdout.isatty()
        self.system = platform.system()
        
        # Initialize GPU monitoring based on platform and available libraries
        self.gpu_monitor = self._initialize_gpu_monitor()
        
    def _initialize_gpu_monitor(self):
        """Initialize the appropriate GPU monitor based on the system and available libraries."""
        if self.system == "Darwin":  # macOS
            return AppleSiliconGPUMonitor() if platform.machine() == "arm64" else IntelGPUMonitor()
        elif self.system == "Linux":
            # Try NVIDIA first, then AMD
            try:
                import pynvml
                return NvidiaGPUMonitor()
            except (ImportError, ModuleNotFoundError):
                try:
                    import pyamdgpuinfo
                    return AMDGPUMonitor()
                except (ImportError, ModuleNotFoundError):
                    return DummyGPUMonitor()
        elif self.system == "Windows":
            # Try NVIDIA first, then AMD
            try:
                import pynvml
                return NvidiaGPUMonitor()
            except (ImportError, ModuleNotFoundError):
                try:
                    from pyrsmi import rocml
                    return AMDGPUMonitor()
                except (ImportError, ModuleNotFoundError):
                    return DummyGPUMonitor()
        return DummyGPUMonitor()
    
    async def get_resource_usage(self) -> Dict:
        """
        Get current resource usage including RAM and GPU.
        
        Returns:
            Dict containing resource usage information
        """
        current_time = time.time()
        
        # Only update at most every update_interval seconds
        if current_time - self.last_update_time < self.update_interval:
            return {}
            
        self.last_update_time = current_time
        
        # Get RAM usage
        ram_usage = self._get_ram_usage()
        
        # Get GPU usage
        gpu_usage = await self.gpu_monitor.get_gpu_usage()
        
        return {
            "timestamp": current_time,
            "ram": ram_usage,
            "gpu": gpu_usage
        }
    
    def _get_ram_usage(self) -> Dict:
        """Get RAM usage information."""
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent
        }
    
    def format_resource_usage(self, usage: Dict, node_id: str, is_local: bool = False) -> str:
        """
        Format resource usage for display in the terminal.
        
        Args:
            usage: Resource usage dictionary
            node_id: ID of the node
            is_local: Whether this is the local node
            
        Returns:
            Formatted string for display
        """
        if not usage or "ram" not in usage or "gpu" not in usage:
            return f"Node {node_id}: No resource data available"
        
        # Format RAM usage
        ram = usage["ram"]
        ram_str = f"RAM: {ram['used'] / (1024**3):.1f}GB/{ram['total'] / (1024**3):.1f}GB ({ram['percent']}%)"
        
        # Format GPU usage
        gpu = usage["gpu"]
        if gpu.get("available", False):
            gpu_str = f"GPU: {gpu.get('used_memory', 0) / (1024**3):.1f}GB/{gpu.get('total_memory', 0) / (1024**3):.1f}GB ({gpu.get('memory_percent', 0)}%)"
            if "utilization" in gpu:
                gpu_str += f", Util: {gpu['utilization']}%"
        else:
            gpu_str = "GPU: Not available"
        
        # Add indicator for local node
        prefix = "* " if is_local else "  "
        
        return f"{prefix}Node {node_id}: {ram_str} | {gpu_str}"


class GPUMonitorBase:
    """Base class for GPU monitors."""
    
    async def get_gpu_usage(self) -> Dict:
        """Get GPU usage information."""
        return {"available": False}


class DummyGPUMonitor(GPUMonitorBase):
    """Dummy GPU monitor for systems without GPU monitoring support."""
    pass


class NvidiaGPUMonitor(GPUMonitorBase):
    """Monitor for NVIDIA GPUs using pynvml."""
    
    async def get_gpu_usage(self) -> Dict:
        try:
            import pynvml
            pynvml.nvmlInit()
            
            # Get the first GPU
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # Get memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            # Get utilization info
            util_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
            
            result = {
                "available": True,
                "name": pynvml.nvmlDeviceGetName(handle),
                "total_memory": mem_info.total,
                "used_memory": mem_info.used,
                "free_memory": mem_info.free,
                "memory_percent": (mem_info.used / mem_info.total) * 100,
                "utilization": util_info.gpu
            }
            
            pynvml.nvmlShutdown()
            return result
        except Exception as e:
            if DEBUG >= 2:
                print(f"Error getting NVIDIA GPU info: {e}")
            return {"available": False}


class AMDGPUMonitor(GPUMonitorBase):
    """Monitor for AMD GPUs."""
    
    async def get_gpu_usage(self) -> Dict:
        if platform.system() == "Linux":
            return await self._get_linux_amd_gpu_usage()
        elif platform.system() == "Windows":
            return await self._get_windows_amd_gpu_usage()
        return {"available": False}
    
    async def _get_linux_amd_gpu_usage(self) -> Dict:
        try:
            import pyamdgpuinfo
            
            gpu = pyamdgpuinfo.get_gpu(0)
            vram_info = gpu.memory_info
            
            return {
                "available": True,
                "name": gpu.name,
                "total_memory": vram_info["vram_size"],
                "used_memory": vram_info["vram_used"],
                "free_memory": vram_info["vram_size"] - vram_info["vram_used"],
                "memory_percent": (vram_info["vram_used"] / vram_info["vram_size"]) * 100
            }
        except Exception as e:
            if DEBUG >= 2:
                print(f"Error getting AMD GPU info on Linux: {e}")
            return {"available": False}
    
    async def _get_windows_amd_gpu_usage(self) -> Dict:
        try:
            from pyrsmi import rocml
            
            rocml.smi_initialize()
            
            gpu_name = rocml.smi_get_device_name(0)
            total_memory = rocml.smi_get_device_memory_total(0)
            used_memory = rocml.smi_get_device_memory_usage(0)
            
            result = {
                "available": True,
                "name": gpu_name,
                "total_memory": total_memory,
                "used_memory": used_memory,
                "free_memory": total_memory - used_memory,
                "memory_percent": (used_memory / total_memory) * 100 if total_memory > 0 else 0
            }
            
            rocml.smi_shutdown()
            return result
        except Exception as e:
            if DEBUG >= 2:
                print(f"Error getting AMD GPU info on Windows: {e}")
            return {"available": False}


class AppleSiliconGPUMonitor(GPUMonitorBase):
    """Monitor for Apple Silicon GPUs."""
    
    async def get_gpu_usage(self) -> Dict:
        try:
            # Use subprocess to get GPU memory info from sysctl
            proc = await asyncio.create_subprocess_exec(
                "sysctl", "-n", "hw.memsize", "hw.physmem",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            
            # Try to get Metal GPU memory allocation
            metal_proc = await asyncio.create_subprocess_exec(
                "sysctl", "-n", "iogpu.wired_limit_mb", "iogpu.wired_size_mb",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            metal_stdout, _ = await metal_proc.communicate()
            
            if metal_proc.returncode == 0:
                values = metal_stdout.decode().strip().split("\n")
                if len(values) >= 2:
                    limit_mb = int(values[0])
                    used_mb = int(values[1])
                    
                    return {
                        "available": True,
                        "name": "Apple Silicon GPU",
                        "total_memory": limit_mb * 1024 * 1024,
                        "used_memory": used_mb * 1024 * 1024,
                        "free_memory": (limit_mb - used_mb) * 1024 * 1024,
                        "memory_percent": (used_mb / limit_mb) * 100 if limit_mb > 0 else 0
                    }
            
            # Fallback: estimate GPU memory as a portion of system memory
            if proc.returncode == 0:
                values = stdout.decode().strip().split("\n")
                if len(values) >= 1:
                    total_memory = int(values[0])
                    # Estimate GPU memory as 30% of system memory for Apple Silicon
                    estimated_gpu_memory = total_memory * 0.3
                    
                    # Try to get actual GPU usage from activity monitor data
                    # This is a rough approximation
                    gpu_usage_percent = 0
                    try:
                        # Check if MLX is using the GPU
                        import mlx.core as mx
                        if mx.default_device().name == "gpu":
                            gpu_usage_percent = 30  # Rough estimate when MLX is active
                    except:
                        pass
                    
                    return {
                        "available": True,
                        "name": "Apple Silicon GPU (estimated)",
                        "total_memory": estimated_gpu_memory,
                        "used_memory": estimated_gpu_memory * (gpu_usage_percent / 100),
                        "free_memory": estimated_gpu_memory * (1 - gpu_usage_percent / 100),
                        "memory_percent": gpu_usage_percent,
                        "utilization": gpu_usage_percent
                    }
            
            return {"available": False}
        except Exception as e:
            if DEBUG >= 2:
                print(f"Error getting Apple Silicon GPU info: {e}")
            return {"available": False}


class IntelGPUMonitor(GPUMonitorBase):
    """Monitor for Intel integrated GPUs."""
    
    async def get_gpu_usage(self) -> Dict:
        # Intel GPUs on Mac don't have good monitoring tools
        # Return a basic structure with limited info
        return {"available": False}


# Singleton instance
resource_monitor = ResourceMonitor()
