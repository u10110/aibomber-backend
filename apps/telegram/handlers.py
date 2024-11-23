from datetime import date, timedelta, datetime
from django.db.models import Q

from apps.home.models import ClientSettings, ProductBuyout, BoostLike, BoostLikeReview, BoostQuestion, AddingReview


def statistic_handler(serializer):
    start_time = serializer.validated_data["start_time"]
    user_tg_id = serializer.validated_data["tg_id"]
    client_settings = ClientSettings.objects.filter(tg_chat_id=user_tg_id).first()
    # user_limits = Limits.objects.filter(client=client_settings.client, end_date__gte=start_time).first()
    start_yesterday = datetime.today().replace(minute=0, hour=0, second=0, microsecond=0) - timedelta(days=1)
    end_yesterday = datetime.today().replace(minute=59, hour=23, second=59, microsecond=0) - timedelta(days=1)
    if start_time == start_yesterday:
        buyout = ProductBuyout.objects.filter(client=client_settings.client) \
            .filter(Q(status="delivery") & Q(buyout_date__gte=start_time) & Q(buyout_date__lte=end_yesterday)).count()
        likes = BoostLike.objects.filter(client=client_settings.client) \
            .filter(Q(status="done") & Q(buyout_date__gte=start_time) & Q(buyout_date__lte=end_yesterday)).count()
        like_reviews = BoostLikeReview.objects.filter(client=client_settings.client) \
            .filter(Q(status="done") & Q(buyout_date__gte=start_time) & Q(buyout_date__lte=end_yesterday)).count()
        questions = BoostQuestion.objects.filter(client=client_settings.client) \
            .filter(Q(status="done") & Q(buyout_date__gte=start_time) & Q(buyout_date__lte=end_yesterday)).count()
        reviews = AddingReview.objects.filter(client=client_settings.client) \
            .filter(Q(status="done") & Q(buyout_date__gte=start_time) & Q(buyout_date__lte=end_yesterday)).count()
    else:
        buyout = ProductBuyout.objects.filter(client=client_settings.client)\
            .filter(Q(status="delivery") & Q(buyout_date__gte=start_time)).count()
        likes = BoostLike.objects.filter(client=client_settings.client)\
            .filter(Q(status="done") & Q(updated_at__gte=start_time)).count()
        like_reviews = BoostLikeReview.objects.filter(client=client_settings.client) \
            .filter(Q(status="done") & Q(updated_at__gte=start_time)).count()
        questions = BoostQuestion.objects.filter(client=client_settings.client) \
            .filter(Q(status="done") & Q(updated_at__gte=start_time)).count()
        reviews = AddingReview.objects.filter(client=client_settings.client) \
            .filter(Q(status="done") & Q(updated_at__gte=start_time)).count()
    if not buyout:
        buyout = 0
    if not likes:
        likes = 0
    if not like_reviews:
        like_reviews = 0
    if not questions:
        questions = 0
    if not reviews:
        reviews = 0
    answer = {
        "start_time": start_time.date(),
        "end_time": date.today(),
        "buyout": buyout,
        "likes": likes,
        "feedback_likes": like_reviews,
        "questions": questions,
        "reviews": reviews
    }
    return answer
