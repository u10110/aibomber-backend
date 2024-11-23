import re

from apps.alert.services import wb_api
from apps.home.models import Brand


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
    def check_sku(sku, marketplace_id=1, type=None):
        data = wb_api.WbHepler.cards_detail_request(sku)
        count_size_stock = 0
        for size_data in data["data"]["products"][0]["sizes"]:
            print(size_data["stocks"])
            if len(size_data["stocks"]) != 0:
                count_size_stock += 1
        if count_size_stock == 0 and type != "review" and type != "seo":
            return False

        title = data["data"]["products"][0]["name"]
        cover = f"https://images.wbstatic.net/big/new/{str(sku)[:-4]}0000/{sku}-1.jpg"
        price = data["data"]["products"][0]["salePriceU"] / 100
        brand = data["data"]["products"][0]["brand"]

        brand, created = Brand.objects.get_or_create(
            marketplace_id=1,
            name=brand,
        )

        product = {
            "title": title,
            "price": price,
            "cover": cover,
            "brand_id": brand.id,
        }
        return product

    @staticmethod
    def marketplace_id(marketplace):
        if marketplace == "Wildberries":
            return 1
        elif marketplace == "Ozon":
            return 2

    @staticmethod
    def is_link_exist(url):
        if "brands" in url:
            return "brand"
        elif "product" or "catolog" in url:
            return "product"
        else:
            return False

    @staticmethod
    def get_review_data(sku, skip=0, take=20, order="dateDesc", has_photo="false"):
        pretty_json = wb_api.WbHepler.get_part_review(int(skip), order, has_photo, sku)
        if not pretty_json["feedbacks"]:
            return [False, False]

        is_end = True if len(pretty_json["feedbacks"]) == 0 else False

        return [pretty_json, is_end]

    @staticmethod
    def get_sizes(sku):
        try:
            response = wb_api.WbHepler.cards_detail_request(sku)
            data = [
                i["origName"]
                for i in response["data"]["products"][0]["sizes"]
                if len(i["stocks"]) > 0
            ]
            return data
        except:
            return False

    @staticmethod
    def get_sku_for_question(sku):
        data = wb_api.WbHepler.cards_detail_request(sku)
        res = data["data"]["products"]
        if len(res) > 0:
            return True
        else:
            return False

    @staticmethod
    def get_qr_for_export(img):
        import base64
        import io
        from io import BytesIO

        from PIL import Image

        filename = "qr.png"

        buffer = io.BytesIO()
        img = Image.open(
            io.BytesIO(
                base64.decodebytes(
                    bytes(
                        (img).replace("data:image/png;base64,", ""),
                        "utf-8",
                    )
                )
            )
        )
        img = img.resize((80, 80))
        img.save("qr.png")
        image_file = open(filename, "rb")
        image_data = BytesIO(image_file.read())
        image_file.close()
        return image_data

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
