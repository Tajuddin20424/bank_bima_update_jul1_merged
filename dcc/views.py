from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.utils import timezone


# ===================== Patient Pages =====================

def patient_page(request):
    """Show list of all patients"""

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dcc_patient_info
            ORDER BY id DESC
        """)

        columns = [col[0] for col in cursor.description]

        patients = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return render(request, "dcc/patient_list.html", {
        "patients": patients
    })


def patient_report_page(request):
    """Show patient report form page"""

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dcc_patient_info
            ORDER BY id DESC
        """)

        columns = [col[0] for col in cursor.description]

        patients = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return render(request, "dcc/patient_report.html", {
        "patients": patients
    })


# ===================== Patient CRUD =====================

@csrf_exempt
def patient_store(request):
    """Create a new patient"""

    if request.method != "POST":
        return JsonResponse({
            "error": "Invalid request"
        }, status=400)

    data = request.POST

    query = """
        INSERT INTO dcc_patient_info (
            patient_name,
            father_husband_name,
            mother_name,
            parent_spouse_name,
            dob,
            age,
            sex,
            marital_status,
            nationality,
            passport_no,
            blood_group,
            country_of_birth,
            religion,
            occupation,
            weight,
            height,
            bmi,
            cause_visit_dcc,
            referral_source,
            referred_by,
            consulted_doctor,
            doctor_name,
            clinic_name,
            daily_routine,
            daily_diet,
            food_preferences,
            avoid_foods,
            diagnostic_reports,
            physical_condition,
            family_history,
            family_relation,
            physical_activity,
            diet,
            present_address,
            present_mobile,
            present_email,
            permanent_address,
            permanent_mobile,
            permanent_email,
            emergency_name,
            emergency_relation,
            emergency_phone,
            patient_signature,
            created_at,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
    """

    values = [
        data.get("patient_name"),
        data.get("father_husband_name"),
        data.get("mother_name"),
        data.get("parent_spouse_name"),
        data.get("dob") or None,
        data.get("age") or None,
        data.get("sex"),
        data.get("marital_status"),
        data.get("nationality"),
        data.get("passport_no"),
        data.get("blood_group"),
        data.get("country_of_birth"),
        data.get("religion"),
        data.get("occupation"),
        data.get("weight") or None,
        data.get("height") or None,
        data.get("bmi") or None,
        data.get("cause_visit_dcc"),
        data.get("referral_source"),
        data.get("referred_by"),
        data.get("consulted_doctor"),
        data.get("doctor_name"),
        data.get("clinic_name"),
        data.get("daily_routine"),
        data.get("daily_diet"),
        data.get("food_preferences"),
        data.get("avoid_foods"),
        data.get("diagnostic_reports"),
        data.get("physical_condition"),
        data.get("family_history"),
        data.get("family_relation"),
        data.get("physical_activity"),
        data.get("diet"),
        data.get("present_address"),
        data.get("present_mobile"),
        data.get("present_email"),
        data.get("permanent_address"),
        data.get("permanent_mobile"),
        data.get("permanent_email"),
        data.get("emergency_name"),
        data.get("emergency_relation"),
        data.get("emergency_phone"),
        data.get("patient_signature"),
        timezone.now(),
        timezone.now(),
    ]

    with connection.cursor() as cursor:
        cursor.execute(query, values)
        patient_id = cursor.lastrowid

    return JsonResponse({
        "success": True,
        "id": patient_id
    })


# ===================== Fetch Patient =====================

@csrf_exempt
def patient_fetch(request):

    patient_id = request.GET.get("id")

    if not patient_id:
        return JsonResponse({
            "error": "No ID provided"
        }, status=400)

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT *
            FROM dcc_patient_info
            WHERE id = %s
        """, [patient_id])

        row = cursor.fetchone()

        if not row:
            return JsonResponse({
                "error": "Patient not found"
            }, status=404)

        columns = [col[0] for col in cursor.description]

        data = dict(zip(columns, row))

    return JsonResponse(data)


# ===================== Update Patient =====================

@csrf_exempt
def patient_update(request, pk):

    if request.method != "POST":
        return JsonResponse({
            "error": "Invalid request"
        }, status=400)

    data = request.POST

    fields = [
        "patient_name",
        "father_husband_name",
        "mother_name",
        "parent_spouse_name",
        "dob",
        "age",
        "sex",
        "marital_status",
        "nationality",
        "passport_no",
        "blood_group",
        "country_of_birth",
        "religion",
        "occupation",
        "weight",
        "height",
        "bmi",
        "cause_visit_dcc",
        "referral_source",
        "referred_by",
        "consulted_doctor",
        "doctor_name",
        "clinic_name",
        "daily_routine",
        "daily_diet",
        "food_preferences",
        "avoid_foods",
        "diagnostic_reports",
        "physical_condition",
        "family_history",
        "family_relation",
        "physical_activity",
        "diet",
        "present_address",
        "present_mobile",
        "present_email",
        "permanent_address",
        "permanent_mobile",
        "permanent_email",
        "emergency_name",
        "emergency_relation",
        "emergency_phone",
        "patient_signature",
    ]

    update_parts = []
    values = []

    for field in fields:

        new_value = data.get(field)

        if new_value:
            update_parts.append(f"{field} = %s")
            values.append(new_value)

    if update_parts:

        update_parts.append("updated_at = %s")
        values.append(timezone.now())
        values.append(pk)

        query = f"""
            UPDATE dcc_patient_info
            SET {", ".join(update_parts)}
            WHERE id = %s
        """

        with connection.cursor() as cursor:
            cursor.execute(query, values)

    return JsonResponse({
        "success": True
    })


# ===================== Delete Patient =====================

@csrf_exempt
def patient_delete(request, pk):

    if request.method != "POST":
        return JsonResponse({
            "error": "Invalid request"
        }, status=400)

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT id
            FROM dcc_patient_info
            WHERE id = %s
        """, [pk])

        if not cursor.fetchone():
            return JsonResponse({
                "success": False,
                "error": "Patient not found"
            }, status=404)

        cursor.execute("""
            DELETE FROM dcc_patient_info
            WHERE id = %s
        """, [pk])

    return JsonResponse({
        "success": True
    })


