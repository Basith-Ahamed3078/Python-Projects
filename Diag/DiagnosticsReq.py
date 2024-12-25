import threading
import time
import pika
import json
from pika.exchange_type import ExchangeType

ECU_Name = "DiagRequest"
Network = "ACC_Vehicle_Network"
Channel = 1
Baudrate = 500000
print("Connected with Channel 1 and run at speed of kbps")


def TransmitMsg(b0, b1, b2, b3, b4, b5, b6, b7):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()

        # Declare the exchange with durable=True to match the existing configuration
        channel.exchange_declare(exchange='DiagRequestExchange', exchange_type=ExchangeType.fanout, durable=True)

        # Define the diagnostic message
        Diag_info = {
            "ID": hex(0x620),
            "Tx Method": "Event",
            "Cycle Time": 0,
            "Channel": 1,
            "DLC": 8,
            "Data": {
                "byte0": hex(b0),
                "byte1": hex(b1),
                "byte2": hex(b2),
                "byte3": hex(b3),
                "byte4": hex(b4),
                "byte5": hex(b5),
                "byte6": hex(b6),
                "byte7": hex(b7),
            }
        }

        # Convert message to JSON and transmit
        result = json.dumps(Diag_info)
        print("Transmitting Event Message...", result)
        channel.basic_publish(exchange='DiagRequestExchange', routing_key="", body=result)

    except Exception as e:
        print("Error transmitting message:", e)
    finally:
        if connection:
            connection.close()



# Call the function with 8 bytes of data
TransmitMsg(0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
#time.sleep(2)
#TransmitMsg(0x10, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
time.sleep(2)
TransmitMsg(0x10, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
time.sleep(2)
TransmitMsg(0x2E, 0xDE, 0x00, 0x72, 0x73, 0x74, 0x75, 0x76)
#time.sleep(2)
#ransmitMsg(0x22, 0xDE, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
