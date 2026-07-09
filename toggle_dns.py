#!/usr/bin/env python3
import subprocess
import sys
import os
import threading
import time

INTERFACE = "Wi-Fi"
CONFIG_FILE = os.path.expanduser("~/dns-toggler/.dns_config")

# ANSI Цвета для терминала (256-цветная палитра для мягких пастельных оттенков)
GREEN = "\033[38;5;120m"    # Мягкий зеленый (мята)
RED = "\033[38;5;203m"      # Нежный красный (коралл)
YELLOW = "\033[38;5;221m"   # Теплый желтый (янтарный)
CYAN = "\033[38;5;117m"     # Нежно-голубой (пастельный синий)
PURPLE = "\033[38;5;141m"   # Лавандовый (для заголовков/акцентов)
GRAY = "\033[38;5;243m"     # Серый для второстепенного текста (например, IP)
BOLD = "\033[1m"
RESET = "\033[0m"

# Шаблоны DNS серверов
DNS_TEMPLATES = {
    "1": {"name": "Google DNS", "ips": ["8.8.8.8", "8.8.4.4"]},
    "2": {"name": "Cloudflare DNS", "ips": ["1.1.1.1", "1.0.0.1"]},
    "3": {"name": "AdGuard DNS (Блокировка рекламы)", "ips": ["94.140.14.14", "94.140.15.15"]},
    "4": {"name": "Yandex DNS (Безопасный/Фильтрация)", "ips": ["77.88.8.8", "77.88.8.1"]},
}

def load_custom_dns():
    """Загружает кастомный DNS из конфигурационного файла."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                ips = [line.strip() for line in f if line.strip()]
                if ips:
                    return ips
        except Exception:
            pass
    return ["111.88.96.50"]  # Значение по умолчанию

def save_custom_dns(ips):
    """Сохраняет кастомный DNS в конфигурационный файл."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            for ip in ips:
                f.write(f"{ip}\n")
    except Exception as e:
        print(f"{RED}Не удалось сохранить настройки: {e}{RESET}")

def run_command_with_spinner(cmd, message):
    """Запускает команду с красивой анимацией загрузки."""
    result = {}
    start_time = time.time()
    
    def worker():
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            result['stdout'] = res.stdout
            result['stderr'] = res.stderr
            result['returncode'] = res.returncode
        except subprocess.CalledProcessError as e:
            result['error'] = e
            result['stdout'] = e.stdout
            result['stderr'] = e.stderr
            result['returncode'] = e.returncode
        except Exception as e:
            result['exception'] = e
            
    thread = threading.Thread(target=worker)
    thread.start()
    
    symbols = ['|', '/', '-', '\\']
    i = 0
    while thread.is_alive():
        symbol = symbols[i % len(symbols)]
        sys.stdout.write(f"\r{YELLOW}{symbol}{RESET} {message}")
        sys.stdout.flush()
        i += 1
        time.sleep(0.1)
        
    # Убедимся, что анимация крутится минимум 2.5 секунды для визуальной эстетики
    elapsed = time.time() - start_time
    if elapsed < 2.5:
        remaining = 2.5 - elapsed
        while remaining > 0:
            symbol = symbols[i % len(symbols)]
            sys.stdout.write(f"\r{YELLOW}{symbol}{RESET} {message}")
            sys.stdout.flush()
            i += 1
            step = min(0.1, remaining)
            time.sleep(step)
            remaining -= step
        
    # Очищаем строку после завершения анимации
    sys.stdout.write("\r" + " " * (len(message) + 10) + "\r")
    sys.stdout.flush()
    
    thread.join()
    
    if 'exception' in result:
        raise result['exception']
    if 'error' in result:
        raise result['error']
        
    return result

def get_current_dns():
    """Получает текущие DNS серверы для интерфейса Wi-Fi."""
    try:
        res = run_command_with_spinner(
            ["networksetup", "-getdnsservers", INTERFACE],
            "Получение текущих настроек DNS..."
        )
        output = res['stdout'].strip()
        # Если DNS не установлены вручную, macOS возвращает фразу о том, что серверов нет
        if "There aren't any DNS Servers set" in output or not output:
            return []
        return [line.strip() for line in output.split("\n") if line.strip()]
    except Exception as e:
        print(f"{RED}Ошибка при получении DNS: {e}{RESET}")
        return None

