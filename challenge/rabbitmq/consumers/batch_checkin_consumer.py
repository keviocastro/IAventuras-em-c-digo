import json
import sys
import logging
from datetime import datetime
from pathlib import Path

# Configuração de paths para importação
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

from infraestructure.channel import ChannelRabbitMQ
from models.database import get_db
from models.entities import CheckIn, Aluno

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def processar_entrada(db, aluno_id, data):
    """
    Registra um novo check-in para o aluno

    Args:
        db: Sessão do banco de dados
        aluno_id: ID do aluno
        data: Data/hora da entrada

    Returns:
        bool: True se o check-in foi registrado com sucesso
    """
    try:
        novo_checkin = CheckIn(aluno_id=aluno_id, data_entrada=data)
        db.add(novo_checkin)
        db.commit()
        logger.info(f"Check-in em lote registrado para aluno {aluno_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(
            f"Erro ao registrar check-in para aluno {aluno_id}: {str(e)}"
        )
        raise


def processar_saida(db, aluno_id, data):
    """
    Registra a saída para o último check-in aberto do aluno

    Args:
        db: Sessão do banco de dados
        aluno_id: ID do aluno
        data: Data/hora da saída

    Returns:
        bool: True se o check-out foi registrado com sucesso, False se não havia check-in aberto
    """
    try:
        ultimo_checkin = (
            db.query(CheckIn)
            .filter(
                CheckIn.aluno_id == aluno_id, CheckIn.duracao_treino.is_(None)
            )
            .order_by(CheckIn.data_entrada.desc())
            .first()
        )

        if not ultimo_checkin:
            logger.warning(
                f"Nenhum check-in aberto encontrado para o aluno {aluno_id}"
            )
            return False

        # Calcular a duração do treino em minutos
        duracao = int(
            (data - ultimo_checkin.data_entrada).total_seconds() / 60
        )
        ultimo_checkin.duracao_treino = duracao
        db.commit()
        logger.info(
            f"Check-out em lote registrado para aluno {aluno_id} - Duração: {duracao} minutos"
        )
        return True
    except Exception as e:
        db.rollback()
        logger.error(
            f"Erro ao registrar check-out para aluno {aluno_id}: {str(e)}"
        )
        raise


def obter_data_evento(timestamp):
    """
    Obtém a data do evento a partir do timestamp

    Args:
        timestamp: String ISO formatada ou None

    Returns:
        datetime: Data/hora do evento ou data atual se timestamp for None
    """
    if not timestamp:
        return datetime.now()

    try:
        return datetime.fromisoformat(timestamp)
    except ValueError as e:
        logger.error(f"Formato de timestamp inválido: {timestamp} - {str(e)}")
        return datetime.now()


def validar_aluno(db, aluno_id):
    """
    Verifica se o aluno existe no banco de dados

    Args:
        db: Sessão do banco de dados
        aluno_id: ID do aluno a ser validado

    Returns:
        bool: True se o aluno existe, False caso contrário
    """
    if not aluno_id:
        return False

    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    return aluno is not None


def processar_checkin_em_lote(channel, method, properties, body):
    """
    Processa mensagens de check-in em lote do RabbitMQ.

    Args:
        channel: Canal RabbitMQ
        method: Método da mensagem
        properties: Propriedades da mensagem
        body: Corpo da mensagem (JSON)
    """
    try:
        # Decodificar a mensagem JSON
        data = json.loads(body)
        logger.info(f"Processando check-in em lote: {data}")

        # Extrair e validar dados necessários
        aluno_id = data.get("aluno_id")
        tipo = data.get("tipo")
        timestamp = data.get("timestamp")

        if not aluno_id or not tipo:
            logger.error(f"Dados inválidos na mensagem: {data}")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        data_evento = obter_data_evento(timestamp)

        # Validar aluno
        db = next(get_db())
        if not validar_aluno(db, aluno_id):
            logger.warning(f"Aluno inválido: {aluno_id}")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Processar conforme o tipo
        try:
            if tipo == "entrada":
                # Importação local para permitir mocking nos testes
                from challenge.rabbitmq.consumers.batch_checkin_consumer import (
                    processar_entrada,
                )

                processar_entrada(db, aluno_id, data_evento)
            elif tipo == "saida":
                # Importação local para permitir mocking nos testes
                from challenge.rabbitmq.consumers.batch_checkin_consumer import (
                    processar_saida,
                )

                processar_saida(db, aluno_id, data_evento)
            else:
                logger.warning(f"Tipo de operação inválido: {tipo}")

            # Confirmar processamento bem-sucedido
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(
                f"Erro ao processar operação {tipo} para aluno {aluno_id}: {str(e)}"
            )
            # Rejeitar a mensagem em caso de erro de processamento
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON da mensagem: {str(e)}")
        # JSON inválido, não adianta reprocessar
        channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(
            f"Erro não esperado ao processar check-in em lote: {str(e)}"
        )
        # Rejeitar a mensagem para reprocessamento
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def iniciar_consumidor_checkins_em_lote():
    """Inicia o consumidor de check-ins em lote"""
    try:
        channel_manager = ChannelRabbitMQ()
        channel = channel_manager.get_channel()

        # Configurar fila e bindings
        queue_name = "checkins.batch"
        exchange_name = "academia.eventos"
        routing_key = "checkin.batch"

        channel.queue_declare(queue=queue_name, durable=True)
        channel.queue_bind(
            exchange=exchange_name,
            queue=queue_name,
            routing_key=routing_key,
        )

        # Configurar processamento um por vez
        channel.basic_qos(prefetch_count=1)

        # Registrar o callback
        channel.basic_consume(
            queue=queue_name, on_message_callback=processar_checkin_em_lote
        )

        logger.info(
            "Consumidor de check-ins em lote iniciado. Para sair, pressione CTRL+C"
        )
        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info(
            "Consumidor de check-ins em lote interrompido pelo usuário"
        )

    except Exception as e:
        logger.error(
            f"Erro ao iniciar consumidor de check-ins em lote: {str(e)}"
        )
        sys.exit(1)


if __name__ == "__main__":
    iniciar_consumidor_checkins_em_lote()
