import time
import pika
import json
from pika.exchange_type import ExchangeType

# Global variables to handle flow control and stored data
stored_data = []
expected_data_length = 0

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
    Listen for incoming messages and handle transport protocol.
    """
    def callback(ch, method, properties, body):
        print("Received:", body)
        global stored_data, expected_data_length
        try:
            request = json.loads(body)
            byte0 = int(request["Data"].get("byte0", "0x00"), 16)
            byte1 = int(request["Data"].get("byte1", "0x00"), 16)

            # Handle First Frame (FF)
            if byte0 == 0x10:
                print("First Frame detected. Sending Flow Control...")
                expected_data_length = byte1  # Total data length from FF

                # Store initial data from First Frame
                stored_data = [
                    request["Data"].get("byte2", "0x00"),
                    request["Data"].get("byte3", "0x00"),
                    request["Data"].get("byte4", "0x00"),
                    request["Data"].get("byte5", "0x00"),
                    request["Data"].get("byte6", "0x00"),
                    request["Data"].get("byte7", "0x00")
                ]

                # Send Flow Control (FC) frame
                flow_control_response = {
                    "byte0": "0x30",  # Flow Control Frame
                    "byte1": "0x00",  # Block size (0 = continuous transmission)
                    "byte2": "0x0A",  # STmin (10ms)
                    "byte3": "0x00",
                    "byte4": "0x00",
                    "byte5": "0x00",
                    "byte6": "0x00",
                    "byte7": "0x00"
                }
                send_response(flow_control_response)

            # Handle Consecutive Frames (CF)
            elif byte0 >= 0x20 and byte0 <= 0x2F:
                print("Consecutive Frame detected. Appending data...")
                # Append data from CF
                stored_data.extend([
                    request["Data"].get("byte1", "0x00"),
                    request["Data"].get("byte2", "0x00"),
                    request["Data"].get("byte3", "0x00"),
                    request["Data"].get("byte4", "0x00"),
                    request["Data"].get("byte5", "0x00"),
                    request["Data"].get("byte6", "0x00"),
                    request["Data"].get("byte7", "0x00")
                ])

                # Check if all data is received
                if len(stored_data) >= expected_data_length:
                    print("All data received. Sending positive response.")
                    response = {
                        "byte0": "0x6E",  # Positive response to 2E SID
                        "byte1": "0xDE",
                        "byte2": "0x00",
                        "byte3": "0x00",
                        "byte4": "0x00",
                        "byte5": "0x00",
                        "byte6": "0x00",
                        "byte7": "0x00"
                    }
                    send_response(response)
                    stored_data = []  # Reset for next transaction

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
