from django.urls import path

from . import views


urlpatterns = [
    path("all-transaction-report/", views.all_transaction_report, name="all_transaction_report"),
    path("all-transaction-report/report/", views.all_transaction_report_pdf, name="all_transaction_report_pdf"),
]
