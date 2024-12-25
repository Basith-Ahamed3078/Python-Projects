import time
import pika
import json
from pika.exchange_type import ExchangeType


def wait_for_flow_control():
    """
    Wait for the Flow Control (FC) frame from the receiver.
    """
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()

        # Declare the exchange before binding
        channel.exchange_declare(exchange="DiagResponseExchange", exchange_type=ExchangeType.fanout, durable=False)
        queue = channel.queue_declare(queue="", exclusive=True)
        channel.queue_bind(exchange="DiagResponseExchange", queue=queue.method.queue)

        print("Waiting for Flow Control Frame...")
        retries = 50  # Maximum retries (5 seconds with 100ms per attempt)
        while retries > 0:
            method, properties, body = channel.basic_get(queue=queue.method.queue, auto_ack=True)
            if body:
                print("Flow Control Frame Received:", body)
                response = json.loads(body)
                if int(response["Data"].get("byte0", "0x00"), 16) == 0x30:  # FC frame detected
                    print("Flow Control Accepted: Continuing Transmission...")
                    return True
                else:
                    print("Unexpected Frame Received. Ignoring...")
            time.sleep(0.1)  # Short delay between retries
            retries -= 1

        print("Flow Control Frame not received within timeout.")
        return False

    except Exception as e:
        print("Error waiting for Flow Control:", e)
        return False

    finally:
        if connection:
            connection.close()


def transmit_multiframe_message(data):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.exchange_declare(exchange='DiagRequestExchange', exchange_type=ExchangeType.fanout, durable=True)

        # Calculate total length of the data
        total_length = len(data)

        # Create and send the First Frame (FF)
        first_frame = {
            "ID": hex(0x620),
            "Tx Method": "Event",
            "Cycle Time": 0,
            "Channel": 1,
            "DLC": 8,
            "Data": {
                "byte0": hex(0x10),
                "byte1": hex(total_length),
                "byte2": hex(data[0]),
                "byte3": hex(data[1]),
                "byte4": hex(data[2]),
                "byte5": hex(data[3]),
                "byte6": hex(data[4]),
                "byte7": hex(data[5])
            }
        }
        print("Transmitting First Frame...", json.dumps(first_frame))
        channel.basic_publish(exchange='DiagRequestExchange', routing_key="", body=json.dumps(first_frame))

        # Wait for Flow Control (FC) response from receiver
        print("Waiting for Flow Control...")
        if not wait_for_flow_control():
            print("Flow Control Frame not received. Stopping transmission.")
            return

        # Send Consecutive Frames (CF)
        sequence_number = 1
        for i in range(6, total_length, 7):
            consecutive_frame = {
                "ID": hex(0x620),
                "Tx Method": "Event",
                "Cycle Time": 0,
                "Channel": 1,
                "DLC": 8,
                "Data": {
                    "byte0": hex(0x20 | sequence_number),
                    "byte1": hex(data[i] if i < total_length else 0x00),
                    "byte2": hex(data[i + 1] if i + 1 < total_length else 0x00),
                    "byte3": hex(data[i + 2] if i + 2 < total_length else 0x00),
                    "byte4": hex(data[i + 3] if i + 3 < total_length else 0x00),
                    "byte5": hex(data[i + 4] if i + 4 < total_length else 0x00),
                    "byte6": hex(data[i + 5] if i + 5 < total_length else 0x00),
                    "byte7": hex(data[i + 6] if i + 6 < total_length else 0x00)
                }
            }
            print("Transmitting Consecutive Frame...", json.dumps(consecutive_frame))
            channel.basic_publish(exchange='DiagRequestExchange', routing_key="", body=json.dumps(consecutive_frame))

            # Increment sequence number and wrap around if necessary
            sequence_number = (sequence_number + 1) & 0x0F

            # Respect Separation Time (STmin)
            time.sleep(0.01)  # 10 ms

    except Exception as e:
        print("Error transmitting multi-frame message:", e)

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    # Example data to send: 22 bytes (more than 8 bytes)
    data = [0x2E, 0xDE, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13]
    transmit_multiframe_message(data)
