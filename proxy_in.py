import os
import django

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.home.models import Proxy  # Импортируем модель Proxy

# Список прокси-адресов
proxies = [
    "SdtHiE:QypQ4hraH8@109.248.14.68:3000",
"SdtHiE:QypQ4hraH8@188.130.136.178:3000",
"SdtHiE:QypQ4hraH8@185.181.246.58:3000",
"SdtHiE:QypQ4hraH8@45.11.21.252:3000",
"SdtHiE:QypQ4hraH8@46.8.16.192:3000",
"SdtHiE:QypQ4hraH8@46.8.222.138:3000",
"SdtHiE:QypQ4hraH8@45.81.136.51:3000",
"SdtHiE:QypQ4hraH8@188.130.185.8:3000",
"SdtHiE:QypQ4hraH8@94.158.190.115:3000",
"SdtHiE:QypQ4hraH8@46.8.157.223:3000",
"SdtHiE:QypQ4hraH8@188.130.137.207:3000",
"SdtHiE:QypQ4hraH8@109.248.138.159:3000",
"SdtHiE:QypQ4hraH8@45.11.21.37:3000",
"SdtHiE:QypQ4hraH8@45.90.196.70:3000",
"SdtHiE:QypQ4hraH8@109.248.14.137:3000",
"SdtHiE:QypQ4hraH8@31.40.203.75:3000",
"SdtHiE:QypQ4hraH8@46.8.110.64:3000",
"SdtHiE:QypQ4hraH8@46.8.106.193:3000",
"SdtHiE:QypQ4hraH8@45.15.72.67:3000",
"SdtHiE:QypQ4hraH8@45.81.136.106:3000",
"SdtHiE:QypQ4hraH8@109.248.143.91:3000",
"SdtHiE:QypQ4hraH8@46.8.212.78:3000",
"SdtHiE:QypQ4hraH8@46.8.23.24:3000",
"SdtHiE:QypQ4hraH8@188.130.128.113:3000",
"SdtHiE:QypQ4hraH8@188.130.185.181:3000",
"SdtHiE:QypQ4hraH8@45.87.253.186:3000",
"SdtHiE:QypQ4hraH8@46.8.222.175:3000",
"SdtHiE:QypQ4hraH8@109.248.204.221:3000",
"SdtHiE:QypQ4hraH8@5.183.130.132:3000",
"SdtHiE:QypQ4hraH8@188.130.189.98:3000",
"SdtHiE:QypQ4hraH8@185.181.247.45:3000",
"SdtHiE:QypQ4hraH8@109.248.14.223:3000",
"SdtHiE:QypQ4hraH8@46.8.17.183:3000",
"SdtHiE:QypQ4hraH8@46.8.16.48:3000",
"SdtHiE:QypQ4hraH8@188.130.137.198:3000",
"SdtHiE:QypQ4hraH8@46.8.22.199:3000",
"SdtHiE:QypQ4hraH8@45.90.196.57:3000",
"SdtHiE:QypQ4hraH8@109.248.204.54:3000",
"SdtHiE:QypQ4hraH8@109.248.129.151:3000",
"SdtHiE:QypQ4hraH8@188.130.218.195:3000",
"SdtHiE:QypQ4hraH8@188.130.129.226:3000",
"SdtHiE:QypQ4hraH8@188.130.211.27:3000",
"SdtHiE:QypQ4hraH8@5.183.130.149:3000",
"SdtHiE:QypQ4hraH8@46.8.111.42:3000",
"SdtHiE:QypQ4hraH8@94.158.190.71:3000",
"SdtHiE:QypQ4hraH8@188.130.210.210:3000",
"SdtHiE:QypQ4hraH8@109.248.205.195:3000",
"SdtHiE:QypQ4hraH8@46.8.106.7:3000",
"SdtHiE:QypQ4hraH8@109.248.204.172:3000",
"SdtHiE:QypQ4hraH8@213.226.101.98:3000",
"SdtHiE:QypQ4hraH8@109.248.15.234:3000",
"SdtHiE:QypQ4hraH8@109.248.13.223:3000",
"SdtHiE:QypQ4hraH8@45.15.72.84:3000",
"SdtHiE:QypQ4hraH8@46.8.213.223:3000",
"SdtHiE:QypQ4hraH8@45.90.196.132:3000",
"SdtHiE:QypQ4hraH8@45.81.136.66:3000",
"SdtHiE:QypQ4hraH8@109.248.55.164:3000",
"SdtHiE:QypQ4hraH8@188.130.219.190:3000",
"SdtHiE:QypQ4hraH8@45.86.1.172:3000",
"SdtHiE:QypQ4hraH8@188.130.128.45:3000",
"SdtHiE:QypQ4hraH8@46.8.22.53:3000",
"SdtHiE:QypQ4hraH8@109.248.15.162:3000",
"SdtHiE:QypQ4hraH8@188.130.129.197:3000",
"SdtHiE:QypQ4hraH8@46.8.106.138:3000",
"SdtHiE:QypQ4hraH8@109.248.14.72:3000",
"SdtHiE:QypQ4hraH8@188.130.136.253:3000",
"SdtHiE:QypQ4hraH8@46.8.17.186:3000",
"SdtHiE:QypQ4hraH8@109.248.143.163:3000",
"SdtHiE:QypQ4hraH8@5.183.130.42:3000",
"SdtHiE:QypQ4hraH8@46.8.106.215:3000",
"SdtHiE:QypQ4hraH8@45.86.1.223:3000",
"SdtHiE:QypQ4hraH8@109.248.142.129:3000",
"SdtHiE:QypQ4hraH8@188.130.136.143:3000",
"SdtHiE:QypQ4hraH8@45.90.196.2:3000",
"SdtHiE:QypQ4hraH8@194.32.229.50:3000",
"SdtHiE:QypQ4hraH8@185.181.245.105:3000",
"SdtHiE:QypQ4hraH8@188.130.128.49:3000",
"SdtHiE:QypQ4hraH8@188.130.136.23:3000",
"SdtHiE:QypQ4hraH8@46.8.222.96:3000",
"SdtHiE:QypQ4hraH8@188.130.129.219:3000",
"SdtHiE:QypQ4hraH8@94.158.190.97:3000",
"SdtHiE:QypQ4hraH8@188.130.128.192:3000",
"SdtHiE:QypQ4hraH8@109.248.139.89:3000",
"SdtHiE:QypQ4hraH8@46.8.192.192:3000",
"SdtHiE:QypQ4hraH8@46.8.110.79:3000",
"SdtHiE:QypQ4hraH8@45.87.253.34:3000",
"SdtHiE:QypQ4hraH8@45.90.196.222:3000",
"SdtHiE:QypQ4hraH8@109.248.138.236:3000",
"SdtHiE:QypQ4hraH8@45.86.0.5:3000",
"SdtHiE:QypQ4hraH8@46.8.22.103:3000",
"SdtHiE:QypQ4hraH8@45.15.72.152:3000",
"SdtHiE:QypQ4hraH8@109.248.128.193:3000",
"SdtHiE:QypQ4hraH8@46.8.107.142:3000",
"SdtHiE:QypQ4hraH8@92.119.193.54:3000",
"SdtHiE:QypQ4hraH8@109.248.205.22:3000",
"SdtHiE:QypQ4hraH8@46.8.107.117:3000",
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
