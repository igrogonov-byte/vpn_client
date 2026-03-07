"""
Менеджер памяти для контроля утечек
"""
import gc
import logging
import tracemalloc
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class MemoryManager:
    """Менеджер памяти для отслеживания утечек"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._snapshots: List = []
        self._enabled = False
    
    def start_tracking(self):
        """Включить отслеживание памяти"""
        tracemalloc.start()
        self._enabled = True
        logger.info("Memory tracking enabled")
    
    def stop_tracking(self):
        """Выключить отслеживание"""
        if self._enabled:
            tracemalloc.stop()
            self._enabled = False
    
    def take_snapshot(self, label: str = "") -> None:
        """Сделать снимок памяти"""
        if not self._enabled:
            return
        
        snapshot = tracemalloc.take_snapshot()
        self._snapshots.append((label, snapshot))
        
        if label:
            logger.info(f"Memory snapshot taken: {label}")
    
    def get_top_allocations(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Получить топ аллокаций памяти"""
        if not self._enabled:
            return []
        
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')[:limit]
        
        return [
            (str(stat.traceback), stat.size)
            for stat in top_stats
        ]
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Получить текущее использование памяти"""
        if not self._enabled:
            return {}
        
        current, peak = tracemalloc.get_traced_memory()
        return {
            'current': current,
            'peak': peak,
            'current_mb': current / 1024 / 1024,
            'peak_mb': peak / 1024 / 1024
        }
    
    def force_gc(self) -> int:
        """Принудительная сборка мусора"""
        collected = gc.collect()
        logger.info(f"GC collected {collected} objects")
        return collected
    
    def compare_snapshots(self, index1: int = 0, index2: int = -1) -> List[str]:
        """Сравнить два снимка памяти"""
        if len(self._snapshots) < 2:
            return []
        
        _, snapshot1 = self._snapshots[index1]
        _, snapshot2 = self._snapshots[index2]
        
        diff = snapshot2.compare_to(snapshot1, 'lineno')
        
        return [
            f"{stat.traceback} | {stat.size_diff} bytes"
            for stat in diff[:20]
            if stat.size_diff != 0
        ]


# Глобальный экземпляр
memory_manager = MemoryManager()
