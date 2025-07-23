#Django Imports
import os
import cantools
import paho.mqtt.client as mqtt
import logging,sys,time, signal
from datetime import datetime
import pandas as pd
from django.utils import timezone
from typing import Optional
from dotenv import load_dotenv
from devices.models import Device, DeviceData, ExtraDevice

# Load environment variables from .env file
load_dotenv()

class MQTTDataProcessor:
    def __init__(self, config: dict):
        self.config = config
        self.setup_logging()
        self.setup_mqtt_client()
        self.running = True
        self.mqtt_data_df = pd.DataFrame()

        self.seen_devices = set()

        # Signal handlers for shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def mark_disconnected_devices(self):
        """
        Mark devices not seen in the current run as disconnected.
        """
        try:
            all_devices = Device.objects.all()
            for device in all_devices:
                if device.device_id not in self.seen_devices:
                    if device.is_connected:  # Only update if currently connected
                        device.is_connected = False
                        device.save()
                        self.logger.info(f"Device marked as disconnected: {device.device_id}")
        except Exception as e:
            self.logger.error(f"Error marking disconnected devices: {e}")

    def setup_logging(self):
        # Configure logging
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

    def extract_lat_long(mqtt_message: str):
        try:
            parts = mqtt_message.split(',')
            # Find index of latitude direction (e.g., 'N') and use it to locate lat/lng values
            for i in range(len(parts)):
                if parts[i] in ['N', 'S'] and parts[i+2] in ['E', 'W']:
                    latitude = float(parts[i - 1])
                    longitude = float(parts[i + 1])
                    # Optionally apply sign based on direction
                    if parts[i] == 'S':
                        latitude = -latitude
                    if parts[i + 2] == 'W':
                        longitude = -longitude
                    return latitude, longitude
            raise ValueError("Latitude/Longitude not found")
        except Exception as e:
            print(f"Error extracting coordinates: {e}")
            return None, None

    def setup_mqtt_client(self):
        """Setup MQTT client and callbacks"""
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Credentials
        if self.config.get('username') and self.config.get('password'):
            self.client.username_pw_set(self.config['username'], self.config['password'])

    def signal_handler(self, signum, frame):
        # Handle shutdown signal
        self.logger.info("Shutdown signal received. Cleaning up...")
        try:
            if not self.mqtt_data_df.empty:
                self.upload_to_s3(self.mqtt_data_df)
            else:
                self.logger.info("No data to save.")
        except Exception as e:
            self.logger.error(f"Error saving final data: {str(e)}")

        self.running = False
        self.disconnect()
        sys.exit(0)

    def extract_device_id(self, message: str) -> Optional[str]:
        try:
            parts = message.split(',')
            if len(parts) >= 7:
                return parts[6]  # 7th element (index 6) is device ID
            else:
                self.logger.warning("Unable to extract device ID - malformed message.")
                return None
        except Exception as e:
            self.logger.error(f"Error extracting device ID: {e}")
            return None

    def parse_message(self, message: str, dbc_file) -> Optional[pd.DataFrame]:
        try:
            device_id = self.extract_device_id(message)
            if device_id is None:
                return None  # Skip message if device ID is missing
            parts = message.split(',')
            timestamp = datetime.now().isoformat()
            
            # Basic structure for known fields
            field_names = [ 
                "header", "vendor_id", "version", "packet_type","alert_id", "packet_status", "IMEI",
                "vehicle_reg_no", "gps_fix", "date", "time",
                "latitude", "latitude_dir", "longitude", "longitude_dir",
                "speed","heading","no_of_stattalites", "altitude", "pdop", "hdop",
                "operator","ignition","main_power_status","main_input_voltage","internal_battery_voltage",
                "emergency_status","temper_alert","gsm_strength", "MCC","MNC","LAC",
                "cell_id"   
            ]

            parsed_data = {
                'timestamp': timestamp,
                'device_id': device_id
            }
            
            parsed_data['NMR'] = parts[33:44]
            parsed_data['digital_input_status'] = parts[45]
            parsed_data['digital_output_status'] = parts[46]
            parsed_data['analog_input_1'] = parts[47]
            parsed_data['analog_input_2'] = parts[48]
            parsed_data['frame_number'] = parts[49]
            parsed_data['odometer'] = parts[50]
            parsed_data['mis_field_1'] = parts[51]
            parsed_data['mis_field_2'] = parts[52]
            parsed_data['mis_field_3'] = parts[53]
            parsed_data['mis_field_4'] = parts[54]
            parsed_data['debug_info'] = parts[56]

            # Fill parsed_data with fixed fields
            for i, field in enumerate(field_names):
                if i < len(parts):
                    if field == 'NMR' or  i >= 33:
                        continue
                    else:
                        parsed_data[field] = parts[i]
                        
            # Extract CAN section
            can_section = ""
            if parsed_data['mis_field_2'] != '-':
                try:
                    can_section = parsed_data['mis_field_2'].split('CAN|')[1].split('|-')[0]
                except IndexError:
                    logging.warning("Malformed CAN section in the message.")

            can_data = can_section.split('|') if can_section else []
            filtered_can_data = [data if data != 'N' and len(data) > 0 else 'N' for data in can_data]
            # CAN IDs
            can_ids = [
                0x800, 0x801, 0x802, 0x803, 0x804, 0x805, 0x806, 0x807, 0x808, 0x809,
                0x810, 0x811, 0x812, 0x813, 0x814, 0x815, 0x816, 0x817, 0x818, 0x819,
                0x820, 0x821, 0x822, 0x823, 0x824, 0x825, 0x826, 0x827, 0x828, 0x829,
                0x830, 0x831, 0x832, 0x833, 0x834, 0x835, 0x836, 0x837, 0x838, 0x839,
                0x840, 0x841, 0x842, 0x843, 0x844, 0x845, 0x850, 0x851, 0x852, 0x853
            ]
            for idx, item in enumerate(filtered_can_data):
                try:
                    if ':' in item:
                        # Format: ['000800:n']
                        hex_str = item.strip()
                        can_id_str, hex_data = hex_str.split(":")
                        can_id = int(can_id_str, 16)
                    else:
                        # Format: ['n', 'AABBCC']
                        can_id = can_ids[idx]
                        hex_data = item.strip()

                    if hex_data.lower() == 'n':
                        for signal in dbc_file.get_message_by_frame_id(can_id).signals:
                            parsed_data[signal.name] = 'N'
                        continue

                    can_data_bytes = bytes.fromhex(hex_data)
                    decoded = dbc_file.decode_message(can_id, can_data_bytes)

                    for signal_name, value in decoded.items():
                        parsed_data[signal_name] = value

                except Exception as e:
                    logging.warning(f"Error decoding CAN ID {hex(can_id)}: {e}")
 
            return pd.DataFrame([parsed_data])

        except Exception as e:
            logging.error(f"Error parsing message: {e}")
            return None

    def on_connect(self, client, userdata, flags, rc):
        """Callback when client connects"""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            self.client.subscribe(self.config['topic'])
        else:
            self.logger.error(f"Connection failed with code {rc}")


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

    def on_message(self, client, userdata, msg):
        # """Callback when a message is received"""
        try:
            message = msg.payload.decode()
            self.logger.debug(f"Received message: {message}")
            device_id = self.extract_device_id(message)
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
            parsed_df = self.parse_message(message, dbc_file=dbc_file)
            if parsed_df is not None:
                device_id = parsed_df.iloc[0]['device_id']
                for _, row in parsed_df.iterrows():
                    try:
                        DeviceData.objects.create(
                            NMR = row.get('NMR'),
                            digital_input_status = row.get('digital_input_status'),
                            digital_output_status = row.get('digital_output_status'),
                            analog_input_1 = row.get('analog_input_1'),
                            analog_input_2 = row.get('analog_input_2'),
                            frame_number = row.get('frame_number'),
                            odometer = row.get('odometer'),
                            debug_info = row.get('debug_info'),
                            timestamp=row.get('timestamp'),
                            device_id=row.get('device_id'),
                            header = row.get("header"),
                            vendor_id = row.get("vendor_id"),
                            version = row.get("version"),
                            packet_type = row.get("packet_type"),
                            alert_id = row.get("alert_id"),
                            packet_status = row.get("packet_status"),
                            IMEI = row.get("IMEI"),
                            vehicle_reg_no = row.get("vehicle_reg_no"),
                            gps_fix = row.get("gps_fix"),
                            date = row.get("date"),
                            time = row.get("time"),
                            latitude = row.get("latitude"),
                            latitude_dir = row.get("latitude_dir"),
                            longitude = row.get("longitude"),
                            longitude_dir = row.get("longitude_dir"),
                            speed = row.get("speed"),
                            heading = row.get("heading"),
                            no_of_stattalites = row.get("no_of_stattalites"),
                            altitude = row.get("altitude"),
                            pdop = row.get("pdop"),
                            hdop = row.get("hdop"),
                            operator = row.get("operator"),
                            ignition = row.get("ignition"),
                            main_power_status = row.get("main_power_status"),
                            main_input_voltage = row.get("main_input_voltage"),
                            internal_battery_voltage = row.get("internal_battery_voltage"),
                            emergency_status = row.get("emergency_status"),
                            temper_alert = row.get("temper_alert"),
                            gsm_strength = row.get("gsm_strength"),
                            MCC = row.get("MCC"),
                            MNC = row.get("MNC"),
                            LAC = row.get("LAC"),
                            cell_id = row.get("cell_id"), #have to check Tire_Location_
                            extra_data = {},
                            can_data = {
                                key: row.get(key)
                                for key in row.index
                                if key not in [
                                    'timestamp', 'device_id', 'latitude', 'longitude',
                                    'Tire_Location_', 'ODOMETER', 'heading', 'NMR',
                                    'digital_input_status', 'digital_output_status',
                                    'analog_input_1', 'analog_input_2', 'frame_number',
                                    'odometer', "debug_info", 'latitude_dir', 'longitude_dir',
                                    'mis_field_1', 'mis_field_2', 'mis_field_3', 'mis_field_4',
                                    'header', 'vendor_id', 'version', 'packet_type', 'alert_id',
                                    'packet_status', 'IMEI', 'vehicle_reg_no', 'gps_fix', 'date',
                                    'time', 'speed', 'no_of_stattalites', 'altitude', 'pdop',
                                    'hdop', 'operator', 'ignition', 'main_power_status',
                                    'main_input_voltage', 'internal_battery_voltage',
                                    'emergency_status', 'temper_alert', 'gsm_strength',
                                    'MCC', 'MNC', 'LAC', 'cell_id'
                                ]
                            }
                        )
                        self.logger.info("Trying addingf the data")
                    except Exception as db_err:
                        self.logger.error(f"Error saving to DB for device {device_id} {row}: {db_err}")

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")


    def on_disconnect(self, client, userdata, rc):
        """Callback when client disconnects"""
        self.logger.warning("Disconnected from MQTT broker")
        if rc != 0 and self.running:
            self.logger.info("Attempting to reconnect...")
            self.connect()

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

    def run(self):
        """Main run loop"""
        if self.connect():
            self.client.loop_start()
            while self.running:
                time.sleep(10)  # Check connection status every 10 sec or adjust as needed

                # Check for devices that have not sent data recently
                self.mark_disconnected_devices()

            self.disconnect()

def main():
    config = {
        'broker_host': '43.204.176.28',
        'broker_port': 1883,
        'topic': 'devicedata/#',
        'username': 'EKA',
        'password': 'EKA@123',
        'dbc_paths': {
            '3w': 'dbcs/3w.dbc',
            '4w': 'dbcs/4w.dbc',
        }
    }

    processor = MQTTDataProcessor(config)
    processor.run()

# def main():
#     # Load DBC file
#     # dbc_path = "EKA_VTS_DBC_271224 2.dbc"
#     dbc_path = "mqtt_processor/sample.dbc"
#     dbc_file = cantools.database.load_file(dbc_path)
    
#     config = {
#         'broker_host': '43.204.176.28',
#         'broker_port': 1883,
#         'topic': 'devicedata/#',
#         'username': 'EKA',
#         'password': 'EKA@123',
#         'dbc_file': dbc_file,
#     }

#     processor = MQTTDataProcessor(config)
#     processor.run()

# if __name__ == "__main__":
#     main()