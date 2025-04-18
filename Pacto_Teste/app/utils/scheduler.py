import pika, json, time, sys
import schedule

def publish_report_request():
    credentials = pika.PlainCredentials("admin", "admin123")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='relatorio', durable=True)
    msg = json.dumps({"action": "gerar_relatorio", "data": time.strftime("%Y-%m-%d")})
    channel.basic_publish(
        exchange='',
        routing_key='relatorio',
        body=msg,
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print(" [x] Pedido de relatório enviado")
    connection.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run_manual":
        publish_report_request()
    else:
        schedule.every().day.at("08:00").do(publish_report_request)
        while True:
            schedule.run_pending()
            time.sleep(60)

def publish_churn_update():
    credentials = pika.PlainCredentials("admin", "admin123")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='churn', durable=True)
    msg = json.dumps({"action": "atualizar_churn"})
    channel.basic_publish(
        exchange='',
        routing_key='churn',
        body=msg,
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print(" [x] Pedido de atualização de churn enviado")
    connection.close()