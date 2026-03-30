#!/usr/bin/env python3
# ====================================================================
# gpu_support.py - FASE 4: GPU Support para AI Tasks
# ====================================================================

import os
import logging
from typing import Optional, Dict, Any

try:
    import torch
except ImportError:
    torch = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

class GPUManager:
    """✓ FASE 4: Gerenciador de GPU para aceleração AI."""
    
    def __init__(self):
        if torch is None:
            self.cuda_available = False
            self.device_count = 0
            logger.warning("PyTorch não instalado - GPU support desativado")
            return
        self.cuda_available = torch.cuda.is_available()
        self.device_count = torch.cuda.device_count() if self.cuda_available else 0
        
        if self.cuda_available:
            logger.info(f"GPU disponível: {self.device_count} dispositivo(s)")
            for i in range(self.device_count):
                props = torch.cuda.get_device_properties(i)
                logger.info(f"GPU {i}: {props.name} - {props.total_memory / 1024**3:.1f}GB")
        else:
            logger.warning("CUDA não disponível - usando CPU")
    
    def get_device(self, device_id: Optional[int] = None):
        """Obter device GPU ou CPU."""
        if torch is None:
            return None
        if self.cuda_available and device_id is not None and device_id < self.device_count:
            return torch.device(f"cuda:{device_id}")
        elif self.cuda_available:
            return torch.device("cuda:0")
        else:
            return torch.device("cpu")
    
    def get_memory_info(self, device_id: int = 0) -> Dict[str, float]:
        """Informações de memória GPU."""
        if not self.cuda_available or torch is None:
            return {"error": "CUDA não disponível"}
        
        try:
            allocated = torch.cuda.memory_allocated(device_id) / 1024**3
            reserved = torch.cuda.memory_reserved(device_id) / 1024**3
            total = torch.cuda.get_device_properties(device_id).total_memory / 1024**3
            
            return {
                "allocated_gb": allocated,
                "reserved_gb": reserved,
                "total_gb": total,
                "free_gb": total - allocated,
                "utilization_percent": (allocated / total) * 100
            }
        except Exception as e:
            return {"error": str(e)}
    
    def optimize_for_gpu(self, model):
        """Otimizar modelo para GPU."""
        if not self.cuda_available:
            return model
        
        device = self.get_device()
        
        # Mover para GPU
        model = model.to(device)
        
        # Habilitar autocast para mixed precision
        if hasattr(torch.cuda, 'amp') and torch.cuda.is_available():
            model = torch.cuda.amp.autocast()(model)
        
        return model
    
    def clear_cache(self):
        """Limpar cache GPU."""
        if self.cuda_available and torch is not None:
            torch.cuda.empty_cache()
            logger.info("GPU cache limpo")

# ✓ Instância global
_gpu_manager = None

def get_gpu_manager() -> GPUManager:
    """Obter gerenciador GPU."""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUManager()
    return _gpu_manager

# ✓ Decorator para tasks GPU
def gpu_task(device_id: Optional[int] = None):
    """Decorator para tasks que usam GPU."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            gpu = get_gpu_manager()
            device = gpu.get_device(device_id)
            
            # Adicionar device aos kwargs
            kwargs['device'] = device
            
            # Log GPU info
            if gpu.cuda_available:
                mem_info = gpu.get_memory_info(device_id or 0)
                logger.info(f"GPU Task {func.__name__}: Device {device}, Memory {mem_info.get('utilization_percent', 0):.1f}%")
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Limpar cache após task
                gpu.clear_cache()
        
        return wrapper
    return decorator

# ✓ Função para verificar se deve usar GPU
def should_use_gpu(task_type: str, payload: Dict[str, Any]) -> bool:
    """Decidir se usar GPU baseado no tipo de task e payload."""
    gpu = get_gpu_manager()
    
    if not gpu.cuda_available:
        return False
    
    # AI CAD sempre usa GPU se disponível
    if task_type == "ai_cad":
        return True
    
    # Outros tipos podem usar baseado em tamanho
    if task_type == "excel_batch":
        # Se muitos arquivos, usar GPU
        files = payload.get("files", [])
        return len(files) > 10
    
    return False