# ===================== Patient Header Data =====================

def patient_data(request, id):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                patient_name,
                age,
                sex,
                cause_visit_dcc,
                doctor_name,
                bmi,
                physical_condition,
                present_mobile
            FROM dcc_patient_info
            WHERE id = %s
        """, [id])

        row = cursor.fetchone()

        if not row:
            return JsonResponse({
                "error": "Patient not found"
            }, status=404)

    data = {
        "Name": row[0],
        "Age": row[1],
        "Gender": row[2],
        "Reason": row[3],
        "ReferredBy": row[4] or "",
        "BMI": row[5] or "",
        "PhysicalCondition": row[6] or "",
        "PresentMobile": row[7] or "",
    }

    return JsonResponse(data)


# ===================== Prescription =====================

@csrf_exempt
def save_prescription(request):

    if request.method != "POST":
        return JsonResponse({
            "error": "Invalid request"
        }, status=400)

    patient_id = request.POST.get("patient_id")
    html_content = request.POST.get("html")

    if not patient_id or not html_content:
        return JsonResponse({
            "error": "Missing data"
        }, status=400)

    with connection.cursor() as cursor:

        cursor.execute("""
            INSERT INTO dcc_patient_pres (
                patient_id,
                html_content,
                created_at
            )
            VALUES (%s, %s, %s)
        """, [
            patient_id,
            html_content,
            timezone.now()
        ])

        prescription_id = cursor.lastrowid

    return JsonResponse({
        "status": "success",
        "id": prescription_id
    })


# ===================== Patient Prescriptions =====================

def patient_prescriptions(request, patient_id):

    with connection.cursor() as cursor:

        # Patient
        cursor.execute("""
            SELECT *
            FROM dcc_patient_info
            WHERE id = %s
        """, [patient_id])

        patient_row = cursor.fetchone()

        if not patient_row:
            return JsonResponse({
                "error": "Patient not found"
            }, status=404)

        patient_columns = [
            col[0] for col in cursor.description
        ]

        patient = dict(
            zip(patient_columns, patient_row)
        )

        # Prescriptions
        cursor.execute("""
            SELECT *
            FROM dcc_patient_pres
            WHERE patient_id = %s
            ORDER BY created_at DESC
        """, [patient_id])

        prescription_rows = cursor.fetchall()

        prescription_columns = [
            col[0] for col in cursor.description
        ]

        prescriptions = [
            dict(zip(prescription_columns, row))
            for row in prescription_rows
        ]

    return render(request, "dcc/prescriptions.html", {
        "patient": patient,
        "prescriptions": prescriptions
    })


# ===================== Prescription View =====================

def prescription_view(request, presc_id):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT html_content
            FROM dcc_patient_pres
            WHERE id = %s
        """, [presc_id])

        row = cursor.fetchone()

    if not row:
        return JsonResponse({
            "error": "Prescription not found"
        }, status=404)

    return JsonResponse({
        "html_content": row[0]
    })


# ===================== Prescription Delete =====================

@csrf_exempt
def prescription_delete(request, presc_id):

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Invalid request"
        })

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT id
            FROM dcc_patient_pres
            WHERE id = %s
        """, [presc_id])

        if not cursor.fetchone():
            return JsonResponse({
                "success": False,
                "error": "Prescription not found"
            }, status=404)

        cursor.execute("""
            DELETE FROM dcc_patient_pres
            WHERE id = %s
        """, [presc_id])

    return JsonResponse({
        "success": True
    })


# ===================== Report Template =====================

def load_report_template(request):

    report_type = request.GET.get("type")

    template_map = {
        "diet_plan": "dcc/report_templates/diet_plan.html",
        "regular_prescription": "report_templates/regular_prescription.html",
        "food_chart": "report_templates/food_chart.html",
    }

    template = template_map.get(report_type)

    if not template:
        return JsonResponse({
            "error": "Invalid report type"
        }, status=400)

    return render(request, template)