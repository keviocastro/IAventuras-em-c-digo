import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

from infraestructure.channel import ChannelRabbitMQ
from models.database import get_db
from models.entities import CheckIn, Aluno


def processar_checkin(ch, method, properties, body):
    """
    Processa um evento de check-in recebido do RabbitMQ
    """
    try:
        # Decodificar a mensagem JSON
        mensagem = json.loads(body)
        print(f"Processando checkin: {mensagem}")

        # Criar sessão com o banco
        db = next(get_db())

        # Verificar se o aluno existe
        aluno_id = mensagem.get("aluno_id")
        aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
        if not aluno:
            print(f"Aluno {aluno_id} não encontrado")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Verificar o tipo de evento (entrada ou saída)
        tipo = mensagem.get("tipo")
        timestamp = mensagem.get("timestamp")
        data = (
            datetime.fromisoformat(timestamp) if timestamp else datetime.now()
        )

        if tipo == "entrada":
            # Registrar novo check-in
            novo_checkin = CheckIn(aluno_id=aluno_id, data_entrada=data)
            db.add(novo_checkin)
            db.commit()
            print(f"Check-in registrado para aluno {aluno_id}")

        elif tipo == "saida":
            # Buscar último check-in aberto para o aluno
            ultimo_checkin = (
                db.query(CheckIn)
                .filter(
                    CheckIn.aluno_id == aluno_id,
                    CheckIn.duracao_treino.is_(None),
                )
                .order_by(CheckIn.data_entrada.desc())
                .first()
            )

            if ultimo_checkin:
                ultimo_checkin.duracao_treino = (
                    data - ultimo_checkin.data_entrada
                ).total_seconds() / 60
                db.commit()
                print(f"Check-out registrado para aluno {aluno_id}")
            else:
                print(
                    f"Nenhum check-in aberto encontrado para o aluno {aluno_id}"
                )

        # Confirmar o processamento da mensagem
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Erro ao processar checkin: {e}")
        # Em caso de erro, não confirmamos o processamento para que a mensagem seja reprocessada
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def iniciar_consumidor_checkins():
    """
    Inicia o consumidor de check-ins
    """
    channel_manager = ChannelRabbitMQ()
    channel = channel_manager.get_channel()

    # Garantir que a fila existe
    channel.queue_declare(queue="checkins.processamento", durable=True)

    # Configurar o consumidor para processar uma mensagem por vez
    channel.basic_qos(prefetch_count=1)

    # Registrar o callback
    channel.basic_consume(
        queue="checkins.processamento", on_message_callback=processar_checkin
    )

    print("Aguardando mensagens de check-ins. Para sair, pressione CTRL+C")
    channel.start_consuming()


if __name__ == "__main__":
    iniciar_consumidor_checkins()
