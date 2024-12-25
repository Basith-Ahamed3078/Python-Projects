import threading
import time
import pika
import json
from pika.exchange_type import ExchangeType

ECU_Name = "Diag Response"
Network = "ACC_Vehicle_Network"
Channel = 1
Baudrate = 500000
print("Connected with Channel 1 and run at speed of kbps")

# Define ECM_info for responses
Response_info = {
    "ID": hex(0x720),
    "Tx Method": "Event",
    "Cycle Time": 0,
    "Channel": 1,
    "DLC": 8,
    "Data": {"byte0": "0x00", "byte1": "0x00", "byte2": "0x00", "byte3": "0x00",
             "byte4": "0x00", "byte5": "0x00", "byte6": "0x00", "byte7": "0x00"}
}

def send_response(response_data):
    """
    Send the response message with the given data.
    """
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.exchange_declare(exchange='DiagResponseExchange', exchange_type=ExchangeType.fanout, durable=False)

        # Update ECM_info with response data
        Response_info["Data"].update(response_data)
        result = json.dumps(Response_info)
        print("Transmitting Response...", result)

        # Publish the response
        channel.basic_publish(exchange='DiagResponseExchange', routing_key="", body=result)

    finally:
        if connection:
            connection.close()


def onmsg():
    """
    Listen for incoming messages and respond accordingly.
    """
    def callback(ch, method, properties, body):
        print("Received:", body)
        try:
            request = json.loads(body)
            byte0 = int(request["Data"].get("byte0", "0x00"), 16)
            byte1 = int(request["Data"].get("byte1", "0x00"), 16)
            byte2 = int(request["Data"].get("byte2", "0x00"), 16)

            # Prepare a response based on the SID
            if byte0 == 0x10:
                print("Handling 10 SID request...")
                response = {
                    "byte0": "0x50",  # Positive response to SID 0x10
                    "byte1": hex(byte1),
                    "byte2": "0x01",
                    "byte3": "0xF4",
                    "byte4": "0x13",
                    "byte5": "0x88",
                    "byte6": "0x00",
                    "byte7": "0x00"
                }
                send_response(response)

            elif byte0 == 0x2E:
                print("Handling 2E SID request...")
                # Response for 2E SID
                response = {
                    "byte0": "0x6E",  # Positive response to SID 0x2E
                    "byte1": hex(byte1),
                    "byte2": "0x00",
                    "byte3": "0x00",
                    "byte4": "0x00",
                    "byte5": "0x00",
                    "byte6": "0x00",
                    "byte7": "0x00"
                }
                send_response(response)

            else:
                print("Unknown SID request, echoing back...")
                # Echo back whatever was received
                response = {
                    "byte0": hex(byte0),
                    "byte1": hex(byte1),
                    "byte2": hex(byte2),
                    "byte3": request["Data"].get("byte3", "0x00"),
                    "byte4": request["Data"].get("byte4", "0x00"),
                    "byte5": request["Data"].get("byte5", "0x00"),
                    "byte6": request["Data"].get("byte6", "0x00"),
                    "byte7": request["Data"].get("byte7", "0x00")
                }
                send_response(response)

        except Exception as e:
            print("Error processing message:", e)

    print("Waiting for messages. To Exit Press CTRL+C")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    # Declare the exchange before binding
    channel.exchange_declare(exchange="DiagRequestExchange", exchange_type=ExchangeType.fanout, durable=True)

    # Bind to the exchange to receive requests
    queue = channel.queue_declare(queue="", exclusive=True)
    channel.queue_bind(exchange="DiagRequestExchange", queue=queue.method.queue)

    # Start consuming messages
    channel.basic_consume(queue=queue.method.queue, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()


if __name__ == "__main__":
    # Start the message listener
    onmsg()
