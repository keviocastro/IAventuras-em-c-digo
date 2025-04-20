import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

from infraestructure.channel import ChannelRabbitMQ
from models.database import get_db
from machine_learning.train import treinar_modelo_churn
from pathlib import Path
import sys


def processar_atualizacao_modelo(ch, method, properties, body):
    """
    Processa uma solicitação de atualização do modelo de churn
    """
    try:
        # Decodificar a mensagem JSON
        mensagem = json.loads(body)
        print(f"Processando solicitação de atualização do modelo: {mensagem}")

        # Criar sessão com o banco
        db = next(get_db())

        # Treinar o modelo usando a função do módulo train.py
        resultado = treinar_modelo_churn(db)

        if resultado:
            print(f"Modelo treinado com sucesso: {resultado['modelo_path']}")
            print(f"Acurácia: {resultado['acuracia']:.4f}")
            print(f"Total de alunos: {resultado['total_alunos']}")
            print(f"Total de registros: {resultado['total_registros']}")
        else:
            print("Falha ao treinar o modelo")

        # Confirmar o processamento da mensagem
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Erro ao processar solicitação de atualização do modelo: {e}")
        # Em caso de erro, não confirmamos o processamento para que a mensagem seja reprocessada
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def iniciar_consumidor_modelo():
    """
    Inicia o consumidor de solicitações de atualização do modelo
    """
    channel_manager = ChannelRabbitMQ()
    channel = channel_manager.get_channel()

    # Garantir que a fila existe
    channel.queue_declare(queue="modelo.churn", durable=True)

    # Configurar o consumidor para processar uma mensagem por vez
    channel.basic_qos(prefetch_count=1)

    # Registrar o callback
    channel.basic_consume(
        queue="modelo.churn", on_message_callback=processar_atualizacao_modelo
    )

    print(
        "Aguardando solicitações de atualização do modelo. Para sair, pressione CTRL+C"
    )
    channel.start_consuming()


if __name__ == "__main__":
    iniciar_consumidor_modelo()
