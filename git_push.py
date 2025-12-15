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
        output = result.stdout + result.stderr
        return output.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        output = e.stdout + e.stderr
        return output.strip(), e.returncode


def ensure_gitignore():
    """Проверяет наличие .gitignore и добавляет config.py если нужно"""
    gitignore_path = Path('.gitignore')
    
    if not gitignore_path.exists():
        print("📝 Создаю .gitignore...")
        gitignore_path.write_text('config.py\n')
    else:
        content = gitignore_path.read_text()
        if 'config.py' not in content:
            print("📝 Добавляю config.py в .gitignore...")
            with open(gitignore_path, 'a') as f:
                f.write('\nconfig.py\n')


def get_current_branch():
    """Получает текущую ветку или создает main если её нет"""
    branch, returncode = run_git_command("git rev-parse --abbrev-ref HEAD", check=False)
    
    # Если нет ветки или detached HEAD
    if returncode != 0 or branch == "HEAD":
        print("⚠️  Ветка не определена. Создаю ветку 'main'...")
        run_git_command("git checkout -b main", check=False)
        return "main"
    
    return branch


def main():
    print("🚀 Автоматическая отправка проекта на GitHub\n")
    
    # Проверяем, инициализирован ли git
    if not os.path.exists('.git'):
        print("❌ Ошибка: Git репозиторий не инициализирован. Запустите 'git init'")
        sys.exit(1)
    
    # Проверяем, настроен ли remote
    remote_output, _ = run_git_command("git remote -v")
    if not remote_output:
        print("❌ Ошибка: Remote репозиторий не настроен.")
        print("   Выполните: git remote add origin <URL_вашего_репозитория>")
        sys.exit(1)
    
    # Убеждаемся что config.py в .gitignore
    ensure_gitignore()
    
    # Проверяем наличие изменений
    status_output, _ = run_git_command("git status --porcelain")
    
    if not status_output:
        print("ℹ️  Нет изменений для коммита. Рабочее дерево чистое.")
        print("   Измените какие-нибудь файлы и попробуйте снова.")
        sys.exit(0)
    
    print(f"📝 Найдено изменений: {len(status_output.splitlines())}")
    
    # Добавляем все изменения
    print("📁 Добавляем файлы...")
    run_git_command("git add .")
    
    # Запрашиваем сообщение коммита у пользователя
    print("\n💬 Введите сообщение коммита:")
    commit_msg = input("> ").strip()
    
    if not commit_msg:
        print("⚠️ Сообщение коммита не может быть пустым!")
        commit_msg = input("Попробуйте ещё раз: ").strip()
        if not commit_msg:
            print("❌ Отмена операции")
            sys.exit(1)
    
    # Делаем коммит
    print(f"\n💾 Коммитим: {commit_msg}")
    output, returncode = run_git_command(f'git commit -m "{commit_msg}"', check=False)
    
    if returncode != 0:
        print(f"❌ Ошибка при коммите: {output}")
        sys.exit(1)
    
    # Получаем текущую ветку (с созданием если нужно)
    branch = get_current_branch()
    print(f"📌 Работаем с веткой: {branch}")
    
    # Устанавливаем upstream при первом push
    print("📤 Отправляем на GitHub...")
    output, returncode = run_git_command(f"git push -u origin {branch}", check=False)
    
    # Если push не удался из-за удалённых изменений
    if returncode != 0 and ("fetch first" in output or "rejected" in output):
        print("⚠️  Обнаружены изменения на GitHub. Синхронизирую...")
        sync_output, sync_code = run_git_command(f"git pull --rebase origin {branch}", check=False)
        
        if sync_code != 0:
            print(f"❌ Ошибка синхронизации: {sync_output}")
            sys.exit(1)
            
        print("📤 Повторная отправка на GitHub...")
        output, returncode = run_git_command(f"git push origin {branch}", check=False)
    
    if returncode != 0:
        print(f"❌ Ошибка Git: {output}")
        sys.exit(1)
    
    print("\n✅ Проект успешно отправлен на GitHub!")


if __name__ == "__main__":
    main()
