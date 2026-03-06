#!/usr/bin/env python3
"""
Скрипт нагрузочного тестирования для сервиса модерации
"""
import requests
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

API_URL = "http://localhost:8003"

# Цвета для терминала
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

# Данные для генерации
CATEGORIES = list(range(1, 101))
NAMES = [
    "iPhone 15 Pro", "MacBook Air", "Samsung Galaxy", "PlayStation 5",
    "Nike Shoes", "Adidas Sneakers", "Gaming Chair", "Laptop Backpack",
    "Wireless Headphones", "Smart Watch", "Bluetooth Speaker", "Camera",
    "Vintage Watch", "Designer Bag", "Electric Scooter", "Bicycle"
]

DESCRIPTIONS = [
    "Brand new, never used. Original packaging included.",
    "Slightly used, excellent condition. No scratches or defects.",
    "Rare item! Buy now before it's gone! Limited offer!",
    "High quality product. Fast shipping available.",
    "💰 BEST PRICE! 🔥 DON'T MISS THIS DEAL! 💎",
    "Authentic product with warranty. Free delivery.",
    "Like new condition. Comes with all accessories.",
    "Perfect for daily use. Great value for money.",
    "🎁 Special discount! ⚡ Order now! 🚀 Free shipping!",
    "Professional seller. Quick response guaranteed."
]

def generate_item():
    """Генерация случайного объявления"""
    seller_id = random.randint(1, 5000)
    item_id = random.randint(1, 100000)
    is_verified = random.choice([True, False])
    
    return {
        "seller_id": seller_id,
        "is_verified_seller": is_verified,
        "item_id": item_id,
        "name": random.choice(NAMES),
        "description": random.choice(DESCRIPTIONS),
        "category": random.choice(CATEGORIES),
        "images_qty": random.randint(1, 10)
    }

def send_predict_request(session, item_data):
    """Отправка запроса на предсказание"""
    try:
        start = time.time()
        response = session.post(f"{API_URL}/predict", json=item_data, timeout=5)
        duration = time.time() - start
        
        return {
            "status": response.status_code,
            "duration": duration,
            "success": response.status_code == 200,
            "data": response.json() if response.status_code == 200 else None
        }
    except Exception as e:
        return {
            "status": 0,
            "duration": 0,
            "success": False,
            "error": str(e)
        }

def check_api_availability():
    """Проверка доступности API"""
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False

def print_progress(current, total, prefix='', success=0, errors=0):
    """Вывод прогресса"""
    bar_length = 40
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    percent = 100 * current / total
    
    print(f'\r{prefix} |{bar}| {percent:.1f}% ({current}/{total}) '
          f'✓ {Colors.GREEN}{success}{Colors.END} '
          f'✗ {Colors.RED}{errors}{Colors.END}', end='', flush=True)

def run_load_test(num_requests=200, num_workers=10):
    """Основная функция нагрузочного тестирования"""
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}🚀 Нагрузочное тестирование API модерации{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    # Проверка доступности
    print(f"{Colors.YELLOW}⏳ Проверка доступности API...{Colors.END}")
    if not check_api_availability():
        print(f"{Colors.RED}❌ API недоступен на {API_URL}{Colors.END}")
        print(f"{Colors.YELLOW}Запусти: uvicorn app.main:app --host 0.0.0.0 --port 8003{Colors.END}")
        return
    print(f"{Colors.GREEN}✅ API доступен{Colors.END}\n")
    
    # Статистика
    results = []
    success_count = 0
    error_count = 0
    violations = 0
    no_violations = 0
    
    session = requests.Session()
    
    print(f"{Colors.YELLOW}📤 Отправка {num_requests} запросов с {num_workers} потоками...{Colors.END}\n")
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        
        for i in range(num_requests):
            item = generate_item()
            future = executor.submit(send_predict_request, session, item)
            futures.append(future)
        
        # Обработка результатов
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            
            if result["success"]:
                success_count += 1
                if result["data"] and result["data"].get("is_violation"):
                    violations += 1
                else:
                    no_violations += 1
            else:
                error_count += 1
            
            print_progress(i, num_requests, "Прогресс:", success_count, error_count)
    
    total_time = time.time() - start_time
    
    print("\n")
    
    # Дополнительные запросы для разнообразия
    print(f"\n{Colors.YELLOW}🎯 Генерация специальных сценариев...{Colors.END}\n")
    
    # Невалидные запросы
    print(f"{Colors.YELLOW}Отправка невалидных запросов...{Colors.END}")
    for i in range(10):
        try:
            session.post(f"{API_URL}/predict", json={"invalid": "data"}, timeout=2)
        except:
            pass
        print(f"\r❌ Невалидный запрос {i+1}/10", end='', flush=True)
        time.sleep(0.1)
    
    print(f"\n{Colors.GREEN}✓ Готово{Colors.END}\n")
    
    # Расчет статистики
    durations = [r["duration"] for r in results if r["success"]]
    avg_duration = sum(durations) / len(durations) if durations else 0
    min_duration = min(durations) if durations else 0
    max_duration = max(durations) if durations else 0
    
    rps = num_requests / total_time if total_time > 0 else 0
    
    # Вывод результатов
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}📊 ИТОГОВАЯ СТАТИСТИКА{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    print(f"⏱️  Время выполнения: {Colors.GREEN}{total_time:.2f}s{Colors.END}")
    print(f"🚀 Запросов в секунду: {Colors.GREEN}{rps:.2f} RPS{Colors.END}\n")
    
    print(f"📈 Всего запросов: {num_requests}")
    print(f"✅ Успешных: {Colors.GREEN}{success_count}{Colors.END}")
    print(f"❌ Ошибок: {Colors.RED}{error_count}{Colors.END}\n")
    
    print(f"🔍 Предсказания модели:")
    print(f"   🚫 Нарушения: {Colors.RED}{violations}{Colors.END}")
    print(f"   ✓ Без нарушений: {Colors.GREEN}{no_violations}{Colors.END}\n")
    
    print(f"⚡ Производительность:")
    print(f"   Среднее время: {Colors.YELLOW}{avg_duration*1000:.2f}ms{Colors.END}")
    print(f"   Минимум: {Colors.GREEN}{min_duration*1000:.2f}ms{Colors.END}")
    print(f"   Максимум: {Colors.RED}{max_duration*1000:.2f}ms{Colors.END}\n")
    
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}🔗 Ссылки:{Colors.END}")
    print(f"   📊 Grafana: {Colors.BLUE}http://localhost:3000{Colors.END} (admin/admin)")
    print(f"   📈 Prometheus: {Colors.BLUE}http://localhost:9090{Colors.END}")
    print(f"   📡 Метрики API: {Colors.BLUE}http://localhost:8003/metrics{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

if __name__ == "__main__":
    import sys
    
    num_requests = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print(f"\n{Colors.GREEN}💡 Использование:{Colors.END}")
    print(f"   python load_test.py [количество_запросов] [количество_потоков]")
    print(f"   По умолчанию: 200 запросов, 10 потоков\n")
    
    run_load_test(num_requests, num_workers)
