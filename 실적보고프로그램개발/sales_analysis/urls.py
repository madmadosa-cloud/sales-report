from django.urls import path



from sales_analysis import master_views, profit_views, views, welfare_views



app_name = "sales_analysis"



urlpatterns = [

    path("", views.index, name="index"),

    path("upload/", views.upload_sales, name="upload"),

    path("upload/confirm/", views.confirm_upload, name="upload_confirm"),

    path("report/generate/", views.generate_report, name="report_generate"),

    path("report/generate/simple/", views.generate_simple_report, name="report_generate_simple"),
    path("report/generate/welfare/", views.generate_welfare_report, name="report_generate_welfare"),
    path("report/generate/final/", views.generate_final_report, name="report_generate_final"),

    path("report/download/excel/", views.download_excel, name="download_excel"),

    path("report/download/pdf/", views.download_pdf, name="download_pdf"),

    path("unclassified/", views.unclassified_list, name="unclassified"),

    path("master/", master_views.category_master, name="category_master"),

    path("master/items/", master_views.item_category_list, name="item_category_list"),

    path("master/items/add/", master_views.item_category_create, name="item_category_create"),

    path("master/items/<str:code>/edit/", master_views.item_category_update, name="item_category_update"),

    path("master/items/<str:code>/delete/", master_views.item_category_delete, name="item_category_delete"),

    path("master/items/upload/", master_views.item_category_upload, name="item_category_upload"),

    path("master/items/upload/confirm/", master_views.item_category_upload_confirm, name="item_category_upload_confirm"),

    path("master/customers/", master_views.customer_category_list, name="customer_category_list"),

    path("master/customers/add/", master_views.customer_category_create, name="customer_category_create"),

    path("master/customers/<str:code>/edit/", master_views.customer_category_update, name="customer_category_update"),

    path("master/customers/<str:code>/delete/", master_views.customer_category_delete, name="customer_category_delete"),

    path("master/customers/upload/", master_views.customer_category_upload, name="customer_category_upload"),

    path(

        "master/customers/upload/confirm/",

        master_views.customer_category_upload_confirm,

        name="customer_category_upload_confirm",

    ),

    path("master/welfare/", welfare_views.welfare_category_master, name="welfare_category_master"),

    path("master/welfare/items/", welfare_views.welfare_output_list, name="welfare_output_list"),

    path("master/welfare/items/add/", welfare_views.welfare_output_create, name="welfare_output_create"),

    path("master/welfare/items/<str:code>/edit/", welfare_views.welfare_output_update, name="welfare_output_update"),

    path("master/welfare/items/<str:code>/delete/", welfare_views.welfare_output_delete, name="welfare_output_delete"),

    path("profit/", profit_views.profit_index, name="profit_index"),
    path("profit/upload/", profit_views.upload_profit, name="profit_upload"),
    path("profit/upload/confirm/", profit_views.confirm_profit_upload, name="profit_upload_confirm"),
    path("profit/report/generate/", profit_views.generate_profit_report, name="profit_report_generate"),
    path(
        "profit/report/generate/welfare/",
        profit_views.generate_profit_welfare_report,
        name="profit_report_generate_welfare",
    ),
    path(
        "profit/report/generate/final/",
        profit_views.generate_profit_final_report,
        name="profit_report_generate_final",
    ),
    path("profit/report/download/excel/", profit_views.download_profit_excel, name="profit_download_excel"),
    path("profit/report/download/pdf/", profit_views.download_profit_pdf, name="profit_download_pdf"),

]


