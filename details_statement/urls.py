from django.urls import path

from . import views


urlpatterns = [
    path("details-statement/", views.details_statement, name="details_statement"),
    path("details-statement/report/", views.details_statement_pdf, name="details_statement_pdf"),
]
