import os
import pickle
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ModelLoader:
    def __init__(self, model_dir="src/models"):
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, "model.pkl")
        self.current_version_path = os.path.join(model_dir, "current_version.txt")
        self._model = None
        self._last_load_time = None
        self._reload_intervalo = 3600  # recarregar de 1 em 1h
        
    def get_model(self, force_reload=False):
        current_time = datetime.now()
        
        recarrega = (
            self._model is None or 
            force_reload or
            (self._last_load_time is not None and 
             (current_time - self._last_load_time).total_seconds() > self._reload_intervalo)
        )
        
        if recarrega:
            try:
                with open(self.model_path, 'rb') as f:
                    self._model = pickle.load(f)
                self._last_load_time = current_time
                if os.path.exists(self.current_version_path):
                    with open(self.current_version_path, 'r') as f:
                        version = f.read().strip()
                    logging.info(f"Modelo carregado: {version}")
                else:
                    logging.info(f"Modelo carregado: {self.model_path}")
            except Exception as e:
                logging.error(f"Erro ao carregar o modelo: {e}")
                return None
        
        return self._model
    
    def list_available_versions(self):
        try:
            versions = []
            for file in os.listdir(self.model_dir):
                if file.startswith("model_v") and file.endswith(".pkl"):
                    versions.append(file.replace(".pkl", ""))
            return sorted(versions)
        except Exception as e:
            logging.error(f"Erro ao listar versões do modelo: {e}")
            return []
    
    def load_specific_version(self, version):
        version_path = os.path.join(self.model_dir, f"{version}.pkl")
        
        if not os.path.exists(version_path):
            logging.error(f"Versão do modelo não encontrada: {version}")
            return None
        
        try:
            with open(version_path, 'rb') as f:
                model = pickle.load(f)
            logging.info(f"Versão específica do modelo carregada: {version}")
            return model
        except Exception as e:
            logging.error(f"Erro ao carregar versão específica do modelo: {e}")
            return None

model_loader = ModelLoader()

def get_current_model(force_reload=False):
    return model_loader.get_model(force_reload=force_reload)