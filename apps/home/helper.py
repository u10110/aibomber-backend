import re



class Helper:
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    @staticmethod
    def filter_price(raw_price: str) -> int:
        """
        Price preprocessing.
        """
        raw_price = str(raw_price).replace("\xa0", "")
        price_pattern = r"\d+\.?\d*"
        match = re.search(price_pattern, raw_price.replace(",", ".").replace(" ", ""))

        if match:
            return round(float(match.group(0)), 0)
        return float(0)

    @staticmethod
    def phone_format(phone_number):
        clean_phone_number = re.sub("[^0-9]+", "", phone_number)
        formatted_phone_number = (
            re.sub(
                "(\d)(?=(\d{3})+(?!\d))", r"\1-", "%d" % int(clean_phone_number[:-1])
            )
            + clean_phone_number[-1]
        )
        return formatted_phone_number
