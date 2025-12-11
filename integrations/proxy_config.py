"""
Автоматический VPN прокси для Spotify API через Hiddify subscription
"""
import requests
import base64
import subprocess
import json
import os
import time
import tempfile
import zipfile
import platform
from urllib.parse import urlparse, parse_qs, unquote

# === НАСТРОЙКИ ===
SUBSCRIPTION_URL = "https://key.vpn-one.com/c/1d8ae10d-8dff-4925-b12c-053fafd6b9cc"
SOCKS_PORT = 10808

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
_xray_process = None
_xray_config_file = None


def _get_xray_path():
    """Путь к Xray executable"""
    xray_dir = os.path.join(os.path.expanduser("~"), ".xray_spotify")
    os.makedirs(xray_dir, exist_ok=True)
    
    if platform.system() == "Windows":
        return os.path.join(xray_dir, "xray.exe")
    return os.path.join(xray_dir, "xray")


def _download_xray():
    """Скачивает Xray-core если его нет"""
    xray_path = _get_xray_path()
    
    if os.path.exists(xray_path):
        return xray_path
    
    print("📦 Скачиваю Xray-core (это произойдет один раз)...")
    
    system = platform.system()
    if system == "Windows":
        url = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-windows-64.zip"
    elif system == "Linux":
        url = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
    elif system == "Darwin":  # macOS
        url = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-macos-64.zip"
    else:
        print(f"❌ Неподдерживаемая ОС: {system}")
        return None
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        xray_dir = os.path.dirname(xray_path)
        zip_path = os.path.join(xray_dir, "xray.zip")
        
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(xray_dir)
        
        os.remove(zip_path)
        
        # Права на выполнение для Linux/Mac
        if system != "Windows":
            os.chmod(xray_path, 0o755)
        
        print(f"✅ Xray-core установлен")
        return xray_path
        
    except Exception as e:
        print(f"❌ Ошибка скачивания Xray: {e}")
        return None


def _parse_vless(link):
    """Парсит vless:// ссылку в Xray outbound конфиг"""
    try:
        print(f"🔍 Парсинг VLESS конфигурации...")
        
        link = link.replace("vless://", "")
        
        if "@" not in link:
            print("⚠️ Некорректный формат VLESS (нет @)")
            return None
            
        uuid_part, rest = link.split("@", 1)
        
        # Разделяем server:port от параметров
        if "?" in rest:
            server_part, params_part = rest.split("?", 1)
        else:
            server_part = rest.split("#")[0]
            params_part = ""
        
        # Парсим server:port
        if ":" in server_part:
            server, port = server_part.rsplit(":", 1)
            port = int(port)
        else:
            server = server_part
            port = 443
        
        # Парсим параметры
        params = {}
        if params_part:
            params_part = params_part.split("#")[0]
            for param in params_part.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = unquote(value)
        
        network_type = params.get("type", "tcp")
        security = params.get("security", "none")
        
        print(f"   Server: {server}:{port}")
        print(f"   Type: {network_type}, Security: {security}")
        
        # Базовый конфиг
        config = {
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": server,
                    "port": port,
                    "users": [{
                        "id": uuid_part,
                        "encryption": "none"
                    }]
                }]
            },
            "streamSettings": {
                "network": network_type
            }
        }
        
        # Добавляем flow если есть
        if params.get("flow"):
            config["settings"]["vnext"][0]["users"][0]["flow"] = params["flow"]
        
        # Настройки безопасности
        if security == "tls":
            config["streamSettings"]["security"] = "tls"
            config["streamSettings"]["tlsSettings"] = {
                "serverName": params.get("sni", server),
                "allowInsecure": False,
                "fingerprint": params.get("fp", "chrome")
            }
        elif security == "reality":
            config["streamSettings"]["security"] = "reality"
            config["streamSettings"]["realitySettings"] = {
                "serverName": params.get("sni", server),
                "fingerprint": params.get("fp", "chrome"),
                "show": False
            }
            # Добавляем publicKey если есть
            if params.get("pbk"):
                config["streamSettings"]["realitySettings"]["publicKey"] = params["pbk"]
            # Добавляем shortId если есть
            if params.get("sid"):
                config["streamSettings"]["realitySettings"]["shortId"] = params["sid"]
        
        # WebSocket настройки
        if network_type == "ws":
            config["streamSettings"]["wsSettings"] = {
                "path": params.get("path", "/")
            }
            if params.get("host"):
                config["streamSettings"]["wsSettings"]["headers"] = {
                    "Host": params["host"]
                }
        
        # gRPC настройки
        if network_type == "grpc":
            config["streamSettings"]["grpcSettings"] = {
                "serviceName": params.get("serviceName", ""),
                "multiMode": params.get("mode") == "multi"
            }
        
        print(f"✅ VLESS конфиг создан")
        return config
        
    except Exception as e:
        print(f"⚠️ Ошибка парсинга VLESS: {e}")
        return None



def _parse_vmess(link):
    """Парсит vmess:// ссылку в Xray outbound конфиг"""
    # vmess://base64(json)
    try:
        link = link.replace("vmess://", "")
        decoded = base64.b64decode(link).decode('utf-8')
        vmess_json = json.loads(decoded)
        
        config = {
            "protocol": "vmess",
            "settings": {
                "vnext": [{
                    "address": vmess_json.get("add"),
                    "port": int(vmess_json.get("port", 443)),
                    "users": [{
                        "id": vmess_json.get("id"),
                        "alterId": int(vmess_json.get("aid", 0)),
                        "security": vmess_json.get("scy", "auto")
                    }]
                }]
            },
            "streamSettings": {
                "network": vmess_json.get("net", "tcp"),
                "security": vmess_json.get("tls", "none")
            }
        }
        
        if vmess_json.get("tls") == "tls":
            config["streamSettings"]["tlsSettings"] = {
                "serverName": vmess_json.get("sni", vmess_json.get("add"))
            }
        
        return config
        
    except Exception as e:
        print(f"⚠️ Ошибка парсинга vmess: {e}")
        return None


