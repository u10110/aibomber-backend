import os
import django

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.home.models import Proxy  # Импортируем модель Proxy

# Список прокси-адресов
proxies = [

]

# Добавляем прокси в базу данных
for proxy in proxies:
    # Создаем или обновляем запись
    obj, created = Proxy.objects.update_or_create(
        value=proxy,
        defaults={'updated_at': None}  # Обновляем updated_at, если потребуется
    )
    if created:
        print(f"Добавлен новый прокси: {proxy}")
    else:
        print(f"Обновлен существующий прокси: {proxy}")

print("Все прокси обработаны.")
