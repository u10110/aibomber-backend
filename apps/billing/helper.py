from .models import Limits, UnicTariff, Order
import datetime

class Helper():

    def __init__(self, user_id=None):
        if user_id is not None:
            date_now = datetime.datetime.now(datetime.timezone.utc)
            try:
                self.limits = Limits.objects.get(
                    client_id=user_id, start_date__lte=date_now, end_date__gte=date_now
                )
            except:
                self.limits = None

    def get_max_limit(self, column_name):
        limits = self.limits
        if limits != None:
            order = limits.paid_info.order

            if order.is_calculated:
                tariff_info = order.calculated_tariff
            else:
                tariff_info = UnicTariff.objects.get(title=order.tariff)

            limit = getattr(tariff_info, column_name)

            for current_order in Order.objects.filter(prolongation_to=order.id, paid_status=True):
                tariff_info = current_order.calculated_tariff
                field_value = getattr(tariff_info, column_name)
                if isinstance(field_value, (int, float, complex)) and not isinstance(field_value, bool):
                    limit += field_value
                else:
                    if limit == False and field_value == True:
                        return True
            return limit
        else:
            return False
        

    def validate_calculator(data):
        redemptions = int(data['redemptions'])
        reviews =  int(data['reviews'])
        likes = int(data['likes'])
        questions = int(data['questions'])
        like_review_limit = int(data['likes-on-reviews'])
        search_promotion = int(data['search_promotion']) if 'search_promotion' in data else 0
        monitor = int(data['monitor'])
        monitoring_kz = int(data['monitoring_kz']) if 'monitoring_kz' in data else 0
        adv_company = int(data['adv_company']) if 'adv_company' in data else 0
        monitoring_rate = int(data['rate-monitoring']) if 'rate-monitoring' in data else 0
        course = int(data['course']) if 'course' in data else 0
        price = 0

        if 0 <= redemptions <= 10000:
            if redemptions < 150:
                price += redemptions*55
            elif redemptions < 450:
                price += redemptions*40
            elif redemptions < 1800:
                price += redemptions*25
            else:
                price += redemptions*15
        else:
            return False
        
        if 0 <= reviews <= 3000:
            if reviews < 30:
                price += reviews*55
            elif reviews < 90:
                price += reviews*40
            elif reviews < 360:
                price += reviews*25
            else:
                price += reviews*15
        else:
            return False
        
        if 0 <= likes <= 10000:
            if likes < 150:
                price += likes*5
            elif likes < 450:
                price += likes*4
            elif likes < 1800:
                price += likes*3
            else:
                price += int(likes*2.5)
        else:
            return False
        
        if 0 <= questions <= 3000:
            if questions < 30:
                price += questions*5
            elif questions < 90:
                price += questions*4
            elif questions < 360:
                price += questions*3
            else:
                price += int(questions*2.5)
        else:
            return False
        
        if 0 <= like_review_limit <= 5000:
            if like_review_limit < 70:
                price += like_review_limit*8
            elif like_review_limit < 210:
                price += like_review_limit*6
            elif like_review_limit < 840:
                price += like_review_limit*4
            else:
                price += like_review_limit*3
        else:
            return False
        
        if 0 <= search_promotion <= 2:
            price += search_promotion*10000
        elif 3 <= search_promotion <= 9:
            price += search_promotion*8000
        elif search_promotion >= 10:
            price += search_promotion*7000
        else:
            return False
        
        if monitor >= 0:
            if monitor == 1:
                price += monitor*300
            elif monitor < 4:
                price += monitor*250
            elif monitor < 10:
                price += monitor*200
            else:
                price += monitor*150
        else:
            return False
        
        if monitoring_kz >= 0:
            if monitoring_kz == 1:
                price += monitoring_kz*100
            elif monitoring_kz < 5:
                price += monitoring_kz*70
            elif monitoring_kz < 30:
                price += monitoring_kz*55
            else:
                price += monitoring_kz*35
        else:
            return False

        if adv_company >= 0:
            if adv_company == 1:
                price += adv_company*2990
            elif adv_company < 3:
                price += adv_company*2390
            elif adv_company < 7:
                price += adv_company*1590
            else:
                price += adv_company*1290
        else:
            return False
        
        if 0 <= monitoring_rate <= 1:
            price += monitoring_rate*500
        else:
            return False
        
        if 0 <= course <= 1:
            price += course*5000


        return price
