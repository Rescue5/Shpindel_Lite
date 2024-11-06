import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import threading
import time
import csv
import os
from PIL import Image, ImageTk

# Global variables
ser = None
log_file = None
csv_file = None
stop_event = threading.Event()
test_running = threading.Event()
lock = threading.Lock()
log_file_lock = threading.Lock()
stand_name = "пропеллер"  # Пример типа стенда


def write_to_log_file(message):
    """Записывает сообщение в лог-файл, если логирование активно."""
    if log_file and test_running.is_set():  # Проверка, активен ли процесс логирования
        with log_file_lock:
            with open(log_file, 'a') as f:
                f.write(message + "\n")


def log_to_console(message):
    """Logs messages to the console window and log file."""
    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, message + "\n")
    console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)
    write_to_log_file(message)


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
        threading.Thread(target=read_serial, daemon=True).start()
    except serial.SerialException as e:
        log_to_console(f"Не удалось подключиться к {port}: {e}")


def read_serial():
    """Читает данные из COM-порта и выводит их в консоль."""
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
                        log_to_console(data)
                        parse_and_save_to_csv(data)
            except serial.SerialException as e:
                log_to_console(f"Ошибка чтения из COM-порта: {e}")
                time.sleep(1)
        else:
            time.sleep(1)


def parse_and_save_to_csv(data):
    """Парсит строку и записывает данные в CSV файл."""
    if data.startswith("Момент:"):
        parts = data.split(":")
        try:
            moment = float(parts[1].strip())
            thrust = float(parts[3].strip())
            rpm = float(parts[5].strip())

            write_headers = False
            if test_running.is_set() and csv_file:
                if not os.path.exists(csv_file):
                    write_headers = True
                elif os.path.getsize(csv_file) == 0:
                    write_headers = True

                with log_file_lock:
                    with open(csv_file, 'a', newline='') as csvfile:
                        csv_writer = csv.writer(csvfile, delimiter=';')
                        if write_headers:
                            csv_writer.writerow(["Moment", "Thrust", "RPM"])
                        csv_writer.writerow([moment, thrust, rpm])

        except (IndexError, ValueError) as e:
            log_to_console(f"Ошибка парсинга данных: {data} | Ошибка: {e}")


def confirm_overwrite():
    """Shows a confirmation dialog for overwriting existing files."""
    return messagebox.askyesno("Подтверждение перезаписи", "Файлы с этим именем уже существуют. Перезаписать их?")


def start_logging():
    """Starts the logging process."""
    global log_file, csv_file
    propeller_name = propeller_entry.get()
    if propeller_name:
        log_file = f"{propeller_name}.log"
        csv_file = f"{propeller_name}.csv"

        if os.path.exists(log_file) or os.path.exists(csv_file):
            # Запрашиваем подтверждение перезаписи
            if confirm_overwrite():
                open(log_file, 'w').close()
                open(csv_file, 'w').close()
                log_to_console(f"Файлы для {propeller_name} перезаписаны.")
            else:
                log_to_console("Перезапись отменена.")
                return  # Выходим, если отказались от перезаписи

        else:
            open(log_file, 'w').close()
            open(csv_file, 'w').close()

        log_to_console(f"Логирование для пропеллера {propeller_name} начато.")
        test_running.set()
    else:
        log_to_console("Введите имя пропеллера!")


def stop_logging():
    """Stops the logging process."""
    test_running.clear()
    log_to_console("Логирование остановлено.")


# GUI setup
root = tk.Tk()
root.title("Тестирование")
root.geometry("800x400")

main_frame = ttk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Frame for inputs and buttons
input_frame = ttk.Frame(main_frame)
input_frame.grid(row=0, column=0, padx=10, pady=10, sticky='ew')

# Propeller name input
ttk.Label(input_frame, text="Введите имя пропеллера:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
propeller_entry = ttk.Entry(input_frame)
propeller_entry.grid(row=0, column=1, padx=10, pady=5, sticky='ew')

# COM port selection
selected_port = tk.StringVar()
choose_port_button = ttk.Button(input_frame, text="Обновить список портов", command=choose_port)
choose_port_button.grid(row=1, column=0, padx=10, pady=5)

port_menu = ttk.Combobox(input_frame, textvariable=selected_port)
port_menu.grid(row=1, column=1, padx=10, pady=5, sticky='ew')

# Connect button
connect_button = ttk.Button(input_frame, text="Подключиться", command=connect_to_port)
connect_button.grid(row=2, column=0, columnspan=2, padx=10, pady=5)

# Start/Stop buttons for logging
start_button = ttk.Button(input_frame, text="Начать логирование", command=start_logging)
start_button.grid(row=3, column=0, padx=10, pady=5)

stop_button = ttk.Button(input_frame, text="Остановить логирование", command=stop_logging)
stop_button.grid(row=3, column=1, padx=10, pady=5)

# Console output
console_output = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, state=tk.DISABLED)
console_output.grid(row=1, column=0, padx=10, pady=10, sticky='nsew', columnspan=2)

# Load and display image
try:
    image = Image.open("dron_motors.png")  # Загрузите изображение
    image = image.resize((250, 100), Image.Resampling.LANCZOS)
    logo_photo = ImageTk.PhotoImage(image)
    logo_label = tk.Label(main_frame, image=logo_photo)
    logo_label.grid(row=0, column=1, padx=10, pady=5, sticky='ne')  # Позиционируем картинку
except FileNotFoundError:
    print("Изображение 'dron_motors.png' не найдено.")

# Configuring row/column resizing
main_frame.columnconfigure(0, weight=1)
main_frame.rowconfigure(1, weight=1)

# Run the GUI
root.protocol("WM_DELETE_WINDOW", lambda: (stop_logging(), root.quit()))
root.mainloop()