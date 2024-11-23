from django.contrib import admin
from .models import ReviewsAnalysis


class ReviewsAnalysisAdmin(admin.ModelAdmin):
    list_display = [field.name for field in ReviewsAnalysis._meta.get_fields()]


admin.site.register(ReviewsAnalysis, ReviewsAnalysisAdmin)
# Register your models here.
