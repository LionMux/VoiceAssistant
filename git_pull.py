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

def main():
    print("⬇️  Получение изменений из GitHub\n")
    
    # Проверяем, инициализирован ли git
    if not os.path.exists('.git'):
        print("❌ Ошибка: Git репозиторий не инициализирован.")
        sys.exit(1)
    
    # Проверяем, настроен ли remote
    remote_output, _ = run_git_command("git remote -v")
    if not remote_output:
        print("❌ Ошибка: Remote репозиторий не настроен.")
        print("   Выполните: git remote add origin <URL_вашего_репозитория>")
        sys.exit(1)
    
    # Проверяем, есть ли несохранённые изменения
    status_output, _ = run_git_command("git status --porcelain")
    
    if status_output:
        print("⚠️  Обнаружены несохранённые изменения:")
        print(status_output)
        print("\nВыберите действие:")
        print("1 - Сохранить изменения в stash и продолжить")
        print("2 - Отменить локальные изменения и продолжить (ОПАСНО!)")
        print("3 - Отменить операцию")
        
        choice = input("\nВаш выбор (1/2/3): ").strip()
        
        if choice == "1":
            print("\n💾 Сохраняю изменения в stash...")
            run_git_command("git stash")
            stashed = True
        elif choice == "2":
            confirm = input("⚠️  Вы уверены? Это удалит все локальные изменения! (yes/no): ")
            if confirm.lower() == "yes":
                print("\n🗑️  Отменяю локальные изменения...")
                run_git_command("git reset --hard HEAD")
                stashed = False
            else:
                print("❌ Операция отменена")
                sys.exit(0)
        else:
            print("❌ Операция отменена")
            sys.exit(0)
    else:
        stashed = False
    
    # Сохраняем config.py если он есть
    config_backup = None
    if Path('config.py').exists():
        config_backup = Path('config.py').read_text()
        print("🔒 Сохраняю config.py...")
    
    # Получаем текущую ветку
    branch, _ = run_git_command("git rev-parse --abbrev-ref HEAD")
    
    # Спрашиваем про rebase
    print(f"\n📥 Получаю изменения из ветки: {branch}")
    print("\nВыберите режим pull:")
    print("1 - Обычный pull (merge)")
    print("2 - Pull с rebase (линейная история)")
    
    pull_choice = input("\nВаш выбор (1/2, по умолчанию 2): ").strip() or "2"
    
    if pull_choice == "2":
        print("\n⬇️  Выполняю git pull --rebase...")
        output, returncode = run_git_command(f"git pull --rebase origin {branch}", check=False)
    else:
        print("\n⬇️  Выполняю git pull...")
        output, returncode = run_git_command(f"git pull origin {branch}", check=False)
    
    # Восстанавливаем config.py если нужно
    if config_backup and not Path('config.py').exists():
        Path('config.py').write_text(config_backup)
        print("✅ Восстановил config.py")
    
    # Проверяем результат
    if returncode != 0:
        if "CONFLICT" in output or "conflict" in output:
            print(f"\n⚠️  Обнаружены конфликты слияния:\n{output}")
            print("\nРешите конфликты вручную и выполните:")
            print("  git add .")
            print("  git rebase --continue  (если использовали rebase)")
            print("  git commit  (если использовали merge)")
            sys.exit(1)
        else:
            print(f"\n❌ Ошибка Git: {output}")
            sys.exit(1)
    
    print(f"\n{output}")
    
    # Восстанавливаем изменения из stash
    if stashed:
        print("\n📤 Восстанавливаю сохранённые изменения из stash...")
        stash_output, stash_code = run_git_command("git stash pop", check=False)
        
        if stash_code != 0:
            print(f"⚠️  Предупреждение: {stash_output}")
            print("Проверьте конфликты и разрешите их вручную.")
        else:
            print("✅ Изменения восстановлены")
    
    print("\n✅ Репозиторий успешно обновлён!")

if __name__ == "__main__":
    main()
