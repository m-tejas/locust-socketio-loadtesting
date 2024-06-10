import json
from dotenv import dotenv_values
import uuid
import time
from locust_plugins import *
from locust import task, between, HttpUser, events
import socketio
from locust.env import Environment


class SocketIOUser(HttpUser):
    wait_time = between(1, 5)
    config = dotenv_values('.env')  # Config .env file to access URL, User Credentials etc
    host = config['url']
    base_url = host
    path = config['path']

    message = {"Test"}   # Enter your message here

    def __init__(self, parent):
        super().__init__(parent)
        self.end_time = None
        self.sio = socketio.Client()  # Creating Instances of socket IO client
        self.received_response = False
        self.should_reconnect = True  # Flag to control reconnection logic
        self.my_value = None

    def setup_connection(self):
        @self.sio.event
        def connect(): logging.info("Connected to Socket.IO server")

        @self.sio.event
        def disconnect(): logging.info("Disconnected from Socket.IO server")

        @self.sio.on('chat')
        def on_chat(data):
            logging.info(f"Received message: {data}")
            self.my_value = data  # Update my_value with the received data

        try:
            start_time = time.time()  # Capture start time
            self.sio.connect(self.base_url, socketio_path=self.path)  # Make Connection to server
            events.request.fire(
                request_type="SocketIO", name="Connect time",
                response_time=int((time.time() - start_time) * 1000),   # response time in milliseconds
                response_length=0)  # No response length for connect event
 
        except socketio.exceptions.ConnectionError as e:
            logging.error(f"Connection failed: {e}")

    def on_start(self):
        self.setup_connection()

    @task
    def send_message(self):
        if not self.sio.connected and self.should_reconnect:
            logging.info("Client not connected, attempting to reconnect...")
            self.setup_connection()

        if not self.received_response:
            start_time = time.time()
            self.sio.emit(event='query', data=self.message)  # Emit the event to Socket.IO server along with Data

            while not self.received_response:
                self.sio.sleep(1)   # Wait for push messages from server

            events.request.fire(
                request_type="SocketIO", name="Query Time",
                response_time=int((self.end_time - start_time) * 1000),   # response time in milliseconds
                response_length=len(json.dumps(self.my_value)) )

    def on_stop(self):
        if self.sio.connected:
            self.sio.disconnect()


if __name__ == '__main__':
    env = Environment(user_classes=[SocketIOUser])
