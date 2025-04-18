from flask import Flask, request, jsonify, render_template
from models import Session, Aluno, Plano, Checkin, Base, engine
from consumer import start_consumer
from datetime import datetime
from collections import defaultdict
import time, os, json, pika, threading, joblib

app = Flask(__name__)

@app.route("/")
def main():
    return render_template('portal.html')

@app.route("/api/alunos")
def api_alunos():
    session = Session()
    alunos = session.query(Aluno).join(Plano).all()
    lista = [{
        "id": a.id,
        "nome": a.nome,
        "cpf": a.cpf,
        "plano": a.plano.descricao
    } for a in alunos]
    session.close()
    return jsonify(lista)

@app.route("/aluno/registro", methods=["POST"])
def registrar_aluno():
    data = request.get_json()
    nome, cpf, plano_id = data.get("nome"), data.get("cpf"), data.get("plano")

    if not nome or not cpf or not plano_id:
        return jsonify({"error": "Dados incompletos"}), 400

    session = Session()
    if session.query(Aluno).filter_by(cpf=cpf).first():
        session.close()
        return jsonify({"error": "Aluno com este CPF já está cadastrado"}), 400

    aluno = Aluno(nome=nome, cpf=cpf, plano_id=plano_id)
    session.add(aluno)
    session.commit()
    session.close()

    return jsonify({"message": "Aluno registrado com sucesso"})

@app.route("/aluno/checkin", methods=["POST"])
def aluno_checkin():
    cpf = request.form.get('cpf')
    session = Session()
    aluno = session.query(Aluno).filter_by(cpf=cpf).first()
    session.close()

    if not aluno:
        return jsonify({"message": "Aluno não encontrado"})

    rabbit_url = os.getenv("RABBITMQ_URL")
    connection = pika.BlockingConnection(pika.URLParameters(rabbit_url))
    channel = connection.channel()
    channel.queue_declare(queue='checkins', durable=True)

    message = json.dumps({'aluno_id': aluno.id})
    channel.basic_publish(exchange='', routing_key='checkins', body=message)
    connection.close()

    return jsonify({"message": "Checkin / Checkout realizado com sucesso"})

@app.route("/aluno/<int:id>/frequencia")
def frequencia(id):
    session = Session()
    checkins = session.query(Checkin).filter_by(aluno_id=id).all()
    resultado = [{
        "checkin": c.checkin.strftime("%Y-%m-%d %H:%M:%S") if c.checkin else None,
        "checkout": c.checkout.strftime("%Y-%m-%d %H:%M:%S") if c.checkout else None
    } for c in checkins]
    session.close()
    return jsonify(resultado)

@app.route("/aluno/<int:id>/risco-churn")
def risco_churn(id):
    modelo_carregado = joblib.load('treinamento/modelo_treinado.pkl')
    session = Session()
    aluno = session.query(Aluno).filter_by(id=id).first()
    if not aluno:
        session.close()
        return jsonify({"error": "Aluno não encontrado"}), 404

    checkins = session.query(Checkin).filter_by(aluno_id=id).all()
    tempos, datas_checkin = [], []
    ultimo_checkout, checkin_mais_antigo = None, None

    for checkin in checkins:
        if checkin.checkin:
            data_checkin = checkin.checkin.date()
            datas_checkin.append(data_checkin)
            if not checkin_mais_antigo or data_checkin < checkin_mais_antigo:
                checkin_mais_antigo = data_checkin

        if checkin.checkin and checkin.checkout:
            tempo = checkin.checkout - checkin.checkin
            tempos.append(tempo.total_seconds() / 60)
            if not ultimo_checkout or checkin.checkout > ultimo_checkout:
                ultimo_checkout = checkin.checkout

    plano = session.query(Plano).filter_by(id=aluno.plano_id).first()
    session.close()

    if not checkin_mais_antigo or (datetime.now().date() - checkin_mais_antigo).days < 30:
        return jsonify({
            "tempo_medio_visita_minutos": None,
            "media_checkins_semanal": None,
            "ultimo_checkout": ultimo_checkout.strftime("%Y-%m-%d %H:%M:%S") if ultimo_checkout else None,
            "plano": plano.descricao,
            "Probabilidade de solicitação de cancelamento:": "Aluno com menos de 1 mês, não é possível informar a probabilidade de cancelamento no momento."
        })

    media_tempo = sum(tempos) / len(tempos) if tempos else 0

    dias_por_semana = defaultdict(set)
    for data in datas_checkin:
        ano_semana = data.isocalendar()[:2]
        dias_por_semana[ano_semana].add(data)

    total_semanas = len(dias_por_semana)
    total_dias = sum(len(dias) for dias in dias_por_semana.values())
    media_dias_por_semana = total_dias / total_semanas if total_semanas > 0 else 0

    horas_desde_ultimo_checkout = (datetime.now() - ultimo_checkout).total_seconds() / 3600

    probabilidade = modelo_carregado.predict_proba([[
        media_dias_por_semana,
        horas_desde_ultimo_checkout,
        media_tempo,
        aluno.plano_id]])[0][1]

    return jsonify({
        "tempo_medio_visita_minutos": round(media_tempo, 2),
        "media_checkins_semanal": round(media_dias_por_semana, 2),
        "ultimo_checkout": ultimo_checkout.strftime("%Y-%m-%d %H:%M:%S") if ultimo_checkout else None,
        "plano": plano.descricao,
        "Probabilidade de solicitação de cancelamento:": round(probabilidade * 100, 2)
    })

def wait_for_rabbitmq(retries=10, delay=3):
    rabbit_url = os.getenv("RABBITMQ_URL")
    for i in range(retries):
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbit_url))
            connection.close()
            print("RabbitMQ está online!")
            return
        except pika.exceptions.AMQPConnectionError:
            print(f"⏳ RabbitMQ ainda não está pronto... tentativa {i+1}/{retries}")
            time.sleep(delay)
    raise Exception("Não foi possível conectar ao RabbitMQ após várias tentativas.")

if __name__ == "__main__":
    wait_for_rabbitmq()
    threading.Thread(target=start_consumer, daemon=True).start()
    Base.metadata.create_all(engine)
    app.run(host="0.0.0.0", port=5000)