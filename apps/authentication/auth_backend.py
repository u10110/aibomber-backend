from .models import User
from django.conf import settings
from django.contrib.auth.hashers import check_password


class PhoneAuthBackend():
    def authenticate(self, request, phone=None, password=None):
        try:
            user = User.objects.get(phone=phone)
            success = user.check_password(password)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            print('Not found User')
        except Exception as e:
            print(e)
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            return None
    
    def _get_group_permissions(self, user_obj):
        user_groups_field = get_user_model()._meta.get_field('groups')
        user_groups_query = 'group__%s' % user_groups_field.related_query_name()
        return Permission.objects.filter(**{user_groups_query: user_obj})
