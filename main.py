from DICOM_solver.queue_processing import Consumer
from DICOM_solver.dvh_processor import callback_tread
import logging
from DICOM_solver.config_handler import Config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

if __name__ == "__main__":
    try:
        rabbitMQ_config = Config("rabbitMQ")
        cons = Consumer(rmq_config=rabbitMQ_config)
        cons.open_connection_rmq()
        cons.create_channel()
        cons.start_consumer(callback=callback_tread)

    except Exception as e:
        logger.error(f"An error occurred while trying to start the server: {e}")
        logger.error("Please check the configuration and the RabbitMQ server status.")
        raise e



