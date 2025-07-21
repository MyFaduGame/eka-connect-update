#Django Imports
import paho.mqtt.client as mqtt
import json, logging,sys,os, time, signal, cantools, boto3, tempfile
from datetime import datetime
import pandas as pd
from django.utils import timezone
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from typing import Optional
from dotenv import load_dotenv

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

        # Setup AWS S3 client using environment variables
        # self.s3_client = boto3.client(
        #     's3',
        #     aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        #     aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        #     region_name=os.getenv('AWS_REGION')
        # )
        # self.bucket_name = os.getenv('S3_BUCKET_NAME')

        # Signal handlers for shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    # def check_device_connectivity(self, device_ids: list, timeout_per_device: int = 10):
    #     responsive_devices_data = []
    #     non_responsive_devices = []

    #     received_flags = {device_id: False for device_id in device_ids}
    #     self.temp_device_data = {}

    #     def custom_on_message(client, userdata, msg):
    #         try:
    #             message = msg.payload.decode()
    #             device_id = self.extract_device_id(message)
    #             if device_id in device_ids:
    #                 parsed_df = self.parse_message(message, dbc_file=self.config['dbc_file'])
    #                 if parsed_df is not None:
    #                     responsive_devices_data.append(parsed_df)
    #                     received_flags[device_id] = True
    #         except Exception as e:
    #             self.logger.error(f"[CheckConnectivity] Error: {e}")

    #     # Temporarily override on_message to catch only relevant messages
    #     original_on_message = self.client.on_message
    #     self.client.on_message = custom_on_message

    #     # Connect if not already connected
    #     if not self.connect():
    #         self.logger.error("Cannot start device connectivity check due to connection failure.")
    #         return

    #     self.client.loop_start()

    #     for device_id in device_ids:
    #         topic = f"{self.config['topic'].split('/')[0]}/{device_id}"
    #         self.logger.info(f"Subscribing to topic: {topic}")
    #         self.client.subscribe(topic)

    #         start_time = time.time()
    #         while time.time() - start_time < timeout_per_device:
    #             if received_flags[device_id]:
    #                 break
    #             time.sleep(1)

    #         if not received_flags[device_id]:
    #             non_responsive_devices.append(device_id)
    #         self.client.unsubscribe(topic)

    #     # Restore original on_message handler
    #     self.client.on_message = original_on_message
    #     self.client.loop_stop()

    #     # Save responsive device data
    #     if responsive_devices_data:
    #         full_df = pd.concat(responsive_devices_data, ignore_index=True)
    #         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    #         full_df.to_csv(f"mqtt_processor/csv/responsive_devices_{timestamp}.csv", index=False)
    #         self.logger.info("Saved responsive device data.")

    #     # Save non-responsive device list
    #     if non_responsive_devices:
    #         pd.DataFrame(non_responsive_devices, columns=["device_id"]).to_csv(
    #             f"mqtt_processor/csv/non_responsive_devices_{timestamp}.csv", index=False
    #         )
    #         self.logger.warning("Saved non-responsive device list.")

    def mark_disconnected_devices(self):
        """
        Mark devices not seen in the current run as disconnected.
        """
        try:
            pass
            # all_devices = Device.objects.all()
            # for device in all_devices:
            #     if device.device_id not in self.seen_devices:
            #         if device.is_connected:  # Only update if currently connected
            #             device.is_connected = False
            #             device.save()
            #             self.logger.info(f"Device marked as disconnected: {device.device_id}")
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
            print(device_id,'--->')
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
            print(filtered_can_data)
            # CAN IDs
            can_ids = [
                0x800, 0x801, 0x802, 0x803, 0x804, 0x805, 0x806, 0x807, 0x808, 0x809,
                0x810, 0x811, 0x812, 0x813, 0x814, 0x815, 0x816, 0x817, 0x818, 0x819,
                0x820, 0x821, 0x822, 0x823, 0x824, 0x825, 0x826, 0x827, 0x828, 0x829,
                0x830, 0x831, 0x832, 0x833, 0x834, 0x835, 0x836, 0x837, 0x838, 0x839,
                0x840, 0x841, 0x842, 0x843, 0x844, 0x845, 0x850, 0x851, 0x852, 0x853
            ]
            can_dict = {}
            for idx, hex_data in enumerate(filtered_can_data):
                try:
                    can_id = can_ids[idx]
                    print(idx,hex_data,'-->')
                    if hex_data == 'N':
                        for signal in dbc_file.get_message_by_frame_id(can_id).signals:
                            parsed_data[signal.name] = 'N'
                        continue

                    can_data_bytes = bytes.fromhex(hex_data)
                    decoded = dbc_file.decode_message(can_id, can_data_bytes)

                    for signal_name, value in decoded.items():
                        parsed_data[signal_name] = value
                        can_dict[signal_name] = value

                except Exception as e:
                    logging.warning(f"Error decoding CAN ID {hex(can_id)}: {e}")
            return pd.DataFrame([parsed_data]),can_dict

        except Exception as e:
            logging.error(f"Error parsing message: {e}")
            return None


    # def parse_message(self, message: str, dbc_file) -> Optional[pd.DataFrame]:
    #     try:
    #         device_id = self.extract_device_id(message)
    #         if device_id is None:
    #             return None  # Skip message if device ID is missing

    #         parts = message.split(',')
    #         print(parts)
    #         can_section = ""
    #         if 'CAN|' in message:
    #             try:
    #                 can_section = message.split('CAN|')[1].split('|-')[0]
    #             except IndexError:
    #                 logging.warning("Malformed CAN section in the message.")

    #         can_data = can_section.split('|') if can_section else []
    #         filtered_can_data = [data if data != 'N' and len(data) > 0 else 'N' for data in can_data]

    #         timestamp = datetime.now().isoformat()
    #         parsed_data = {
    #             'timestamp': timestamp,
    #             'device_id': device_id
    #         }

    #         # Extract latitude and longitude
    #         try:
    #             for i in range(len(parts)):
    #                 if parts[i] in ['N', 'S'] and parts[i+2] in ['E', 'W']:
    #                     lat_str = parts[i - 1]
    #                     lng_str = parts[i + 1]
    #                     lat = float(lat_str)
    #                     lng = float(lng_str)
    #                     if parts[i] == 'S':
    #                         lat = -lat
    #                     if parts[i + 2] == 'W':
    #                         lng = -lng
    #                     parsed_data['latitude'] = lat
    #                     parsed_data['longitude'] = lng
    #                     break
    #         except Exception as e:
    #             logging.warning(f"Error extracting GPS coordinates: {e}")
    #             parsed_data['latitude'] = None
    #             parsed_data['longitude'] = None

    #         # List of CAN IDs
    #         can_ids = [
    #             0x800, 0x801, 0x802, 0x803, 0x804, 0x805, 0x806, 0x807, 0x808, 0x809,
    #             0x810, 0x811, 0x812, 0x813, 0x814, 0x815, 0x816, 0x817, 0x818, 0x819,
    #             0x820, 0x821, 0x822, 0x823, 0x824, 0x825, 0x826, 0x827, 0x828, 0x829,
    #             0x830, 0x831, 0x832, 0x833, 0x834, 0x835, 0x836, 0x837, 0x838, 0x839,
    #             0x840, 0x841, 0x842, 0x843, 0x844, 0x845, 0x850, 0x851, 0x852, 0x853
    #         ]

    #         for idx, hex_data in enumerate(filtered_can_data):
    #             try:
    #                 can_id = can_ids[idx]
    #                 if hex_data == 'N':
    #                     for signal in dbc_file.get_message_by_frame_id(can_id).signals:
    #                         parsed_data[signal.name] = 'N'
    #                     continue

    #                 can_data_bytes = bytes.fromhex(hex_data)
    #                 decoded = dbc_file.decode_message(can_id, can_data_bytes)

    #                 for signal_name, value in decoded.items():
    #                     parsed_data[signal_name] = value

    #             except Exception as e:
    #                 logging.warning(f"Error decoding CAN ID {hex(can_id)}: {e}")

    #         return pd.DataFrame([parsed_data])

    #     except Exception as e:
    #         logging.error(f"Error parsing message: {e}")
    #         return None


    # def parse_message(self, message: str, dbc_file) -> Optional[pd.DataFrame]:
    #     try:
    #         device_id = self.extract_device_id(message)
    #         if device_id is None:
    #             return None  # Skip message if device ID is missing

    #         parts = message.split(',')
    #         can_section = ""
    #         if 'CAN|' in message:
    #             try:
    #                 can_section = message.split('CAN|')[1].split('|-')[0]
    #             except IndexError:
    #                 logging.warning("Malformed CAN section in the message.")

    #         can_data = can_section.split('|') if can_section else []
    #         filtered_can_data = [data if data != 'N' and len(data) > 0 else 'N' for data in can_data]

    #         timestamp = datetime.now().isoformat()
    #         parsed_data = {
    #             'timestamp': timestamp,
    #             'device_id': device_id}

    #         can_ids = [0x800, 0x801, 0x802, 0x803, 0x804, 0x805, 0x806, 0x807, 0x808, 0x809,
    #                    0x810, 0x811, 0x812, 0x813, 0x814, 0x815, 0x816, 0x817, 0x818, 0x819,
    #                    0x820, 0x821, 0x822, 0x823, 0x824, 0x825, 0x826, 0x827, 0x828, 0x829,
    #                    0x830, 0x831, 0x832, 0x833, 0x834, 0x835, 0x836, 0x837, 0x838, 0x839,
    #                    0x840 ,0x841, 0x842, 0x843, 0x844, 0x845, 0x850, 0x851, 0x852, 0x853]

    #         for idx, hex_data in enumerate(filtered_can_data):
    #             try:
    #                 can_id = can_ids[idx]
    #                 if hex_data == 'N':
    #                     for signal in dbc_file.get_message_by_frame_id(can_id).signals:
    #                         parsed_data[signal.name] = 'N'
    #                     continue

    #                 can_data_bytes = bytes.fromhex(hex_data)  # hex string to bytes
    #                 decoded = dbc_file.decode_message(can_id, can_data_bytes)

    #                 for signal_name, value in decoded.items():
    #                     parsed_data[signal_name] = value

    #             except Exception as e:
    #                 logging.warning(f"Error decoding CAN ID {hex(can_id)}: {e}")

    #         df = pd.DataFrame([parsed_data])
    #         return df

    #     except Exception as e:
    #         logging.error(f"Error parsing message: {e}")
    #         return None

    def upload_to_s3(self, data_frame: pd.DataFrame):
        # """Upload processed data to AWS S3"""
        # try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"mqtt_processor/csv/mqtt_data_{timestamp}.csv"
            # file_path =  os.path.join(tempfile.gettempdir(), filename)  # Local temporary path before uploading

            # Save the DataFrame to CSV file locally
            data_frame.to_csv(filename, index=False)
            # self.logger.info(f"Uploading data to S3 bucket: {self.bucket_name}")

            # Upload file to S3
            # self.s3_client.upload_file(file_path, self.bucket_name, filename)
            # self.logger.info(f"Successfully uploaded {filename} to S3 bucket {self.bucket_name}")

            # # Clean up temporary local file
            # os.remove(file_path)
        # except NoCredentialsError:
        #     self.logger.error("AWS credentials not found.")
        # except PartialCredentialsError:
        #     self.logger.error("Incomplete AWS credentials.")
        # except Exception as e:
        #     self.logger.error(f"Error uploading data to S3: {str(e)}")

    def on_connect(self, client, userdata, flags, rc):
        """Callback when client connects"""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            self.client.subscribe(self.config['topic'])
        else:
            self.logger.error(f"Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        """Callback when a message is received"""
        try:
            message = msg.payload.decode()
            self.logger.debug(f"Received message: {message}")

            parsed_df,can_dict = self.parse_message(message, dbc_file=self.config['dbc_file'])
            print(can_dict,'--->')
            # if parsed_df is not None:
            #     device_id = parsed_df.iloc[0]['device_id']
                
            #     # self.seen_devices.add(device_id)

            #     # # device_obj, created = Device.objects.update_or_create(
            #     # #     device_id=device_id,
            #     # #     defaults={
            #     # #         'is_connected': True,
            #     # #         'last_seen': timezone.now(),
            #     # #     }
            #     # # )

            #     # if created:
            #     #     self.logger.info(f"New device added: {device_id}")
            #     # else:
            #     #     self.logger.info(f"Updated device last_seen: {device_id}")

            #     # # Save each row of parsed_df to the DB
            #     # for _, row in parsed_df.iterrows():
            #     #     try:
            #     #         MQTTData.objects.create(
            #     #             NMR = row.get('NMR'),
            #     #             digital_input_status = row.get('digital_input_status'),
            #     #             digital_output_status = row.get('digital_output_status'),
            #     #             analog_input_1 = row.get('analog_input_1'),
            #     #             analog_input_2 = row.get('analog_input_2'),
            #     #             frame_number = row.get('frame_number'),
            #     #             odometer = row.get('odometer'),
            #     #             debug_info = row.get('debug_info'),
            #     #             timestamp=row.get('timestamp'),
            #     #             device_id=row.get('device_id'),
            #     #             latitude=row.get('latitude'),
            #     #             latitude_dir=row.get('latitude_dir'),
            #     #             longitude=row.get('longitude'),
            #     #             longitude_dir=row.get('longitude_dir'),
            #     #             heading = row.get('heading'),
            #     #             Tire_Location = row.get('Tire_Location_'),
            #     #             **{
            #     #                 key: row[key]
            #     #                 for key in row.index
            #     #                 if key not in ['timestamp', 'device_id', 'latitude', 'longitude',
            #     #                                'Tire_Location_','ODOMETER','heading','NMR',
            #     #                                'digital_input_status','digital_output_status',
            #     #                                'analog_input_1','analog_input_2','frame_number',
            #     #                                'odometer',"debug_info",'latitude_dir','longitude_dir',
            #     #                                'mis_field_1', 'mis_field_2', 'mis_field_3', 
            #     #                                'mis_field_4']
            #     #             }
            #     #         )
            #     #         self.logger.info("Trying addingf the data")
            #     #     except Exception as db_err:
            #     #         self.logger.error(f"Error saving to DB for device {device_id} {row}: {db_err}")

            # if parsed_df is not None:
            #     device_id = parsed_df.iloc[0]['device_id']

            #     # Add device_id to the seen set
            #     self.seen_devices.add(device_id)

            #     # Update or create Device in DB
            #     device_obj, created = Device.objects.update_or_create(
            #         device_id=device_id,
            #         defaults={
            #             'is_connected': True,
            #             'last_seen': timezone.now(),
            #         }
            #     )
            #     if created:
            #         self.logger.info(f"New device added: {device_id}")
            #     else:
            #         self.logger.info(f"Updated device last_seen: {device_id}")

            #     # Append and handle data
            #     self.mqtt_data_df = pd.concat([self.mqtt_data_df, parsed_df], ignore_index=True)
            #     self.logger.info(f"Appended new data. Current DataFrame shape: {self.mqtt_data_df.shape}")

            #     # Upload data to S3 after accumulating 10 messages
            #     if len(self.mqtt_data_df) % 10 == 0:
            #         # self.upload_to_s3(self.mqtt_data_df)
            #         self.mqtt_data_df = pd.DataFrame()  # Reset dataframe after upload

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")


    # def on_message(self, client, userdata, msg):
    #     """Callback when a message is received"""
    #     try:
    #         message = msg.payload.decode()
    #         self.logger.debug(f"Received message: {message}")

    #         parsed_df = self.parse_message(message, dbc_file=self.config['dbc_file'])
    #         if parsed_df is not None:
    #             # Merge with existing data, keeping only the latest timestamp row
    #             self.mqtt_data_df = pd.concat([self.mqtt_data_df, parsed_df], ignore_index=True)
    #             self.logger.info(f"Appended new data. Current DataFrame shape: {self.mqtt_data_df.shape}")

    #             # Upload data to S3 after accumulating 10 messages
    #             if len(self.mqtt_data_df) % 10 == 0:
    #                 self.upload_to_s3(self.mqtt_data_df)
    #                 self.mqtt_data_df = pd.DataFrame()  # Reset dataframe after upload

    #     except Exception as e:
    #         self.logger.error(f"Error processing message: {str(e)}")

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
        # if self.connect():
        #     self.client.loop_start()
        #     while self.running:
        #         time.sleep(1)
        #     self.disconnect()


def main():
    # Load DBC file
    # dbc_path = "EKA_VTS_DBC_271224 2.dbc"
    dbc_path = "dbcs/4w.dbc"
    dbc_file = cantools.database.load_file(dbc_path)
    
    config = {
        'broker_host': '43.204.176.28',
        'broker_port': 1883,
        'topic': 'devicedata/#',
        'username': 'EKA',
        'password': 'EKA@123',
        'dbc_file': dbc_file,
    }

    processor = MQTTDataProcessor(config)
    processor.run()

# if __name__ == "__main__":
#     main()