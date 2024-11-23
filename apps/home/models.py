from http import client

from django.db import models

from apps.authentication.models import User

# from sqlalchemy import null


class Proxy(models.Model):
    class Meta:
        verbose_name = "прокси"
        verbose_name_plural = "Прокси"

    # pvz_id = models.AutoField(primary_key=True)
    value = models.CharField(max_length=512)
    updated_at = models.DateTimeField(null=True, auto_now_add=True)


class Account(models.Model):
    # pvz_id = models.AutoField(primary_key=True)
    proxy = models.ForeignKey(Proxy, on_delete=models.CASCADE, related_name="Proxy")
    WILDAUTHNEW_V3 = models.CharField(null=True, max_length=1500)
    number = models.CharField(max_length=55)  # phone
    full_name = models.TextField()
    sex = models.IntegerField(null=True)
    status = models.CharField(max_length=512)
    updated_at = models.DateTimeField(null=True, auto_now_add=True)

    def __str__(self):
        return self.number


# DONE
class Marketplace(models.Model):

    name = models.CharField(max_length=100)  # ozon / wildberries
    updated_at = models.DateTimeField(auto_now_add=True)  # auto_now=True, blank=False

    def __str__(self):
        return self.name


class Brand(models.Model):
    class Meta:
        # indexes = [
        #     UniqueIndex(fields=['name']),
        # ]

        verbose_name = "брэнд"
        verbose_name_plural = "Брэнды"

    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.CASCADE, related_name="Brand", null=True
    )
    name = models.CharField(
        max_length=300,
        unique=True,
        null=True,
    )
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)


class TochkaNumbers(models.Model):
    phone = models.CharField(max_length=50)


class ClientSettings(models.Model):
    class Meta:
        verbose_name = "настройки"
        verbose_name_plural = "Настройки"

    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ClientSettings"
    )
    tg_chat_id = models.TextField(null=True, blank=True)
    tg_token = models.TextField(null=True, blank=True)
    wb_token = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, auto_now_add=True)
    tochka_number = models.ForeignKey(
        TochkaNumbers, on_delete=models.CASCADE, null=True
    )
    wb_updated = models.DateTimeField(null=True)


# DONE
class Pvz(models.Model):
    class Meta:
        verbose_name = "пвз"
        verbose_name_plural = "пвз"

    # pvz_id = models.AutoField(primary_key=True)
    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.CASCADE, related_name="Pvz"
    )
    # city = models.CharField(default=None, max_length=55)
    lat = models.CharField(max_length=100)
    lon = models.CharField(max_length=100)
    address = models.TextField()
    status = models.IntegerField(default=1)
    actual_status = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.address


class DBS(models.Model):
    # client = models.ForeignKey(User, on_delete=models.CASCADE)
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE)
    address = models.CharField(max_length=300)
    # country = models.CharField(max_length=100)
    # locality_type = models.CharField(max_length=100)
    # locality_name = models.CharField(max_length=100)
    # street = models.CharField(max_length=100)
    # building = models.IntegerField()
    # building_k = models.IntegerField(null=True)
    # building_s = models.IntegerField(null=True)
    apartament = models.IntegerField(null=True)
    entrance = models.IntegerField(null=True)
    intercom = models.IntegerField(null=True)
    floor = models.IntegerField(null=True)
    # region = models.CharField(max_length=100, null=True)
    updated_at = models.DateTimeField(auto_now_add=True)


# DONE
class ClientProduct(models.Model):
    # cleint_product_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ClientProduct"
    )
    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.CASCADE, related_name="ClientProduct"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="Brand", null=True
    )
    sku = models.CharField(max_length=55)
    title = models.TextField()
    cover = models.TextField()
    price = models.IntegerField()
    status = models.CharField(max_length=55)  # active / inactive
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.sku


# DONE
class ClientPvz(models.Model):
    class Meta:
        verbose_name = "пвз"
        verbose_name_plural = "Пвз"

    # client_pvz_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ClientPvz")
    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.CASCADE, related_name="ClientPvz"
    )
    pvz = models.ForeignKey(Pvz, on_delete=models.CASCADE, related_name="ClientPvz")
    sms_cloud = models.TextField(null=True)
    count_ordered = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now_add=True)


# DONE
class ClientCard(models.Model):
    # boost_basket_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ClientCard"
    )
    number = models.CharField(max_length=55)
    month = models.CharField(max_length=2)  # count for doing
    year = models.CharField(max_length=2)  # count of done
    cvc = models.CharField(max_length=3)  # done / process / error
    status = models.CharField(max_length=55)
    updated_at = models.DateTimeField(auto_now_add=True)
    # bank = models.CharField(max_length=100, default='Qiwi')


