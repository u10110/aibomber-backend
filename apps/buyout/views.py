from django.shortcuts import render
from django.views import View
# Create your views here.
from django.http import HttpResponse

# from .models import Buyout


def index(request):
    return render(request, "apps/buyout2.html")

# def index(request):
#     # одна строка вместо тысячи слов на SQL
#     latest = Buyout.objects.order_by('-sku')[:10]
#     # latest = Buyout.objects.get(id=2)
#     # собираем тексты постов в один, разделяя новой строкой
#     # print(str(latest))
#     context = []
#     for item in latest:
#         context.append(item)
#         print(context)
#     context = {
#         'objects': context
#     }

#     print(context)
#     # return render(request, "index.html", {"posts": latest})
#     return render(request, "apps/buyout2.html", context)

# def create(request):
#     return render(request, "apps/buyout_create.html")

# def all(request):
#     print("asdgasd!!!!!!!!")
#     # одна строка вместо тысячи слов на SQL
#     latest = Buyout.objects.order_by('-sku')[:10]
#     # latest = Buyout.objects.get(id=2)
#     # собираем тексты постов в один, разделяя новой строкой
#     # print(str(latest))
#     context = []
#     for item in latest:
#         context.append(item)
#         print(context)
#     context = {
#         'objects': context
#     }

#     print(context)
#     # return render(request, "index.html", {"posts": latest})
#     return render(request, "apps/buyout2.html", context)

# def active(request):
#     print("asdgasd!!!!!!!!")
#     # одна строка вместо тысячи слов на SQL
#     latest = Buyout.objects.get(id=2)
#     # собираем тексты постов в один, разделяя новой строкой
#     # print(str(latest))
#     context = {
#         'objects': contexlatestt
#     }

#     print(context)
#     # return render(request, "index.html", {"posts": latest})
#     return render(request, "apps/buyout2.html", context)