def set_dns(dns_list):
    """Устанавливает или сбрасывает DNS серверы."""
    try:
        if not dns_list:
            run_command_with_spinner(
                ["networksetup", "-setdnsservers", INTERFACE, "Empty"],
                "Сбрасываем DNS на автоматический (DHCP)..."
            )
            print(f"{GREEN}DNS успешно сброшен на автоматический (DHCP)!{RESET}")
        else:
            dns_str = ", ".join(dns_list)
            run_command_with_spinner(
                ["networksetup", "-setdnsservers", INTERFACE] + dns_list,
                f"Устанавливаем DNS: {dns_str}..."
            )
            print(f"{GREEN}DNS успешно изменен на {dns_str}!{RESET}")
    except Exception as e:
        print(f"{RED}Ошибка при изменении DNS: {e}{RESET}")

def print_status(current, custom_ips):
    """Выводит текущий статус DNS."""
    print(f"{BOLD}{PURPLE}═══ Переключатель DNS для macOS ({INTERFACE}) ═══{RESET}\n")
    
    if current:
        # Пытаемся определить, какой шаблон сейчас установлен
        matched_name = "Неизвестный кастомный DNS"
        for key, template in DNS_TEMPLATES.items():
            if set(current) == set(template["ips"]):
                matched_name = template["name"]
                break
        else:
            if set(current) == set(custom_ips):
                matched_name = "Твой шаблон DNS"
                
        print(f"Статус Wi-Fi DNS:  {RED}{BOLD}КАСТОМНЫЙ ({matched_name}){RESET}")
        print(f"Текущие серверы:   {GRAY}{', '.join(current)}{RESET}")
    else:
        print(f"Статус Wi-Fi DNS:  {GREEN}{BOLD}АВТОМАТИЧЕСКИЙ (DHCP){RESET}")

def main():
    while True:
        # Очищаем терминал перед каждым выводом статуса для чистоты интерфейса
        os.system("clear" if os.name != "nt" else "cls")
        
        custom_ips = load_custom_dns()
        current = get_current_dns()
        if current is None:
            input("\nНажмите Enter для выхода...")
            sys.exit(1)
            
        print_status(current, custom_ips)
        
        print(f"\n{BOLD}{PURPLE}Доступные шаблоны DNS:{RESET}")
        for key, val in DNS_TEMPLATES.items():
            print(f"  {CYAN}[{key}]{RESET} - {val['name']} {GRAY}({', '.join(val['ips'])}){RESET}")
        print(f"  {CYAN}[5]{RESET} - Твой шаблон DNS {GRAY}({', '.join(custom_ips)}){RESET}")
        print(f"  {CYAN}[0]{RESET} - Сбросить на автоматический (DHCP)")
        print(f"  {CYAN}[C]{RESET} - Изменить твой шаблон DNS")
        print(f"  {CYAN}[Q]{RESET} - Выйти")
        
        try:
            choice = input("\nВыберите действие (введите цифру или букву): ").strip().lower()
        except KeyboardInterrupt:
            print("\nВыход.")
            sys.exit(0)
            
        if choice == 'q':
            sys.exit(0)
        elif choice == '0':
            set_dns([])
            time.sleep(1.5)
        elif choice in DNS_TEMPLATES:
            set_dns(DNS_TEMPLATES[choice]["ips"])
            time.sleep(1.5)
        elif choice == '5':
            set_dns(custom_ips)
            time.sleep(1.5)
        elif choice == 'c':
            try:
                new_dns_input = input("\nВведите новые IP DNS серверов через пробел: ").strip()
            except KeyboardInterrupt:
                print("\nОтмена.")
                time.sleep(1.0)
                continue
            if new_dns_input:
                new_ips = new_dns_input.split()
                save_custom_dns(new_ips)
                print(f"{GREEN}Твой шаблон успешно сохранен как: {', '.join(new_ips)}{RESET}")
                set_dns(new_ips)
                time.sleep(1.5)
            else:
                print("Ввод пуст. Отмена.")
                time.sleep(1.0)
        else:
            print(f"{RED}Неверный выбор.{RESET}")
            time.sleep(1.0)

if __name__ == "__main__":
    main()
