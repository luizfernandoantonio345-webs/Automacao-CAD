import json
import os
from typing import Dict, Optional, Any

class RefineryService:
    """
    Serviço para gerenciar dados de refinarias e suas configurações
    """
    
    _instance: Optional['RefineryService'] = None
    _refineries_data: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_data()
        return cls._instance
    
    @classmethod
    def _load_data(cls):
        """Carrega dados de refinarias do arquivo JSON"""
        try:
            # Procura o arquivo na estrutura do backend
            base_path = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(
                base_path, '../../backend/database/refineries_data.json'
            )
            
            # Tente caminhos alternativos
            if not os.path.exists(json_path):
                json_path = os.path.join(
                    base_path, '../backend/database/refineries_data.json'
                )
            
            if not os.path.exists(json_path):
                json_path = os.path.join(
                    base_path, 'backend/database/refineries_data.json'
                )
            
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    cls._refineries_data = json.load(f)
            else:
                # Dados padrão se arquivo não encontrado
                cls._instance._set_default_data()
                
        except Exception as e:
            print(f"Erro ao carregar dados de refinarias: {e}")
            cls._instance._set_default_data()
    
    @staticmethod
    def _set_default_data():
        """Define dados padrão em caso de falha na leitura do arquivo"""
        RefineryService._refineries_data = {
            "REGAP": {
                "name": "REGAP Gabriel Passos",
                "location": "Betim, MG",
                "norms": ["N-0058", "N-0076", "N-0115", "ASME B31.3", "N-0013"],
                "material_database": "SINCOR_REGAP_V2.3.5",
                "default_pressure_class": "150#",
                "clash_detection_tolerance_mm": 5,
                "units": "SI (mm, bar)",
                "cad_version": "AutoCAD 2022+",
                "max_drawing_size_mb": 500
            },
            "REPLAN": {
                "name": "REPLAN Gabriel Passos",
                "location": "Paulínia, SP",
                "norms": ["N-0058", "N-0076", "N-0115", "ASME B31.3", "N-0013"],
                "material_database": "SINCOR_REPLAN_V1.9.0",
                "default_pressure_class": "300#",
                "clash_detection_tolerance_mm": 3,
                "units": "SI (mm, bar)",
                "cad_version": "AutoCAD 2022+",
                "max_drawing_size_mb": 500
            }
        }
    
    def get_all_refineries(self) -> Dict[str, Dict[str, Any]]:
        """Retorna todas as refinarias cadastradas"""
        return self._refineries_data
    
    def get_refinery(self, refinery_id: str) -> Optional[Dict[str, Any]]:
        """Retorna configuração de uma refinaria específica"""
        return self._refineries_data.get(refinery_id.upper())
    
    def get_refinery_norms(self, refinery_id: str) -> list:
        """Retorna normas aplicáveis a uma refinaria"""
        refinery = self.get_refinery(refinery_id)
        return refinery.get('norms', []) if refinery else []
    
    def get_material_database(self, refinery_id: str) -> Optional[str]:
        """Retorna o banco de dados de materiais de uma refinaria"""
        refinery = self.get_refinery(refinery_id)
        return refinery.get('material_database') if refinery else None
    
    def validate_refinery(self, refinery_id: str) -> bool:
        """Valida se uma refinaria existe"""
        return refinery_id.upper() in self._refineries_data
    
    def list_refinery_ids(self) -> list:
        """Retorna lista de IDs de refinarias disponíveis"""
        return list(self._refineries_data.keys())
