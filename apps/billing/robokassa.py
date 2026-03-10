import decimal
import hashlib
from urllib import parse
from urllib.parse import urlparse
# from django.conf.settings import LOGIN, PASSWORD1, PASSWORD2, TEST_MODE
from django.conf import settings

class Robokassa():
    def calculate_signature(*args) -> str:
        print(args)
        return hashlib.md5(':'.join(str(arg) for arg in args).encode()).hexdigest()

    def parse_response(request: str) -> dict:
        """
        :param request: Link.
        :return: Dictionary.
        """
        params = {}

        for item in urlparse(request).query.split('&'):
            key, value = item.split('=')
            params[key] = value
        return params


    def check_signature_result(
        order_number: int,  # invoice number
        received_sum: decimal,  # cost of goods, RU
        received_signature: hex,  # SignatureValue
        password = settings.PASSWORD1  # Merchant password
    ) -> bool:
        signature = Robokassa.calculate_signature(received_sum, order_number, password)
        print(signature.lower())
        print(received_signature.lower())
        if signature.lower() == received_signature.lower():
            return True
        return False


    # Формирование URL переадресации пользователя на оплату.

    def generate_payment_link(
        cost: decimal,  # Cost of goods, RU
        number: int,  # Invoice number
        description: str,  # Description of the purchase
        merchant_login = settings.LOGIN,  # Merchant login
        merchant_password_1 = settings.PASSWORD1,  # Merchant password
        is_test = settings.TEST_MODE,
        robokassa_payment_url = 'https://auth.robokassa.ru/Merchant/Index.aspx',
    ) -> str:
        """URL for redirection of the customer to the service.
        """
        signature = Robokassa.calculate_signature(
            merchant_login,
            cost,
            number,
            merchant_password_1
        )

        data = {
            'MerchantLogin': merchant_login,
            'OutSum': cost,
            'InvId': number,
            'Description': description,
            'SignatureValue': signature,
            'IsTest': is_test
        }
        return f'{robokassa_payment_url}?{parse.urlencode(data)}'


    # Получение уведомления об исполнении операции (ResultURL).

    def result_payment(request: str, merchant_password_2=settings.PASSWORD2) -> str:
        """Verification of notification (ResultURL).
        :param request: HTTP parameters.
        """
        param_request = request
        # param_request = Robokassa.parse_response(request)
        cost = param_request['OutSum']
        number = param_request['InvId']
        signature = param_request['SignatureValue']

        signature = Robokassa.calculate_signature(cost, number, signature)

        if Robokassa.check_signature_result(number, cost, signature, merchant_password_2):
            return f'OK{param_request["InvId"]}'
        return "bad sign"


    # Проверка параметров в скрипте завершения операции (SuccessURL).

    def check_success_payment(request: str, merchant_password_1=settings.PASSWORD1) -> str:
        """ Verification of operation parameters ("cashier check") in SuccessURL script.
        :param request: HTTP parameters
        """
        param_request = request 
        # param_request = Robokassa.parse_response(request)
        cost = param_request['OutSum']
        number = param_request['InvId']
        signature = param_request['SignatureValue']

        # signature = Robokassa.calculate_signature(cost, number, signature)

        if Robokassa.check_signature_result(number, cost, signature, merchant_password_1):
            return True
        return False
