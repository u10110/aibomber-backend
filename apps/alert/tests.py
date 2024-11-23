from apps.alert.services.services import (BuyoutManager, FavoriteManager,
                                          FavoriteReviewManager, QuestionManager,
                                          ReivewManager)
from apps.home.models import (
    ProductBuyout,
)


def test_buyout(buyout_id, payment_type):
    buyout = ProductBuyout.objects.get(id=buyout_id)
    data = {
        "buyout_id": buyout.id,
        "link_type": payment_type,
        "sex": int(buyout.sex),
        "sku": int(buyout.product.sku),
        "AddressId": buyout.pvz.status,
        "Pay_checker": "yes",
    }
    buyout_manager = BuyoutManager(data)
    link = buyout_manager.get_pay_link()
    assert True


def test_review(review_id):
    review_manager = ReivewManager(review_id)
    response = review_manager.add_review()
    assert True


def test_question(favorite_id):
    question_manager = QuestionManager(favorite_id)
    response = question_manager.question_add()
    assert True


def test_favorite_add(favorite_id):
    favorite_manager = FavoriteManager(favorite_id)
    response = favorite_manager.add_favorite()
    assert True


def test_favorite_review_add(favorite_id):
    favorite_manager = FavoriteReviewManager(favorite_id)
    response = favorite_manager.add_favorite()
    assert True
