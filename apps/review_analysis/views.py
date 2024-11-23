import json
import time
import codecs
import csv
import xlsxwriter

from io import BytesIO
from django.shortcuts import render
from .models import ReviewsAnalysis
from apps.home.models import ClientProduct
from apps.home.helper import Helper
from apps.home.services.elastic import ES
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from .services.rabbitmq import RabbitMqServerConfigure, RabbitmqServer


def review_tasks(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        for sku in data['sku_list']:
            marketplace_id = Helper.marketplace_id("Wildberries")
            if ClientProduct.objects.filter(
                    sku=sku, client_id=request.user.id
            ).exists():
                continue
            product = Helper.check_sku(sku, marketplace_id)
            if not product:
                return JsonResponse({"status": "sku error"}, status=200)
            ClientProduct(sku=sku,
                          title=product["title"],
                          cover=product["cover"],
                          price=product["price"],
                          client_id=request.user.id,
                          marketplace_id=marketplace_id,
                          brand_id=product["brand_id"]).save()
        server_configure = RabbitMqServerConfigure()
        server = RabbitmqServer(server=server_configure)
        new_task = ReviewsAnalysis(sku_list=data['sku_list'], client=request.user, status='active')
        new_task.save()

        try:
            server.publish("wb_scrapper_review_qd", {"task_id": new_task.id})
        except:
            new_task.delete()
            return JsonResponse({"status": "error"}, status=200)

        return JsonResponse({"status": "ok"}, status=200)

    context = {}
    review_list = []
    for instanse in ReviewsAnalysis.objects.filter(client=request.user):
        sku_list = []
        for sku in instanse.sku_list:
            product = ClientProduct.objects.get(sku=sku, client_id=request.user)
            sku_list.append(
                {
                    "title": product.title,
                    "cover": product.cover,
                    "sku": product.sku
                }
            )
        review_list.append(
            {
                "id": instanse.id,
                "status": instanse.status,
                "date": instanse.created_at.date(),
                "numb_reviews": instanse.numb_reviews,
                "average_rate": instanse.average_rate,
                "sku_list": sku_list,
                "current": str(len(review_list) + 1)
            }
        )
    context["reviews"] = review_list
    return render(request, "review_analysis/review_analytics.html", context=context)


def review_details(request, pk):
    review = ReviewsAnalysis.objects.get(id=pk)
    sku_list = []
    for sku in review.sku_list:
        roots_sku = []
        product = ClientProduct.objects.get(sku=sku, client_id=request.user)
        es = ES()
        try:
            response = es.get_phrases(sku)
        except Exception:
            return HttpResponseRedirect('/review-analysis')
        for root in response['_source']['roots']:
            roots_sku.append(
                {
                    "sku": sku,
                    "root": root["root"],
                    "type": root["type"],
                    "count": root["count"],
                    "phrases": root["word-phrases"][0],
                }
            )
        sku_list.append(
            {
                "title": product.title,
                "cover": product.cover,
                "sku": product.sku,
                "price": product.price,
                "average_rate": response['_source']['average_rate'],
                "feedbacks": response['_source']['feedbacks_count'],
                "feedbacks_photo": response['_source']['feedbacks_photo'],
                "roots": roots_sku
            }
        )
    context = {
        "products": sku_list
    }

    return render(request, "review_analysis/product_review.html", context=context)


def delete_task(request):
    if request.method == 'POST':
        task_id = json.loads(request.body)
        ReviewsAnalysis.objects.filter(id=task_id['task_id']).delete()
        return JsonResponse({"message": True})


def check_task(request):
    if request.method == 'POST':
        task_list = json.loads(request.body)
        response = {}
        for task_id in task_list['ids_list']:
            task = ReviewsAnalysis.objects.get(id=task_id)
            if task.status == 'active':
                continue
            response[task_id] = [task.average_rate, task.numb_reviews]
        return JsonResponse({"message": response})


def export_tasks(request):
    file_type = request.GET.get("type")
    task_id = request.GET.get("taskId")
    if file_type == "csv":
        response = HttpResponse(content_type="text/csv")
        response.write(codecs.BOM_UTF8)
        response["Content-Disposition"] = f'attachment; filename="mplab.csv"'
    elif file_type == "xlsx":
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, options={"remove_timezone": True})
        worksheet = workbook.add_worksheet()
        row_num = 0
    columns = [
        "Артикул",
        "Ключевое слово",
        "Тип",
        "Количество",
        "Фраза"
    ]
    if file_type == "csv":
        writer = csv.writer(response, delimiter=",")
        writer.writerow(columns)
    elif file_type == "xlsx":
        for col_num in range(len(columns)):
            worksheet.write(row_num, col_num, columns[col_num])
    review = ReviewsAnalysis.objects.get(id=task_id)
    for sku in review.sku_list:
        es = ES()
        roots = es.get_phrases(sku)
        if file_type == "csv":
            for root in roots['_source']['roots']:
                writer.writerow([
                    sku,
                    root["root"],
                    root["type"],
                    root["count"],
                    root["word-phrases"][0]
                ])
        elif file_type == "xlsx":
            for root in roots['_source']['roots']:
                row = [
                    sku,
                    root["root"],
                    root["type"],
                    root["count"],
                    root["word-phrases"][0],
                ]
                row_num += 1
                for col_num, cell_value in enumerate(row, 0):
                    worksheet.write(row_num, col_num, cell_value)
            workbook.close()
            response = HttpResponse(content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = f'attachment; filename="mplab.xlsx"'
            response.write(output.getvalue())
        return response
# Create your views here.
