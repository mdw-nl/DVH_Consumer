from DICOM_solver.queue_processing import Consumer
from DICOM_solver.callback import callback
import logging
from DICOM_solver.config_handler import Config
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

if __name__ == "__main__":

    rabbitMQ_config = Config("rabbitMQ")
    cons = Consumer(rmq_config=rabbitMQ_config)
    cons.open_connection_rmq()
    cons.start_consumer(callback=callback)
