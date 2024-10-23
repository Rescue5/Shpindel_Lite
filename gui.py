import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports
import threading
import time
import csv

# Global variables
ser = None
log_file = None
csv_file = None
stop_event = threading.Event()
test_running = threading.Event()
lock = threading.Lock()
log_file_lock = threading.Lock()

def log_to_console(message):
    """Logs messages to the console window."""
    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, message + "\n")
    console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)

def get_available_ports():
    """Returns a list of available COM ports."""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def choose_port():
    """Allows the user to choose a COM port from the dropdown menu."""
    ports = get_available_ports()
    selected_port.set(ports[0] if ports else "Нет доступных портов")
    port_menu.config(values=ports)

def connect_to_port():
    """Connects to the selected COM port and starts reading from it."""
    global ser
    port = selected_port.get()
    try:
        ser = serial.Serial(port, baudrate=115200, timeout=1)
        log_to_console(f"Подключено к {port}")
        stop_event.clear()
        threading.Thread(target=read_serial, daemon=True).start()  # Start reading from serial
    except serial.SerialException as e:
        log_to_console(f"Не удалось подключиться к {port}: {e}")

def read_serial():
    """Постоянно читает данные из COM-порта и выводит их в консоль. Также логирует данные, если тест запущен."""
    global log_file, csv_file

    while not stop_event.is_set():
        if ser is not None and ser.is_open:
            try:
                if ser.in_waiting > 0:
                    with lock:
                        try:
                            data = ser.readline().decode('utf-8').strip()
                        except UnicodeDecodeError:
                            log_to_console("Не удалось декодировать данные.")
                            continue

                    if data:
                        log_to_console(data)  # Выводим данные в консоль

                        # Записываем в лог-файл, если тест запущен
                        if test_running.is_set() and log_file and csv_file:
                            with log_file_lock:
                                try:
                                    with open(log_file, 'a') as lf:
                                        lf.write(data + '\n')
                                except Exception as e:
                                    log_to_console(f"Ошибка записи в лог-файл: {e}")

            except serial.SerialException as e:
                log_to_console(f"Ошибка чтения из COM-порта: {e}")
                time.sleep(1)
        else:
            time.sleep(1)  # Ждем подключения

def log_to_file(data):
    """Logs data to both text and CSV files."""
    if propeller_name:
        with open(f"{propeller_name}.log", "a") as log_file:
            log_file.write(data + "\n")
        with open(f"{propeller_name}.csv", "a", newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), data])

def start_logging():
    """Starts the logging process."""
    global propeller_name, log_file, csv_file
    propeller_name = propeller_entry.get()
    if propeller_name:
        log_to_console(f"Логирование для пропеллера {propeller_name} начато.")
        log_file = f"{propeller_name}.log"
        csv_file = f"{propeller_name}.csv"
        test_running.set()  # Устанавливаем флаг, что тест запущен
    else:
        log_to_console("Введите имя пропеллера!")

def stop_logging():
    """Stops the logging process."""
    test_running.clear()
    stop_event.set()
    log_to_console("Логирование остановлено.")

# GUI setup
root = tk.Tk()
root.title("Упрощенная программа для стенда")
root.geometry("600x400")

main_frame = ttk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Propeller name input
ttk.Label(main_frame, text="Введите имя пропеллера:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
propeller_entry = ttk.Entry(main_frame)
propeller_entry.grid(row=0, column=1, padx=10, pady=5, sticky='ew')

# COM port selection
selected_port = tk.StringVar()
choose_port_button = ttk.Button(main_frame, text="Обновить список портов", command=choose_port)
choose_port_button.grid(row=1, column=0, padx=10, pady=5)

port_menu = ttk.Combobox(main_frame, textvariable=selected_port)
port_menu.grid(row=1, column=1, padx=10, pady=5, sticky='ew')

# Connect button
connect_button = ttk.Button(main_frame, text="Подключиться", command=connect_to_port)
connect_button.grid(row=2, column=0, columnspan=2, padx=10, pady=5)

# Start/Stop buttons for logging
start_button = ttk.Button(main_frame, text="Начать логирование", command=start_logging)
start_button.grid(row=3, column=0, padx=10, pady=5)

stop_button = ttk.Button(main_frame, text="Остановить логирование", command=stop_logging)
stop_button.grid(row=3, column=1, padx=10, pady=5)

# Console output
console_output = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, width=60, state=tk.DISABLED)
console_output.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

# Configuring row/column resizing
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(4, weight=1)

# Run the GUI
root.protocol("WM_DELETE_WINDOW", lambda: (stop_logging(), root.quit()))
root.mainloop()