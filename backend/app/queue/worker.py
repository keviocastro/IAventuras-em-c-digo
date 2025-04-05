import logging
import time
import sys
import signal
import threading

from app.queue.rabbitmq import (
    RabbitMQClient,
    CHECKIN_QUEUE,
    REPORT_QUEUE,
    MODEL_UPDATE_QUEUE,
    CHURN_PROB_QUEUE
)
from app.queue.consumers import (
    process_checkin_message,
    process_report_message,
    process_model_update_message,
    process_churn_probabilities_message
)

# Configurar logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Controle de execução
running = True


def signal_handler(sig, frame):
    """
    Manipulador de sinais para encerrar o worker corretamente.
    """
    global running
    logger.info("Recebido sinal de encerramento, finalizando worker...")
    running = False


def start_consumer(queue_name, callback):
    """
    Inicia um consumidor em uma thread separada.
    
    Args:
        queue_name: Nome da fila para consumir
        callback: Função de callback para processar mensagens
    """
    client = RabbitMQClient()
    try:
        logger.info(f"Iniciando consumidor para a fila {queue_name}")
        client.consume_messages(queue_name, callback)
    except Exception as e:
        logger.error(f"Erro ao iniciar consumidor para {queue_name}: {e}")
    finally:
        if client:
            client.close()


def main():
    """
    Função principal do worker.
    """
    # Configurar manipulador de sinais
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Iniciando worker RabbitMQ...")
    
    # Iniciar cada consumidor em uma thread separada
    threads = []
    
    # Thread para processar checkins
    checkin_thread = threading.Thread(
        target=start_consumer, 
        args=(CHECKIN_QUEUE, process_checkin_message),
        daemon=True
    )
    threads.append(checkin_thread)
    
    # Thread para processar relatórios
    report_thread = threading.Thread(
        target=start_consumer, 
        args=(REPORT_QUEUE, process_report_message),
        daemon=True
    )
    threads.append(report_thread)
    
    # Thread para processar atualizações do modelo
    model_thread = threading.Thread(
        target=start_consumer, 
        args=(MODEL_UPDATE_QUEUE, process_model_update_message),
        daemon=True
    )
    threads.append(model_thread)
    
    # Thread para processar cálculo de probabilidades de churn
    churn_prob_thread = threading.Thread(
        target=start_consumer, 
        args=(CHURN_PROB_QUEUE, process_churn_probabilities_message),
        daemon=True
    )
    threads.append(churn_prob_thread)
    
    # Iniciar todas as threads
    for thread in threads:
        thread.start()
    
    # Manter o programa em execução
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupção de teclado recebida, encerrando...")
    finally:
        logger.info("Worker encerrado")


if __name__ == "__main__":
    main() 