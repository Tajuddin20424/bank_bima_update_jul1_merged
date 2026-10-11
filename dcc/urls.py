from django.urls import path
from . import views

urlpatterns = [
    # ===== Patient CRUD =====
    path('patients/', views.patient_page, name='patient_page'),                       # List all patients
    path('patients/store/', views.patient_store, name='patient_store'),              # Create new patient
    path('patients/fetch/', views.patient_fetch, name='patient_fetch'),              # Fetch patient info via GET?id=
    path('patients/<int:pk>/update/', views.patient_update, name='patient_update'), # Update patient
    path('patients/<int:pk>/delete/', views.patient_delete, name='patient_delete'), # Delete patient

    # ===== Patient Report Page =====
    path('patients/report/', views.patient_report_page, name='patient_report'),      # Report form page
    path('patients/<int:id>/data/', views.patient_data, name='patient_data'),        # Fetch old patient header data

    # ===== Prescriptions =====
    path('patients/prescriptions/save/', views.save_prescription, name='save_prescription'),  # Save prescription PDF
    path('patients/prescriptions/<int:patient_id>/', views.patient_prescriptions, name='patient_prescriptions'),  # List prescriptions for patient
    path('prescriptions/view/<int:presc_id>/', views.prescription_view, name='prescription_view'),  # View a single prescription
    path('prescriptions/delete/<int:presc_id>/', views.prescription_delete, name='prescription_delete'),  # Delete a prescription
    path('patients/prescriptions/<int:patient_id>/', views.patient_prescriptions, name='patient_prescriptions'),

    path('load-report-template/', views.load_report_template, name="load_report_template"),
]