from django.urls import path

from sales_analysis import views

app_name = "sales_analysis"

urlpatterns = [
    path("", views.index, name="index"),
    path("upload/", views.upload_sales, name="upload"),
    path("upload/confirm/", views.confirm_upload, name="upload_confirm"),
    path("report/generate/", views.generate_report, name="report_generate"),
    path("report/generate/simple/", views.generate_simple_report, name="report_generate_simple"),
    path("report/download/excel/", views.download_excel, name="download_excel"),
    path("report/download/pdf/", views.download_pdf, name="download_pdf"),
    path("unclassified/", views.unclassified_list, name="unclassified"),
]
