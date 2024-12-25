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

# Global variable to store data from 2E DE 00 request
stored_data = {
    "byte3": "0x00",
    "byte4": "0x00",
    "byte5": "0x00",
    "byte6": "0x00",
    "byte7": "0x00"
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
            global stored_data
            request = json.loads(body)
            byte0 = int(request["Data"].get("byte0", "0x00"), 16)
            byte1 = int(request["Data"].get("byte1", "0x00"), 16)
            byte2 = int(request["Data"].get("byte2", "0x00"), 16)

            # Handle 10 SID request
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

            # Handle 2E SID request
            elif byte0 == 0x2E and byte1 == 0xDE and byte2 == 0x00:
                print("Handling 2E DE 00 request...")
                # Store the incoming data
                stored_data = {
                    "byte3": request["Data"].get("byte3", "0x00"),
                    "byte4": request["Data"].get("byte4", "0x00"),
                    "byte5": request["Data"].get("byte5", "0x00"),
                    "byte6": request["Data"].get("byte6", "0x00"),
                    "byte7": request["Data"].get("byte7", "0x00")
                }
                response = {
                    "byte0": "0x6E",  # Positive response to SID 0x2E
                    "byte1": "0xDE",
                    "byte2": "0x00",
                    "byte3": "0x00",
                    "byte4": "0x00",
                    "byte5": "0x00",
                    "byte6": "0x00",
                    "byte7": "0x00"
                }
                send_response(response)

            # Handle 22 SID request
            elif byte0 == 0x22 and byte1 == 0xDE and byte2 == 0x00:
                print("Handling 22 DE 00 request...")
                # Respond with the stored data
                response = {
                    "byte0": "0x62",  # Positive response to SID 0x22
                    "byte1": "0xDE",
                    "byte2": "0x00",
                    "byte3": stored_data["byte3"],
                    "byte4": stored_data["byte4"],
                    "byte5": stored_data["byte5"],
                    "byte6": stored_data["byte6"],
                    "byte7": stored_data["byte7"]
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
