#!/usr/bin/env python

"""
Script para iniciar o worker RabbitMQ.
Este script inicia o processamento das filas RabbitMQ em segundo plano.
"""

import os
import sys
import logging

# Ajustar o path para importar os módulos do app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.queue.worker import main

if __name__ == "__main__":
    try:
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        logging.info("Iniciando worker RabbitMQ...")
        
        # Iniciar worker
        main()
    except KeyboardInterrupt:
        logging.info("Worker encerrado pelo usuário")
    except Exception as e:
        logging.error(f"Erro ao iniciar worker: {e}")
        sys.exit(1) 