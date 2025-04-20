import json
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

from infraestructure.channel import ChannelRabbitMQ
from models.database import get_db
from models.entities import CheckIn, Aluno


def gerar_relatorio_diario(data_str, db):
    """
    Gera um relatório diário de frequência
    """
    try:
        # Converter string para data
        data = datetime.fromisoformat(data_str).date()

        # Definir início e fim do dia
        inicio_dia = datetime.combine(data, datetime.min.time())
        fim_dia = datetime.combine(data, datetime.max.time())

        # Buscar todos os check-ins do dia
        checkins = (
            db.query(CheckIn)
            .filter(
                CheckIn.data_entrada >= inicio_dia,
                CheckIn.data_entrada <= fim_dia,
            )
            .all()
        )

        # Obter estatísticas
        total_checkins = len(checkins)
        alunos_distintos = len(set(c.aluno_id for c in checkins))

        # Calcular distribuição por hora
        horas = {}
        for h in range(24):
            horas[h] = 0

        for checkin in checkins:
            hora = checkin.data_entrada.hour
            horas[hora] += 1

        # Criar diretório para relatórios se não existir
        relatorios_dir = Path(__file__).parent.parent.parent / "relatorios"
        if not relatorios_dir.exists():
            relatorios_dir.mkdir(parents=True, exist_ok=True)

        # Gerar gráfico de distribuição por hora
        df = pd.DataFrame(list(horas.items()), columns=["Hora", "Frequência"])
        plt.figure(figsize=(12, 6))
        plt.bar(df["Hora"], df["Frequência"])
        plt.title(f"Distribuição de Check-ins por Hora - {data}")
        plt.xlabel("Hora do dia")
        plt.ylabel("Número de check-ins")
        plt.xticks(range(24))
        plt.grid(axis="y", linestyle="--", alpha=0.7)

        grafico_path = relatorios_dir / f"frequencia_{data}.png"
        plt.savefig(grafico_path)

        # Gerar relatório em texto
        relatorio_path = relatorios_dir / f"relatorio_{data}.txt"
        with open(relatorio_path, "w") as f:
            f.write(f"Relatório de Frequência - {data}\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Total de check-ins: {total_checkins}\n")
            f.write(f"Total de alunos distintos: {alunos_distintos}\n\n")
            f.write("Distribuição por hora:\n")
            for hora, qtd in horas.items():
                f.write(f"{hora:02d}:00 - {qtd} check-ins\n")

        return {
            "data": data_str,
            "total_checkins": total_checkins,
            "alunos_distintos": alunos_distintos,
            "grafico_path": grafico_path,
            "relatorio_path": relatorio_path,
        }

    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
        return None


def processar_solicitacao_relatorio(ch, method, properties, body):
    """
    Processa uma solicitação de relatório recebida do RabbitMQ
    """
    try:
        # Decodificar a mensagem JSON
        mensagem = json.loads(body)
        print(f"Processando solicitação de relatório: {mensagem}")

        data = mensagem.get("data")
        if not data:
            data = datetime.now().date().isoformat()

        # Criar sessão com o banco
        db = next(get_db())

        # Gerar o relatório
        resultado = gerar_relatorio_diario(data, db)

        if resultado:
            print(
                f"Relatório gerado com sucesso: {resultado['relatorio_path']}"
            )
        else:
            print("Falha ao gerar relatório")

        # Confirmar o processamento da mensagem
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Erro ao processar solicitação de relatório: {e}")
        # Em caso de erro, não confirmamos o processamento para que a mensagem seja reprocessada
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def iniciar_consumidor_relatorios():
    """
    Inicia o consumidor de solicitações de relatório
    """
    channel_manager = ChannelRabbitMQ()
    channel = channel_manager.get_channel()

    # Garantir que a fila existe
    channel.queue_declare(queue="relatorios.diarios", durable=True)

    # Configurar o consumidor para processar uma mensagem por vez
    channel.basic_qos(prefetch_count=1)

    # Registrar o callback
    channel.basic_consume(
        queue="relatorios.diarios",
        on_message_callback=processar_solicitacao_relatorio,
    )

    print("Aguardando solicitações de relatório. Para sair, pressione CTRL+C")
    channel.start_consuming()


if __name__ == "__main__":
    iniciar_consumidor_relatorios()
