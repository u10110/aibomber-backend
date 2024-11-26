from django.contrib.auth.models import User

def user_balance(request):
    # Проверяем, авторизован ли пользователь
    if request.user.is_authenticated:
        user = request.user
        # Здесь предполагается, что у пользователя есть поле balance
        balance = user.ClientSettings.first().balance
        # balance = balance.balance
    else:
        balance = 0  # Если пользователь не авторизован, возвращаем 0

    # Возвращаем баланс в контексте
    
    return {'balance': balance}
