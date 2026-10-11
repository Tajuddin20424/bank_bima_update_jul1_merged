from django.db import models

class PatientInfo(models.Model):
    id = models.AutoField(primary_key=True)
    patient_name = models.CharField(max_length=255)
    father_husband_name = models.CharField(max_length=255, blank=True, null=True)
    mother_name = models.CharField(max_length=255, blank=True, null=True)
    parent_spouse_name = models.CharField(max_length=255, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    sex = models.CharField(max_length=10, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    passport_no = models.CharField(max_length=50, blank=True, null=True)
    blood_group = models.CharField(max_length=5, blank=True, null=True)
    country_of_birth = models.CharField(max_length=100, blank=True, null=True)
    religion = models.CharField(max_length=50, blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)
    height = models.FloatField(blank=True, null=True)
    bmi = models.FloatField(blank=True, null=True)

    # Text/comment-like fields
    cause_visit_dcc = models.TextField(blank=True, null=True)
    referral_source = models.TextField(blank=True, null=True)
    referred_by = models.TextField(blank=True, null=True)
    consulted_doctor = models.TextField(blank=True, null=True)
    doctor_name = models.TextField(blank=True, null=True)
    clinic_name = models.TextField(blank=True, null=True)
    daily_routine = models.TextField(blank=True, null=True)
    daily_diet = models.TextField(blank=True, null=True)
    food_preferences = models.TextField(blank=True, null=True)
    avoid_foods = models.TextField(blank=True, null=True)
    diagnostic_reports = models.TextField(blank=True, null=True)
    physical_condition = models.CharField(max_length=100, blank=True, null=True)
    family_history = models.CharField(max_length=10, blank=True, null=True)  # Yes/No
    family_relation = models.TextField(blank=True, null=True)  # multiple choice as text
    physical_activity = models.TextField(blank=True, null=True)
    diet = models.TextField(blank=True, null=True)

    present_address = models.TextField(blank=True, null=True)
    present_mobile = models.CharField(max_length=20, blank=True, null=True)
    present_email = models.EmailField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    permanent_mobile = models.CharField(max_length=20, blank=True, null=True)
    permanent_email = models.EmailField(blank=True, null=True)

    emergency_name = models.CharField(max_length=255, blank=True, null=True)
    emergency_relation = models.CharField(max_length=100, blank=True, null=True)
    emergency_phone = models.CharField(max_length=20, blank=True, null=True)
    patient_signature = models.TextField(blank=True, null=True)  # could store signature as base64 or file path

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_info"   

    def __str__(self):
        return self.patient_name
    
class Prescription(models.Model):
    patient = models.ForeignKey("PatientInfo", on_delete=models.CASCADE)  # <-- ঠিক নাম
    pdf_file = models.FileField(upload_to="prescriptions/")
    html_content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dcc_patient_pres"