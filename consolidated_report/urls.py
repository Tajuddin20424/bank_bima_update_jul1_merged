from django.urls import path
from . import views

urlpatterns = [
    path("consolidated-report/", views.consolidated_report, name="consolidated_report"),
    path("consolidated-report/report/", views.consolidated_report_pdf, name="consolidated_report_pdf"),
]
