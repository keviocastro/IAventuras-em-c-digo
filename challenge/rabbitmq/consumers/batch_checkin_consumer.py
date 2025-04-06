import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

from infraestructure.channel import ChannelRabbitMQ
from models.database import get_db
from models.entities import CheckIn, Aluno


def processar_entrada(db, aluno_id, data):
    """Registra um novo check-in para o aluno"""
    novo_checkin = CheckIn(aluno_id=aluno_id, data_entrada=data)
    db.add(novo_checkin)
    db.commit()
    print(f"Check-in em lote registrado para aluno {aluno_id}")
    return True


def processar_saida(db, aluno_id, data):
    """Registra a saída para o último check-in aberto do aluno"""
    ultimo_checkin = (
        db.query(CheckIn)
        .filter(CheckIn.aluno_id == aluno_id, CheckIn.data_saida.is_(None))
        .order_by(CheckIn.data_entrada.desc())
        .first()
    )

    if not ultimo_checkin:
        print(f"Nenhum check-in aberto encontrado para o aluno {aluno_id}")
        return False

    ultimo_checkin.data_saida = data
    ultimo_checkin.duracao = (
        data - ultimo_checkin.data_entrada
    ).total_seconds() / 60
    db.commit()
    print(f"Check-out em lote registrado para aluno {aluno_id}")
    return True


def obter_data_evento(timestamp):
    """Obtém a data do evento a partir do timestamp"""
    return datetime.fromisoformat(timestamp) if timestamp else datetime.now()


def validar_aluno(db, aluno_id):
    """Verifica se o aluno existe no banco de dados"""
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    return aluno is not None


def processar_checkin_em_lote(ch, method, properties, body):
    """Processa um check-in do lote recebido do RabbitMQ"""
    try:
        # Decodificar a mensagem JSON
        mensagem = json.loads(body)
        print(f"Processando check-in em lote: {mensagem}")

        # Extrair dados da mensagem
        aluno_id = mensagem.get("aluno_id")
        tipo = mensagem.get("tipo", "")
        timestamp = mensagem.get("timestamp")

        # Abrir conexão com o banco
        db = next(get_db())

        # Validar aluno
        if not validar_aluno(db, aluno_id):
            print(f"Aluno {aluno_id} não encontrado")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Obter data do evento
        data = obter_data_evento(timestamp)

        # Processar por tipo de operação
        processadores = {
            "entrada": processar_entrada,
            "saida": processar_saida,
        }

        processador = processadores.get(tipo)
        if processador:
            processador(db, aluno_id, data)
        else:
            print(f"Tipo de operação inválido: {tipo}")

        # Confirmar o processamento da mensagem
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Erro ao processar check-in em lote: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def iniciar_consumidor_checkins_em_lote():
    """Inicia o consumidor de check-ins em lote"""
    channel_manager = ChannelRabbitMQ()
    channel = channel_manager.get_channel()

    # Configurar fila e bindings
    channel.queue_declare(queue="checkins.batch", durable=True)
    channel.queue_bind(
        exchange="academia.eventos",
        queue="checkins.batch",
        routing_key="checkin.batch",
    )

    # Configurar processamento um por vez
    channel.basic_qos(prefetch_count=1)

    # Registrar o callback
    channel.basic_consume(
        queue="checkins.batch", on_message_callback=processar_checkin_em_lote
    )

    print(
        "Aguardando mensagens de check-ins em lote. Para sair, pressione CTRL+C"
    )
    channel.start_consuming()


if __name__ == "__main__":
    iniciar_consumidor_checkins_em_lote()
