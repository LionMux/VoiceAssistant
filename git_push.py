#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path

def run_git_command(cmd, check=True):
    """Выполняет git команду и возвращает результат"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True, cwd=Path(__file__).parent)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка Git: {e.stderr}")
        sys.exit(1)

def main():
    print("🚀 Автоматическая отправка проекта на GitHub")
    
    # Проверяем, инициализирован ли git
    if not os.path.exists('.git'):
        print("❌ Ошибка: Git репозиторий не инициализирован. Запустите 'git init'")
        sys.exit(1)
    
    # Добавляем все изменения
    print("📁 Добавляем файлы...")
    run_git_command("git add .")
    
    # Делаем коммит (можно передать сообщение через аргумент)
    commit_msg = sys.argv[1] if len(sys.argv) > 1 else "Авто-коммит из скрипта"
    print(f"💾 Коммитим: {commit_msg}")
    run_git_command(f'git commit -m "{commit_msg}"')
    
    # Пушим на GitHub (main или master)
    print("📤 Отправляем на GitHub...")
    branch = run_git_command("git rev-parse --abbrev-ref HEAD").strip()
    run_git_command(f"git push origin {branch}")
    
    print("✅ Проект успешно отправлен на GitHub!")

if __name__ == "__main__":
    main()
