import threading
import time
import random
import pika
import json
from pika.exchange_type import ExchangeType
import multiprocessing

ECU_Name = "BCM"
Network = "CAN Network"
Channel = 1
Baudrate = 500000

print("Connected with Channel 1")

BCM_info = {"ID": hex(0x32A), "Tx Method": "Cyclic", "Cycle Time": 250, "Channel": 1, "DLC": 1, "Data":{"VehicleSpeed":10 }}


def TransmitMsg():
    try:

            connection = pika.BlockingConnection(pika.ConnectionParameters(host = 'localhost'))
            channel = connection.channel()
            channel.exchange_declare(exchange= 'BCMMessage', exchange_type=ExchangeType.fanout)
            while True:
                result=json.dumps(BCM_info)
                print("Transmitting..", result)

                channel.basic_publish(exchange = 'BCMMessage', routing_key = "", body = result)

                #connection.close()
                time.sleep(0.25)
    except KeyboardInterrupt:
        print("Message Transmission stopped by user")
    finally:
        if connection:
            connection.close()

    #threading.Timer(int(BCM_info["Cycle Time"])/1000,TransmitMsg).start()

def onmsg():
    print("Ready to receive")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host = 'localhost'))
    channel = connection.channel()




    queue = channel.queue_declare(queue= "",exclusive=True)
    channel.queue_bind(exchange="IPCMessage",queue=queue.method.queue)
    channel.basic_consume(queue=queue.method.queue, on_message_callback=callback, auto_ack=True)
    channel.queue_bind(exchange="ACCExchange", queue=queue.method.queue)
    channel.basic_consume(queue=queue.method.queue, on_message_callback=callback, auto_ack=True)
    channel.queue_bind(exchange="ICMExchange", queue=queue.method.queue)
    channel.basic_consume(queue=queue.method.queue, on_message_callback=callback, auto_ack=True)

    print("waiting for message . To Exit Press CTRL+C")
    channel.start_consuming()

def callback(ch, method, properties, body):
    print("Received", body)

if __name__ == "__main__":
    # Create threads for TransmitMsg and onmsg
    transmitter_thread = threading.Thread(target=TransmitMsg, daemon=True)
    receiver_thread = threading.Thread(target=onmsg, daemon=True)

    # Start the threads
    transmitter_thread.start()
    receiver_thread.start()

    # Wait for threads to complete
    transmitter_thread.join()
    receiver_thread.join()