def _get_subscription_links():
    """Получает ссылки из subscription"""
    try:
        response = requests.get(SUBSCRIPTION_URL, timeout=10)
        response.raise_for_status()
        
        # Используем response.content (bytes) вместо response.text
        # Некоторые subscription возвращают уже декодированный текст
        content = response.content if isinstance(response.content, bytes) else response.text.encode('utf-8')
        
        try:
            # Пробуем декодировать как base64
            decoded = base64.b64decode(content).decode('utf-8')
        except:
            # Если не base64 - значит уже plain text
            decoded = content.decode('utf-8')
        
        # Разбиваем на строки и фильтруем пустые
        links = []
        for line in decoded.split('\n'):
            line = line.strip()
            if line and (line.startswith('vless://') or 
                        line.startswith('vmess://') or 
                        line.startswith('ss://') or 
                        line.startswith('trojan://')):
                links.append(line)
        
        print(f"✅ Получено {len(links)} конфигураций")
        return links
        
    except Exception as e:
        print(f"❌ Ошибка получения subscription: {e}")
        import traceback
        traceback.print_exc()  # Для отладки
        return []



def _create_xray_config(outbound):
    """Создает полный Xray config с SOCKS5 inbound"""
    return {
        "log": {
            "loglevel": "warning"
        },
        "inbounds": [{
            "port": SOCKS_PORT,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {
                "udp": True,
                "auth": "noauth"
            }
        }],
        "outbounds": [outbound]
    }


def start_xray_tunnel():
    """Запускает Xray процесс в фоновом режиме"""
    global _xray_process, _xray_config_file
    
    # Если уже запущен - ничего не делаем
    if _xray_process and _xray_process.poll() is None:
        return True
    
    # Скачиваем/проверяем Xray
    xray_path = _download_xray()
    if not xray_path:
        return False
    
    # Получаем subscription links
    print("🔄 Загрузка VPN конфигурации...")
    links = _get_subscription_links()
    
    if not links:
        print("❌ Не удалось получить конфигурацию")
        return False
    
    # Пробуем запустить разные конфиги
    for i, link in enumerate(links[:10]):  # Пробуем первые 10
        outbound = None
        
        if link.startswith("vless://"):
            outbound = _parse_vless(link)
        elif link.startswith("vmess://"):
            outbound = _parse_vmess(link)
        
        if not outbound:
            continue
        
        # Создаем конфиг файл
        xray_config = _create_xray_config(outbound)
        
        # Создаем временный файл для логов
        log_file = os.path.join(os.path.dirname(_get_xray_path()), "xray.log")
        
        # Обновляем конфиг с логированием
        xray_config["log"] = {
            "loglevel": "warning",
            "access": "",
            "error": log_file
        }
        
        # Сохраняем во временный файл
        if _xray_config_file and os.path.exists(_xray_config_file):
            os.remove(_xray_config_file)
        
        fd, _xray_config_file = tempfile.mkstemp(suffix='.json', prefix='xray_')
        with os.fdopen(fd, 'w') as f:
            json.dump(xray_config, f, indent=2)
        
        # Запускаем Xray
        try:
            print(f"🚀 Попытка {i+1}: запуск VPN туннеля...")
            
            _xray_process = subprocess.Popen(
                [xray_path, "run", "-config", _xray_config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # Даем время на запуск
            time.sleep(4)
            
            # Проверяем что процесс жив
            if _xray_process.poll() is None:
                print(f"✅ VPN туннель активен (порт {SOCKS_PORT})")
                return True
            else:
                # Читаем ошибку
                stderr_output = _xray_process.stderr.read().decode('utf-8', errors='ignore')
                if stderr_output:
                    print(f"   ⚠️ Ошибка: {stderr_output[:200]}")
                print(f"   ❌ Конфиг #{i+1} не работает, пробуем следующий...")
                continue
                
        except Exception as e:
            print(f"   ⚠️ Ошибка запуска: {e}")
            continue
    
    print("❌ Ни один конфиг не запустился")
    return False


def get_proxy():
    """
    Главная функция - вызывается из spotify_manager.py
    Возвращает proxies dict для использования с spotipy
    """
    success = start_xray_tunnel()
    
    if success:
        # Spotipy/requests поддерживает socks5
        proxy_url = f"socks5://127.0.0.1:{SOCKS_PORT}"
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    # Если не удалось - работаем без прокси
    print("⚠️ Работаю без VPN (может не работать из-за гео-блокировки)")
    return None


def stop_xray():
    """Останавливает Xray (вызывать при выходе из приложения)"""
    global _xray_process, _xray_config_file
    
    if _xray_process:
        _xray_process.terminate()
        _xray_process.wait(timeout=5)
        _xray_process = None
    
    if _xray_config_file and os.path.exists(_xray_config_file):
        os.remove(_xray_config_file)
        _xray_config_file = None


# Автоматическая очистка при выходе
import atexit
atexit.register(stop_xray)
