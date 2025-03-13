import pika

RABBITMQ_URL = "amqp://user:password@host.docker.internal:5672/"
QUEUE_NAME = "DICOM_Processor"


class Consumer:
    def __init__(self, rmq_config):
        self.connection_rmq = None
        self.channel = None
        self.config_dict_rmq = rmq_config.config
        self.db = None

    def open_connection_rmq(self):
        """Establish connection"""
        host, port, user, pwd = self.config_dict_rmq["host"], self.config_dict_rmq["port"] \
            , self.config_dict_rmq["username"], self.config_dict_rmq["password"]

        connection_string = f"amqp://{user}:{pwd}@{host}:{port}/"
        connection = pika.BlockingConnection(pika.URLParameters(connection_string))
        self.connection_rmq = connection
        self.channel = self.connection_rmq.channel()

    def close_connection(self):
        """Close connection"""

        self.connection_rmq.close()

    def start_consumer(self, callback):
        self.channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=False)
        self.channel.start_consuming()
