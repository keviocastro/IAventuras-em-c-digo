import multiprocessing
import os
import sys

from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from consumers.checkin_consumer import iniciar_consumidor_checkins
from consumers.relatorio_consumer import iniciar_consumidor_relatorios
from consumers.modelo_churn_consumer import iniciar_consumidor_modelo
from consumers.batch_checkin_consumer import (
    iniciar_consumidor_checkins_em_lote,
)


def iniciar_todos_consumidores():
    """
    Inicia todos os consumidores em processos separados
    """
    processos = []

    # Iniciar consumidor de check-ins
    p1 = multiprocessing.Process(target=iniciar_consumidor_checkins)
    p1.start()
    processos.append(p1)

    # Iniciar consumidor de relatórios
    p2 = multiprocessing.Process(target=iniciar_consumidor_relatorios)
    p2.start()
    processos.append(p2)

    # Iniciar consumidor de modelo de churn
    p3 = multiprocessing.Process(target=iniciar_consumidor_modelo)
    p3.start()
    processos.append(p3)

    # Iniciar consumidor de check-ins em lote
    p4 = multiprocessing.Process(target=iniciar_consumidor_checkins_em_lote)
    p4.start()
    processos.append(p4)

    # Aguardar finalização dos processos (que na prática não deve ocorrer)
    for p in processos:
        p.join()


if __name__ == "__main__":
    print("Iniciando todos os consumidores RabbitMQ...")
    iniciar_todos_consumidores()
