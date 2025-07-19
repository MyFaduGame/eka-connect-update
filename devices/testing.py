# Updated MQTTDataProcessor
import os
import sys
import signal
import time
import logging
import paho.mqtt.client as mqtt
import pandas as pd
from datetime import datetime
from django.utils import timezone
from typing import Optional
from dotenv import load_dotenv
import cantools

from devices.models import Device, ExtraDevice, MQTTData

load_dotenv()

class MQTTDataProcessor:
    def __init__(self, config: dict):
        self.config = config
        self.running = True
        self.setup_logging()
        self.setup_mqtt_client()
        self.seen_devices = set()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def setup_logging(self):
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('mqtt_processor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_mqtt_client(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        if self.config.get('username') and self.config.get('password'):
            self.client.username_pw_set(self.config['username'], self.config['password'])

    def signal_handler(self, signum, frame):
        self.logger.info("Shutdown signal received. Cleaning up...")
        self.running = False
        self.disconnect()
        sys.exit(0)

    def connect(self):
        try:
            self.client.connect(self.config['broker_host'], self.config['broker_port'], keepalive=60)
        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
            return False
        return True

    def disconnect(self):
        self.client.disconnect()
        self.client.loop_stop()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            self.client.subscribe(self.config['topic'])
        else:
            self.logger.error(f"Connection failed with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.logger.warning("Disconnected from MQTT broker")
        if rc != 0 and self.running:
            self.logger.info("Attempting to reconnect...")
            self.connect()

    def extract_device_id(self, message: str) -> Optional[str]:
        try:
            parts = message.split(',')
            if len(parts) >= 7:
                return parts[6]
            else:
                self.logger.warning("Malformed message: missing device ID")
                return None
        except Exception as e:
            self.logger.error(f"Error extracting device ID: {e}")
            return None

    def load_dbc_file(self, device_type: str):
        try:
            dbc_path = self.config['dbc_paths'].get(device_type)
            if not dbc_path or not os.path.exists(dbc_path):
                self.logger.error(f"DBC file not found for type: {device_type}")
                return None
            return cantools.database.load_file(dbc_path)
        except Exception as e:
            self.logger.error(f"Failed to load DBC file for {device_type}: {e}")
            return None

    def decode_can_data(self, can_section: str, dbc_file) -> dict:
        can_data_json = {}
        try:
            if not can_section or not dbc_file:
                return {}

            can_data_list = can_section.split('|')
            can_ids = list(range(0x800, 0x800 + len(can_data_list)))

            for idx, hex_data in enumerate(can_data_list):
                try:
                    if hex_data in ['N', '']:
                        continue
                    can_id = can_ids[idx]
                    can_data_bytes = bytes.fromhex(hex_data)
                    decoded = dbc_file.decode_message(can_id, can_data_bytes)
                    can_data_json.update(decoded)
                except Exception as decode_err:
                    self.logger.warning(f"CAN decode error at ID {hex(can_id)}: {decode_err}")

        except Exception as e:
            self.logger.error(f"CAN decoding failed: {e}")
        return can_data_json

    def on_message(self, client, userdata, msg):
        try:
            message = msg.payload.decode()
            self.logger.debug(f"Message received: {message}")
            device_id = self.extract_device_id(message)

            if not device_id:
                return

            try:
                device_obj = Device.objects.get(device_id=device_id)
            except Device.DoesNotExist:
                ExtraDevice.objects.get_or_create(device_id=device_id)
                self.logger.info(f"Unknown device stored to ExtraDevice: {device_id}")
                return

            device_obj.is_connected = True
            device_obj.last_seen = timezone.now()
            device_obj.save()

            dbc_file = self.load_dbc_file(device_obj.device_type)
            if not dbc_file:
                return

            parts = message.split(',')
            can_section = "-"
            try:
                can_section = parts[52].split('CAN|')[1].split('|-')[0]
            except Exception:
                self.logger.warning(f"No CAN section found for device {device_id}")

            can_data = self.decode_can_data(can_section, dbc_file)

            node_info = {
                "timestamp": datetime.now().isoformat(),
                "latitude": float(parts[11]) if parts[11] else None,
                "longitude": float(parts[13]) if parts[13] else None,
                "speed": parts[15],
                "heading": parts[16],
                "altitude": parts[18],
                "imei": device_id
            }

            MQTTData.objects.create(
                device=device_obj,
                timestamp=timezone.now(),
                latitude=node_info["latitude"],
                longitude=node_info["longitude"],
                node_info=node_info,
                can_data=can_data
            )
            self.logger.info(f"Data saved for device: {device_id}")

        except Exception as e:
            self.logger.error(f"Error in message processing: {e}")

    def run(self):
        if self.connect():
            self.client.loop_start()
            while self.running:
                time.sleep(10)
            self.disconnect()