# DONE
class ProductBuyout(models.Model):
    # product_buyout_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ProductBuyout"
    )
    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.CASCADE, related_name="ProductBuyout"
    )
    product = models.ForeignKey(
        ClientProduct, on_delete=models.CASCADE, related_name="ProductBuyout"
    )
    pvz = models.ForeignKey(
        Pvz, on_delete=models.CASCADE, related_name="pvz", null=True
    )

    price_buy = models.IntegerField(null=True)
    size = models.TextField(null=True)
    sex = models.CharField(null=True, max_length=55)  # TODO remove null=true
    buyout_date = models.DateTimeField()
    key_phrase = models.TextField()
    code = models.CharField(max_length=55, null=True)
    status = models.CharField(max_length=55)  # active / inactive
    delivery_description = models.TextField(null=True)
    phone = models.CharField(null=True, max_length=10, blank=True)
    full_name = models.CharField(null=True, max_length=155, blank=True)
    check_number = models.CharField(null=True, max_length=155)
    screen = models.CharField(null=True, max_length=555)
    qr = models.TextField(null=True)
    dev_err = models.TextField(null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    is_dbs = models.BooleanField(null=False, default=0)
    dbs_address = models.ForeignKey(DBS, null=True, on_delete=models.CASCADE)
    pay_method = models.CharField(max_length=10, null=True)
    num_group = models.IntegerField(null=False, default=1)
    pay_type = models.CharField(default="no", max_length=10)
    tg_start_date = models.TimeField(null=True)
    tg_end_date = models.TimeField(null=True)
    payment_status = models.CharField(max_length=150, default="not_payed")
    rId = models.CharField(max_length=250, null=True)
    pay_check = models.CharField(max_length=555, null=True)
    orderId = models.CharField(max_length=250, null=True)
    payment_link = models.TextField(null=True)
    pay_link_generated = models.DateTimeField(null=True)

    def __str__(self):
        return self.product.sku

    class Meta:
        verbose_name = "выкуп"
        verbose_name_plural = "Выкупы"


# creating reviews
class AddingReview(models.Model):
    class Meta:
        verbose_name = "отзыв"
        verbose_name_plural = "Отзывы"

    # adding_review_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="AddingReview"
    )
    buyout = models.ForeignKey(
        ProductBuyout, on_delete=models.CASCADE, related_name="AddingReview"
    )
    review_date = models.DateTimeField(null=True)  # TODO remove null=true
    star = models.IntegerField()
    text = models.TextField()
    # photo = models.ImageField(null=True, upload_to='images/') # TODO add null=True
    image1 = models.ImageField(null=True, upload_to="images/")
    image2 = models.ImageField(null=True, upload_to="images/")
    image3 = models.ImageField(null=True, upload_to="images/")
    image4 = models.ImageField(null=True, upload_to="images/")
    image5 = models.ImageField(null=True, upload_to="images/")
    status = models.TextField(default="available")
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    status_description = models.TextField(null=True)


# DONE
class BoostLike(models.Model):
    class Meta:
        verbose_name = "лайк"
        verbose_name_plural = "Избранное"

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="BoostLike")
    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.CASCADE, related_name="BoostLike"
    )
    # product = models.ForeignKey(ClientProduct, on_delete=models.CASCADE, related_name="BoostLike")
    url = models.TextField()
    url_type = models.CharField(max_length=55)
    status = models.CharField(max_length=55)  # done / process / error
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    count = models.IntegerField(default=0)  # count for doing
    count_done = models.IntegerField(default=0)  # count of done
    account_phone = models.CharField(max_length=55, null=True)


class BoostLikeReview(models.Model):
    class Meta:
        verbose_name = "лайк"
        verbose_name_plural = "Лайки на отзывы"

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    action = models.CharField(max_length=15)
    text = models.CharField(max_length=50)
    sender_name = models.CharField(max_length=50)
    id_sender = models.CharField(max_length=20)
    url = models.TextField(null=True)
    status = models.CharField(max_length=55)  # active / done
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    product = models.ForeignKey(ClientProduct, on_delete=models.CASCADE)


class BoostQuestion(models.Model):
    class Meta:
        verbose_name = "вопрос"
        verbose_name_plural = "Вопросы"

    status = models.CharField(max_length=55, default="active")
    sku = models.CharField(max_length=55)
    question_text = models.CharField(max_length=1000)
    question_date = models.DateTimeField()
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    sex = models.IntegerField(null=True)
    product = models.ForeignKey(ClientProduct, on_delete=models.CASCADE, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)


class ReferralLinks(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "реферальная ссылка"
        verbose_name_plural = "Реферальные ссылки"


class ReferralClickCounter(models.Model):
    source = models.ForeignKey(ReferralLinks, on_delete=models.CASCADE)
    ip = models.CharField(max_length=100)


class ReferralUsers(models.Model):
    source = models.ForeignKey(ReferralLinks, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "реферальный пользователь"
        verbose_name_plural = "Реферальные пользователи"


class Phrase(models.Model):

    value = models.CharField(max_length=512)
    es_id = models.CharField(max_length=512, null=True)

    frequency = models.IntegerField(max_length=512)
    count_products = models.IntegerField(null=True)

    updated_at = models.DateField(auto_now=True, null=True)
    created_at = models.DateField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = "ключевая фраза"
        verbose_name_plural = "Ключевые фразы(все)"


class ClientPhrase(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="Phrase")
    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.CASCADE, related_name="Phrase"
    )
    product = models.ForeignKey(
        ClientProduct, on_delete=models.CASCADE, related_name="Phrase"
    )
    phrase = models.ManyToManyField(Phrase, related_name="Phrase", null=True)

    is_search_promotion = models.BooleanField(default=False)
    status = models.CharField(max_length=512, default=None)
    status_dev = models.CharField(max_length=512, null=True)

    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    stoped_at = models.DateTimeField(null=True)

    class Meta:
        verbose_name = "ключевая фраза"
        verbose_name_plural = "Ключевые фразы"


class AmoCrm(models.Model):
    website = models.JSONField()
    tg = models.JSONField()
