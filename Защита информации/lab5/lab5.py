import hashlib
import os
import subprocess
import sys


def compute_sha256(file_name):
    """Вычисляет SHA256 хеш файла"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_name, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"Ошибка при чтении файла {file_name}: {e}")
        return None


def get_test_files():
    """Получает список тестовых файлов (1.txt - 10.txt)"""
    files = []
    for i in range(1, 11):
        filename = f"{i}.txt"
        if os.path.exists(filename):
            files.append(filename)
    return files


def save_hashes(file_hashes, filename):
    """Сохраняет хеши в файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        for file_name in sorted(file_hashes.keys(), key=lambda x: int(x.split('.')[0])):
            f.write(f"{file_name} - {file_hashes[file_name]}\n")


def load_virus_hashes(filename):
    """Загружает список вирусных хешей из файла"""
    virus_hashes = set()
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    virus_hashes.add(line.upper())
    return virus_hashes


def main():
    print("=== Антивирусная программа hash-scan ===\n")

    print("Шаг 1: Вычисление исходных хеш-сумм файлов...")
    test_files = get_test_files()

    if not test_files:
        print("Тестовые файлы не найдены!")
        return

    origin_hashes = {}
    for file_name in test_files:
        file_hash = compute_sha256(file_name)
        if file_hash:
            origin_hashes[file_name] = file_hash
            print(f"  {file_name}: {file_hash}")

    print("\nШаг 2: Сохранение хеш-сумм в HashList.txt...")
    save_hashes(origin_hashes, "HashList.txt")
    print("  Хеши сохранены в HashList.txt")

    print("\nШаг 3: Запуск тестовой программы FC...")
    fc_program = None
    if os.path.exists("FC.exe"):
        fc_program = "FC.exe"
    elif os.path.exists("FC"):
        fc_program = "./FC"

    if fc_program:
        try:
            if os.name == 'nt':
                subprocess.run([fc_program], check=False)
            else:  # Linux
                subprocess.run([fc_program], check=False)
            print("  Программа FC выполнена")
        except Exception as e:
            print(f"  Предупреждение: Не удалось запустить FC: {e}")
    else:
        print("  Предупреждение: Программа FC не найдена")

    print("\nШаг 4: Вычисление хеш-сумм после изменений...")
    new_hashes = {}
    for file_name in test_files:
        if os.path.exists(file_name):
            file_hash = compute_sha256(file_name)
            if file_hash:
                new_hashes[file_name] = file_hash

    print("\nШаг 5: Загрузка списка вирусных хешей...")
    virus_hashes = load_virus_hashes("VirusHashList.txt")
    print(f"  Загружено {len(virus_hashes)} вирусных хешей")

    print("\nШаг 6: Анализ файлов...")
    changed_files = {}
    infected_files = {}

    for file_name in test_files:
        if file_name in new_hashes:
            if file_name in origin_hashes and new_hashes[file_name] != origin_hashes[file_name]:
                changed_files[file_name] = new_hashes[file_name]

            if new_hashes[file_name].upper() in virus_hashes:
                infected_files[file_name] = new_hashes[file_name]

    print("\n=== РЕЗУЛЬТАТЫ ПРОВЕРКИ ===")

    if changed_files:
        print(f"\nИзмененные файлы ({len(changed_files)}):")
        for file_name in sorted(changed_files.keys(), key=lambda x: int(x.split('.')[0])):
            print(f"  - {file_name}")
    else:
        print("\nИзмененные файлы: не обнаружено")

    if infected_files:
        print(f"\nЗараженные файлы ({len(infected_files)}):")
        for file_name in sorted(infected_files.keys(), key=lambda x: int(x.split('.')[0])):
            print(f"  - {file_name}")
    else:
        print("\nЗараженные файлы: не обнаружено")

    deleted_files = []
    user_decision = "нет"

    if infected_files:
        print("\n" + "=" * 50)
        while True:
            user_input = input("Удалить зараженные файлы? (да/нет): ").strip().lower()
            if user_input in ['да', 'yes', 'y', 'д']:
                user_decision = "да"
                print("\nУдаление зараженных файлов...")
                for file_name in infected_files:
                    try:
                        os.remove(file_name)
                        deleted_files.append(file_name)
                        print(f"Удален: {file_name}")
                    except Exception as e:
                        print(f"Ошибка при удалении {file_name}: {e}")
                break
            elif user_input in ['нет', 'no', 'n', 'н']:
                user_decision = "нет"
                print("\nЗараженные файлы НЕ были удалены (по решению пользователя)")
                break
            else:
                print("Пожалуйста, введите 'да' или 'нет'")

    print("\nШаг 7: Создание отчета report.txt...")
    with open("report.txt", 'w', encoding='utf-8') as f:
        f.write("Origin hash:\n")
        for file_name in sorted(origin_hashes.keys(), key=lambda x: int(x.split('.')[0])):
            f.write(f"{file_name} - {origin_hashes[file_name]}\n")

        f.write("Changed:\n")
        if changed_files:
            for file_name in sorted(changed_files.keys(), key=lambda x: int(x.split('.')[0])):
                f.write(f"{file_name} - {changed_files[file_name]}\n")
        else:
            f.write("Нет измененных файлов\n")

        f.write("Infected:\n")
        if infected_files:
            for file_name in sorted(infected_files.keys(), key=lambda x: int(x.split('.')[0])):
                f.write(f"{file_name} - {infected_files[file_name]}\n")
        else:
            f.write("Нет зараженных файлов\n")

        f.write("Deleted:\n")
        if deleted_files:
            f.write(f"Решение пользователя: {user_decision}\n")
            for file_name in sorted(deleted_files, key=lambda x: int(x.split('.')[0])):
                f.write(f"{file_name} - удален\n")
        else:
            if infected_files and user_decision == "нет":
                f.write(f"Решение пользователя: {user_decision}\n")
                f.write("Зараженные файлы не были удалены по решению пользователя\n")
            else:
                f.write("Нет удаленных файлов\n")

    print("  Отчет сохранен в report.txt")

    print("\n=== ПРОВЕРКА ЗАВЕРШЕНА ===")
    print(f"Проверено файлов: {len(test_files)}")
    print(f"Изменено файлов: {len(changed_files)}")
    print(f"Заражено файлов: {len(infected_files)}")
    print(f"Удалено файлов: {len(deleted_files)}")


if __name__ == "__main__":
    main()
