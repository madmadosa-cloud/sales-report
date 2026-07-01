from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("sales_analysis.urls")),
]

admin.site.site_header = "매출분석 시스템"
admin.site.site_title = "매출분석"
admin.site.index_title = "관리"
