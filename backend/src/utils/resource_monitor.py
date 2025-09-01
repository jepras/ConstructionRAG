"""Resource monitoring utilities for Beam pipeline."""

import psutil
import asyncio
from datetime import datetime
from typing import Dict, Any


class ResourceMonitor:
    """Monitor CPU and RAM usage during pipeline execution."""
    
    def __init__(self, log_interval: int = 10):
        """
        Initialize resource monitor.
        
        Args:
            log_interval: Seconds between resource logs
        """
        self.log_interval = log_interval
        self.monitoring = False
        self.peak_cpu = 0
        self.peak_ram = 0
        
    def get_current_usage(self) -> Dict[str, Any]:
        """Get current resource usage snapshot."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Track peaks
        self.peak_cpu = max(self.peak_cpu, cpu_percent)
        self.peak_ram = max(self.peak_ram, memory.percent)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count(),
                "per_core": psutil.cpu_percent(interval=1, percpu=True),
            },
            "memory": {
                "percent": memory.percent,
                "used_gb": round(memory.used / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
            },
            "process": {
                "cpu_percent": psutil.Process().cpu_percent(),
                "memory_mb": round(psutil.Process().memory_info().rss / (1024**2), 2),
            },
            "peaks": {
                "cpu": self.peak_cpu,
                "ram": self.peak_ram,
            }
        }
    
    def log_usage(self, context: str = ""):
        """Log current resource usage."""
        usage = self.get_current_usage()
        
        print(f"\n📊 RESOURCE USAGE {context}:")
        print(f"  ⚡ CPU: {usage['cpu']['percent']:.1f}% (Peak: {usage['peaks']['cpu']:.1f}%)")
        print(f"  💾 RAM: {usage['memory']['percent']:.1f}% - {usage['memory']['used_gb']:.1f}GB/{usage['memory']['total_gb']:.1f}GB (Peak: {usage['peaks']['ram']:.1f}%)")
        print(f"  📦 Process: CPU {usage['process']['cpu_percent']:.1f}%, RAM {usage['process']['memory_mb']:.0f}MB")
        
        # Warn if resources are constrained
        if usage['cpu']['percent'] > 90:
            print("  ⚠️ CPU is at >90% - possible bottleneck!")
        if usage['memory']['percent'] > 85:
            print("  ⚠️ RAM is at >85% - possible memory pressure!")
            
        return usage
    
    async def start_monitoring(self):
        """Start background resource monitoring."""
        self.monitoring = True
        while self.monitoring:
            self.log_usage("(Background Monitor)")
            await asyncio.sleep(self.log_interval)
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self.monitoring = False
        
    def get_summary(self) -> Dict[str, Any]:
        """Get resource usage summary."""
        return {
            "peak_cpu_percent": self.peak_cpu,
            "peak_ram_percent": self.peak_ram,
            "final_usage": self.get_current_usage(),
        }


# Singleton instance for easy access
_monitor = None

def get_monitor() -> ResourceMonitor:
    """Get or create the resource monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ResourceMonitor()
    return _monitor


def log_resources(context: str = ""):
    """Quick function to log resources."""
    monitor = get_monitor()
    return monitor.log_usage(context)


async def monitor_step(step_name: str, step_function, *args, **kwargs):
    """Monitor resources during a specific step."""
    monitor = get_monitor()
    
    # Log before
    monitor.log_usage(f"Before {step_name}")
    
    # Execute step
    result = await step_function(*args, **kwargs)
    
    # Log after
    monitor.log_usage(f"After {step_name}")
    
    return result