from datetime import datetime
from io import BytesIO
import json
import traceback  # CRITICAL FIX: Explicitly imported to avoid NameError
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.db import connection, transaction
from django.utils import timezone
from django.utils.html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.barcode import code128
from administrator.views import dictfetchall

from django.http import JsonResponse
from django.db.models import Q
from doctors.models import Doctor
from sr.models import SalesRepresentative # Apnar model framework accurate mapping check korben
from django.views.decorators.csrf import csrf_exempt

# =========================================================================
# 🛠️ CORE DICTIONARY DATA FETCH ROW WRAPPERS (RAW SQL)
# =========================================================================
def dict_fetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def dict_fetchone(cursor):
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if row:
        return dict(zip(columns, row))
    return None


DIAGNOSIS_MAIN_HEAD_ID = 10


def referral_setup_page(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, COALESCE(custom_doc_id, CONCAT('DOC', LPAD(id, 9, '0'))) AS code, name, specialization AS meta, chamber AS extra
            FROM doctors_info
            WHERE is_active = 1
            ORDER BY name ASC
        """)
        doctors = dict_fetchall(cursor)
    return render(request, 'diagnosis/referral_setup.html', {
        'providers': doctors,
        'provider_label': 'Doctor',
        'provider_meta_label': 'Specialization',
        'provider_extra_label': 'Chamber',
        'referral_tests_url': '/diagnosis/referral/tests/',
        'referral_saved_groups_url': '/diagnosis/referral/saved-groups/',
        'referral_save_url': '/diagnosis/referral/save/',
        'referral_copy_url': '/diagnosis/referral/copy/',
        'referral_success_message': 'Doctor referral setup updated successfully',
        'referral_copy_success_message': 'Doctor referral setup copied successfully',
    })


def referral_sr_setup_page(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, COALESCE(custom_sr_id, CONCAT('SR', LPAD(id, 10, '0'))) AS code, name, company_name AS meta, commission_percentage AS extra
            FROM item__sr_agents
            WHERE is_active = 1
            ORDER BY name ASC
        """)
        sr_agents = dict_fetchall(cursor)
    return render(request, 'diagnosis/referral_setup.html', {
        'providers': sr_agents,
        'provider_label': 'SR',
        'provider_meta_label': 'Company',
        'provider_extra_label': 'Commission',
        'referral_tests_url': '/diagnosis/referral/sr/tests/',
        'referral_saved_groups_url': '/diagnosis/referral/sr/saved-groups/',
        'referral_save_url': '/diagnosis/referral/sr/save/',
        'referral_copy_url': '/diagnosis/referral/sr/copy/',
        'referral_success_message': 'SR referral setup updated successfully',
        'referral_copy_success_message': 'SR referral setup copied successfully',
    })


def referral_group_combo(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, tran_groupe_name AS name
            FROM transaction__groupes
            WHERE tran_groupe_type = %s AND status = 1
            ORDER BY tran_groupe_name ASC
        """, [DIAGNOSIS_MAIN_HEAD_ID])
        groups = dict_fetchall(cursor)
    return JsonResponse({'groups': groups})


def referral_tests_by_group(request):
    doc_id = request.GET.get('doc_id')
    group_id = request.GET.get('group_id')
    if not group_id:
        return JsonResponse({'success': False, 'message': 'Group required'}, status=400)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT h.id, h.tran_head_name AS name, h.mrp,
                   COALESCE(r.ref_type, 'tk') AS ref_type,
                   COALESCE(r.ref_rate, 0) AS ref_rate,
                   COALESCE(r.status, 0) AS selected
            FROM transaction__heads h
            LEFT JOIN referral_setup r
              ON r.tran_head_id = h.id AND r.group_id = h.groupe_id AND r.doc_id = %s
            WHERE h.groupe_id = %s AND h.status = 1
            ORDER BY h.tran_head_name ASC
        """, [doc_id or 0, group_id])
        tests = dict_fetchall(cursor)
    return JsonResponse({'success': True, 'tests': tests})


def referral_saved_groups(request):
    doc_id = request.GET.get('doc_id')
    if not doc_id:
        return JsonResponse({'success': False, 'message': 'Doctor required'}, status=400)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT r.group_id, g.tran_groupe_name AS group_name
            FROM referral_setup r
            JOIN transaction__groupes g ON g.id = r.group_id
            WHERE r.doc_id = %s AND r.status = 1
            ORDER BY g.tran_groupe_name ASC
        """, [doc_id])
        groups = dict_fetchall(cursor)
    return JsonResponse({'success': True, 'groups': groups})


def referral_sr_tests_by_group(request):
    sr_id = request.GET.get('doc_id')
    group_id = request.GET.get('group_id')
    if not group_id:
        return JsonResponse({'success': False, 'message': 'Group required'}, status=400)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT h.id, h.tran_head_name AS name, h.mrp,
                   COALESCE(r.ref_type, 'tk') AS ref_type,
                   COALESCE(r.ref_rate, 0) AS ref_rate,
                   COALESCE(r.status, 0) AS selected
            FROM transaction__heads h
            LEFT JOIN referral_setup_sr r
              ON r.tran_head_id = h.id AND r.group_id = h.groupe_id AND r.sr_id = %s
            WHERE h.groupe_id = %s AND h.status = 1
            ORDER BY h.tran_head_name ASC
        """, [sr_id or '', group_id])
        tests = dict_fetchall(cursor)
    return JsonResponse({'success': True, 'tests': tests})


def referral_sr_saved_groups(request):
    sr_id = request.GET.get('doc_id')
    if not sr_id:
        return JsonResponse({'success': False, 'message': 'SR required'}, status=400)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT r.group_id, g.tran_groupe_name AS group_name
            FROM referral_setup_sr r
            JOIN transaction__groupes g ON g.id = r.group_id
            WHERE r.sr_id = %s AND r.status = 1
            ORDER BY g.tran_groupe_name ASC
        """, [sr_id])
        groups = dict_fetchall(cursor)
    return JsonResponse({'success': True, 'groups': groups})


@csrf_exempt
def save_referral_setup(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        doc_id = payload.get('doc_id')
        group_id = payload.get('group_id')
        rows = payload.get('rows', [])
        if not doc_id or not group_id:
            return JsonResponse({'success': False, 'message': 'Doctor and group required'}, status=400)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE referral_setup SET status = 0 WHERE doc_id = %s AND group_id = %s", [doc_id, group_id])
                for row in rows:
                    tran_head_id = row.get('tran_head_id')
                    ref_type = row.get('ref_type') if row.get('ref_type') in ['tk', 'percent'] else 'tk'
                    ref_rate = row.get('ref_rate') or 0
                    status = 1 if row.get('selected') else 0
                    if not tran_head_id:
                        continue
                    cursor.execute("""
                        INSERT INTO referral_setup (doc_id, group_id, tran_head_id, ref_type, ref_rate, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE ref_type = VALUES(ref_type), ref_rate = VALUES(ref_rate), status = VALUES(status)
                    """, [doc_id, group_id, tran_head_id, ref_type, ref_rate, status])
        return JsonResponse({'success': True})
    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


@csrf_exempt
def copy_referral_setup(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        source_doc_id = payload.get('source_doc_id')
        target_doc_id = payload.get('target_doc_id')
        if not source_doc_id or not target_doc_id or str(source_doc_id) == str(target_doc_id):
            return JsonResponse({'success': False, 'message': 'Valid source and target doctor required'}, status=400)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE referral_setup SET status = 0 WHERE doc_id = %s", [target_doc_id])
                cursor.execute("""
                    INSERT INTO referral_setup (doc_id, group_id, tran_head_id, ref_type, ref_rate, status)
                    SELECT %s, group_id, tran_head_id, ref_type, ref_rate, status
                    FROM referral_setup
                    WHERE doc_id = %s AND status = 1
                    ON DUPLICATE KEY UPDATE ref_type = VALUES(ref_type), ref_rate = VALUES(ref_rate), status = VALUES(status)
                """, [target_doc_id, source_doc_id])
        return JsonResponse({'success': True})
    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


@csrf_exempt
def save_referral_sr_setup(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        sr_id = payload.get('doc_id')
        group_id = payload.get('group_id')
        rows = payload.get('rows', [])
        if not sr_id or not group_id:
            return JsonResponse({'success': False, 'message': 'SR and group required'}, status=400)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE referral_setup_sr SET status = 0 WHERE sr_id = %s AND group_id = %s", [sr_id, group_id])
                for row in rows:
                    tran_head_id = row.get('tran_head_id')
                    ref_type = row.get('ref_type') if row.get('ref_type') in ['tk', 'percent'] else 'tk'
                    ref_rate = row.get('ref_rate') or 0
                    status = 1 if row.get('selected') else 0
                    if not tran_head_id:
                        continue
                    cursor.execute("""
                        INSERT INTO referral_setup_sr (sr_id, group_id, tran_head_id, ref_type, ref_rate, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE ref_type = VALUES(ref_type), ref_rate = VALUES(ref_rate), status = VALUES(status)
                    """, [sr_id, group_id, tran_head_id, ref_type, ref_rate, status])
        return JsonResponse({'success': True})
    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


@csrf_exempt
def copy_referral_sr_setup(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        source_sr_id = payload.get('source_doc_id')
        target_sr_id = payload.get('target_doc_id')
        if not source_sr_id or not target_sr_id or str(source_sr_id) == str(target_sr_id):
            return JsonResponse({'success': False, 'message': 'Valid source and target SR required'}, status=400)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE referral_setup_sr SET status = 0 WHERE sr_id = %s", [target_sr_id])
                cursor.execute("""
                    INSERT INTO referral_setup_sr (sr_id, group_id, tran_head_id, ref_type, ref_rate, status)
                    SELECT %s, group_id, tran_head_id, ref_type, ref_rate, status
                    FROM referral_setup_sr
                    WHERE sr_id = %s AND status = 1
                    ON DUPLICATE KEY UPDATE ref_type = VALUES(ref_type), ref_rate = VALUES(ref_rate), status = VALUES(status)
                """, [target_sr_id, source_sr_id])
        return JsonResponse({'success': True})
    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


def referral_report_page(request):
    return render(request, 'diagnosis/referral_report.html')


def referral_report_providers(request):
    report_type = request.GET.get('report_type')
    if report_type == 'sr':
        sql = """
            SELECT COALESCE(custom_sr_id, CONCAT('SR', LPAD(id, 10, '0'))) AS code, name
            FROM item__sr_agents WHERE is_active = 1 ORDER BY name ASC
        """
    else:
        sql = """
            SELECT COALESCE(custom_doc_id, CONCAT('DOC', LPAD(id, 9, '0'))) AS code, name
            FROM doctors_info WHERE is_active = 1 ORDER BY name ASC
        """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        providers = dict_fetchall(cursor)
    return JsonResponse({'success': True, 'providers': providers})


def _referral_report_rows(report_type, provider_id, start_date, end_date):
    setup_table = 'referral_setup_sr' if report_type == 'sr' else 'referral_setup'
    provider_column = 'td.sr_id' if report_type == 'sr' else 'td.doctor_id'
    setup_provider_column = 'rs.sr_id' if report_type == 'sr' else 'rs.doc_id'

    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT
                td.tran_id, DATE(td.tran_date) AS tran_date, COALESCE(td.tran_groupe_id, th.groupe_id) AS group_id,
                COALESCE(tg.tran_groupe_name, '-') AS group_name,
                th.tran_head_name, COALESCE(td.mrp, td.amount, 0) AS test_tk,
                COALESCE(td.discount, 0) AS discount, COALESCE(rs.ref_type, '-') AS ref_type,
                COALESCE(rs.ref_rate, 0) AS ref_rate,
                CASE
                    WHEN rs.ref_type = 'percent' THEN ROUND((COALESCE(td.mrp, td.amount, 0) * COALESCE(rs.ref_rate, 0)) / 100, 2)
                    WHEN rs.ref_type = 'tk' THEN ROUND(COALESCE(rs.ref_rate, 0), 2)
                    ELSE 0
                END AS referral_amount
            FROM transaction__details td
            LEFT JOIN transaction__mains tm ON tm.tran_id = td.tran_id
            LEFT JOIN transaction__heads th ON th.id = td.tran_head_id
            LEFT JOIN transaction__groupes tg ON tg.id = COALESCE(td.tran_groupe_id, th.groupe_id)
            LEFT JOIN {setup_table} rs ON {setup_provider_column} = {provider_column}
                AND rs.group_id = COALESCE(td.tran_groupe_id, th.groupe_id)
                AND rs.tran_head_id = td.tran_head_id
                AND rs.status = 1
            WHERE td.tran_type = %s
              AND {provider_column} = %s
              AND DATE(td.tran_date) BETWEEN %s AND %s
              AND td.status = 1
              AND COALESCE(td.due, 0) = 0
              AND COALESCE(tm.due, 0) = 0
            ORDER BY td.tran_date ASC, td.tran_id ASC
        """, [DIAGNOSIS_MAIN_HEAD_ID, provider_id, start_date, end_date])
        rows = dict_fetchall(cursor)
    return rows


def _referral_report_totals(rows):
    return {
        'total_referral': sum(float(row.get('referral_amount') or 0) for row in rows),
        'total_test_tk': sum(float(row.get('test_tk') or 0) for row in rows),
        'total_discount': sum(float(row.get('discount') or 0) for row in rows),
    }


def _referral_provider_name(report_type, provider_id):
    if report_type == 'sr':
        sql = "SELECT name FROM item__sr_agents WHERE COALESCE(custom_sr_id, CONCAT('SR', LPAD(id, 10, '0'))) = %s LIMIT 1"
    else:
        sql = "SELECT name FROM doctors_info WHERE COALESCE(custom_doc_id, CONCAT('DOC', LPAD(id, 9, '0'))) = %s LIMIT 1"
    with connection.cursor() as cursor:
        cursor.execute(sql, [provider_id])
        row = cursor.fetchone()
    return row[0] if row else '-'


def referral_report_data(request):
    report_type = request.GET.get('report_type') or 'doctor'
    provider_id = request.GET.get('provider_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not provider_id or not start_date or not end_date:
        return JsonResponse({'success': False, 'message': 'Report type, provider, start date and end date required'}, status=400)

    rows = _referral_report_rows(report_type, provider_id, start_date, end_date)
    totals = _referral_report_totals(rows)
    return JsonResponse({'success': True, 'rows': rows, **totals})


def referral_report_pdf(request):
    report_type = request.GET.get('report_type') or 'doctor'
    provider_id = request.GET.get('provider_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not provider_id or not start_date or not end_date:
        return HttpResponse("Report type, provider, start date and end date required", status=400)
    rows = _referral_report_rows(report_type, provider_id, start_date, end_date)
    totals = _referral_report_totals(rows)
    provider_label = 'SR' if report_type == 'sr' else 'Doctor'
    provider_name = _referral_provider_name(report_type, provider_id)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=22, bottomMargin=22)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph("Diagnosis Referral Report", styles["Title"]))
    elements.append(Paragraph(f"<b>Report Type:</b> {provider_label} &nbsp;&nbsp; <b>{provider_label}:</b> {provider_id} - {provider_name}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Start Date:</b> {start_date} &nbsp;&nbsp; <b>End Date:</b> {end_date}", styles["Normal"]))
    elements.append(Spacer(1, 10))
    table_data = [["SL", "Tran ID", "Date", "Group Name", "Tran Head", "Test Tk", "Discount", "Ref Type", "Ref Rate", "Referral"]]
    for index, row in enumerate(rows, 1):
        table_data.append([
            index,
            row.get('tran_id') or '-',
            str(row.get('tran_date') or '-'),
            row.get('group_name') or '-',
            Paragraph(str(row.get('tran_head_name') or '-'), styles["BodyText"]),
            f"{float(row.get('test_tk') or 0):.2f}",
            f"{float(row.get('discount') or 0):.2f}",
            row.get('ref_type') or '-',
            f"{float(row.get('ref_rate') or 0):.2f}",
            f"{float(row.get('referral_amount') or 0):.2f}",
        ])
    table_data.append(["", "", "", "", "Total", f"{totals['total_test_tk']:.2f}", f"{totals['total_discount']:.2f}", "", "", f"{totals['total_referral']:.2f}"])
    table = Table(table_data, colWidths=[28, 82, 58, 78, 149, 58, 58, 55, 55, 60], repeatRows=1)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1f2327")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f3f5")),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (5, 1), (6, -1), 'RIGHT'),
        ('ALIGN', (8, 1), (9, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="diagnosis_referral_report.pdf"'
    return response

def product_search(request):
    q = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0))
    tran_main_head_id = request.GET.get('tran_main_head_id').strip()
    tran_group_id = request.GET.get('tran_group_id')
    limit = 10

    if not tran_group_id:
        return JsonResponse({'results': []})

    print (tran_main_head_id);
    cursor = connection.cursor()

    if q:
        sql = """
            SELECT 
                t.id,
                t.tran_head_name AS name,
                t.cp,
                m.manufacturer_name AS manufacturer,
                f.form_name AS form,
                c.name AS category_name,
                t.quantity,
                t.mrp
            FROM transaction__heads t
            JOIN transaction__groupes tg ON t.groupe_id = tg.id
            JOIN transaction__main__heads tmh ON tmh.id = tg.tran_groupe_type
            LEFT JOIN item__manufacturers m ON t.manufacturer_id = m.id
            LEFT JOIN item__forms f ON t.form_id = f.id
            LEFT JOIN transaction__category c ON t.category_id = c.id
            WHERE t.tran_head_name LIKE %s
            AND tmh.id = %s
            AND tg.id = %s
            ORDER BY t.id ASC
            LIMIT %s OFFSET %s
        """
        params = [f"{q}%", tran_main_head_id, tran_group_id, limit, offset]
    
    else:

        sql = """
            SELECT 
                t.id,
                t.tran_head_name AS name,
                t.cp,
                m.manufacturer_name AS manufacturer,
                f.form_name AS form,
                c.name AS category_name,
                t.quantity,
                t.mrp
            FROM transaction__heads t
            JOIN transaction__groupes tg ON t.groupe_id = tg.id
            JOIN transaction__main__heads tmh ON tmh.id = tg.tran_groupe_type
            LEFT JOIN item__manufacturers m ON t.manufacturer_id = m.id
            LEFT JOIN item__forms f ON t.form_id = f.id
            LEFT JOIN transaction__category c ON t.category_id = c.id
            WHERE tmh.id = %s
            AND tg.id = %s
            ORDER BY t.id ASC
            LIMIT %s OFFSET %s
        """
        params = [tran_main_head_id, tran_group_id, limit, offset]


    cursor.execute(sql, params)
    data = dictfetchall(cursor)

    return JsonResponse({'results': data})
# =========================================================================
# 📋 1. PATIENT MAIN LISTING GATEWAY VIEW (HTML VIEW 1)
# =========================================================================
def patient_list_view(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM patient_info ORDER BY id DESC")
        patients = dict_fetchall(cursor)
    return render(request, 'diagnosis/patient_list.html', {'patients': patients})


# =========================================================================
# 📝 2. SPLIT ENTRY & EDIT WORKSPACE VIEW (HTML VIEW 2)
# =========================================================================
def patient_form_view(request, pk=None):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM patient_info ORDER BY id DESC")
        patients = dict_fetchall(cursor)
    return render(request, 'diagnosis/patient_form.html', {
        'patients': patients,
        'edit_id': pk
    })


# =========================================================================
# 🔍 3. FETCH SINGLE PATIENT PROFILE ENGINE (AJAX GET)
# =========================================================================
def fetch_patient(request):
    patient_id = request.GET.get('id')
    if not patient_id:
        return JsonResponse({'error': 'Missing target context ID'}, status=400)
        
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM patient_info WHERE id = %s", [patient_id])
        patient = dict_fetchone(cursor)
        
    if patient:
        if patient.get('dob'):
            patient['dob'] = patient['dob'].strftime('%Y-%m-%d')
        return JsonResponse(patient)
    return JsonResponse({'error': 'Target patient records not found'}, status=404)


# =========================================================================
# 💾 4. STORE NEW PATIENT DATA ARCHITECTURE (AJAX POST)
# =========================================================================
def store_patient(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
        
    try:
        data = request.POST
        current_now = timezone.now()

        with transaction.atomic():
            with connection.cursor() as cursor:
                
                # --- STEP A: DYNAMIC LOOKUP WITH MULTIPLE MATCHING OPTIONS ---
                # Search directly by specific name 'Diagnosis Patients' or 'Diagnosis' head
                cursor.execute("""
                    SELECT id, tran_method, user_role 
                    FROM transaction__withs 
                    WHERE (LOWER(tran_with_name) LIKE '%%diagnosis patients%%' 
                       OR LOWER(tran_with_name) LIKE '%%diagnosis%%') 
                       AND tran_type = 10 
                    LIMIT 1
                """)
                tran_with_meta = cursor.fetchone()
                
                if tran_with_meta:
                    tran_with_id_val = tran_with_meta[0]
                    extracted_tran_method = tran_with_meta[1] if tran_with_meta[1] is not None else "0"
                    # CRITICAL FIX: Ensure user_role from DB isn't Null, fallback to 4
                    extracted_user_role = tran_with_meta[2] if tran_with_meta[2] is not None else 4
                else:
                    # STRICT FALLBACK SAFETIES: If no rows matching in DB table yet
                    tran_with_id_val = None
                    extracted_tran_method = "0"
                    extracted_user_role = 4

                # --- STEP B: UNIQUE PATIENT ID (DP SEQUENCE) GENERATION ---
                cursor.execute("SELECT user_id FROM user__infos WHERE user_id LIKE 'DP%%' ORDER BY user_id DESC LIMIT 1")
                last_user = cursor.fetchone()
                
                if last_user and last_user[0]:
                    last_number = int(last_user[0][2:])
                    new_number = last_number + 1
                else:
                    new_number = 1
                generated_user_id = f"DP{new_number:09d}"

                # --- STEP C: INSERT INTO USER__INFOS ---
                user_sql = """
                    INSERT INTO user__infos (
                        user_id, user_name, user_email, user_phone, gender, dob, 
                        nationality, religion, address, passport, user_role, status, 
                        tran_with_id, tran_method, added_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(user_sql, [
                    generated_user_id, 
                    data.get('patient_name'), 
                    data.get('present_email') or None,
                    data.get('present_mobile') or None, 
                    data.get('gender') or None, 
                    data.get('dob') or None,
                    data.get('nationality') or None, 
                    data.get('religion') or None, 
                    data.get('present_address') or None,
                    data.get('passport_no') or None, 
                    extracted_user_role, # Guarantees non-null int 4 fallback
                    1,                   # Status active
                    tran_with_id_val,  
                    extracted_tran_method,
                    current_now
                ])

                # --- STEP D: INSERT INTO PRIMARY patient_info SCHEMA ---
                patient_sql = """
                    INSERT INTO patient_info (
                        patient_name, father_husband_name, mother_name, parent_spouse_name, dob, age,
                        gender, marital_status, nationality, passport_no, blood_group, country_of_birth,
                        religion, occupation, weight, height, bmi, cause_visit_dcc, referral_source,
                        referred_by, consulted_doctor, doctor_name, clinic_name, daily_routine, daily_diet,
                        food_preferences, avoid_foods, diagnostic_reports, physical_condition, family_history,
                        family_relation, physical_activity, diet, present_address, present_mobile, present_email,
                        permanent_address, permanent_mobile, permanent_email, emergency_name, emergency_relation,
                        emergency_phone, patient_signature, user_info_id, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                """
                cursor.execute(patient_sql, [
                    data.get('patient_name'), data.get('father_husband_name') or None, data.get('mother_name') or None,
                    data.get('parent_spouse_name') or None, data.get('dob') or None, data.get('age') or None,
                    data.get('gender') or None, data.get('marital_status') or None, data.get('nationality') or None,
                    data.get('passport_no') or None, data.get('blood_group') or None, data.get('country_of_birth') or None,
                    data.get('religion') or None, data.get('occupation') or None, data.get('weight') or None,
                    data.get('height') or None, data.get('bmi') or None, data.get('cause_visit_dcc') or None,
                    data.get('referral_source') or None, data.get('referred_by') or None, data.get('consulted_doctor') or None,
                    data.get('doctor_name') or None, data.get('clinic_name') or None, data.get('daily_routine') or None,
                    data.get('daily_diet') or None, data.get('food_preferences') or None, data.get('avoid_foods') or None,
                    data.get('diagnostic_reports') or None, data.get('physical_condition') or None, data.get('family_history') or None,
                    data.get('family_relation') or None, data.get('physical_activity') or None, data.get('diet') or None,
                    data.get('present_address') or None, data.get('present_mobile') or None, data.get('present_email') or None,
                    data.get('permanent_address') or None, data.get('permanent_mobile') or None, data.get('permanent_email') or None,
                    data.get('emergency_name') or None, data.get('emergency_relation') or None, data.get('emergency_phone') or None,
                    data.get('patient_signature') or None, generated_user_id, current_now, current_now
                ])
                
                return JsonResponse({'success': True, 'id': cursor.lastrowid})
                
    except Exception as e:
        print("========!!! COREDATA CRASH TRACEBACK !!!========")
        traceback.print_exc()
        print("================================================")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# =========================================================================
# 🔄 5. UPDATE EXISTING PATIENT WORKFLOWS (AJAX POST)
# =========================================================================
def update_patient(request, pk):
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
        
    try:
        data = request.POST
        current_now = timezone.now()

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_info_id FROM patient_info WHERE id = %s", [pk])
                current_patient = cursor.fetchone()
                if not current_patient:
                    return JsonResponse({'success': False, 'error': 'Patient profile not found'}, status=404)
                
                user_info_id = current_patient[0]

                # Update primary table data
                update_patient_sql = """
                    UPDATE patient_info SET 
                        patient_name=%s, father_husband_name=%s, mother_name=%s, parent_spouse_name=%s, dob=%s, age=%s,
                        gender=%s, marital_status=%s, nationality=%s, passport_no=%s, blood_group=%s, country_of_birth=%s,
                        religion=%s, occupation=%s, weight=%s, height=%s, bmi=%s, cause_visit_dcc=%s, referral_source=%s,
                        referred_by=%s, consulted_doctor=%s, doctor_name=%s, clinic_name=%s, daily_routine=%s, daily_diet=%s,
                        food_preferences=%s, avoid_foods=%s, diagnostic_reports=%s, physical_condition=%s, family_history=%s,
                        family_relation=%s, physical_activity=%s, diet=%s, present_address=%s, present_mobile=%s, present_email=%s,
                        permanent_address=%s, permanent_mobile=%s, permanent_email=%s, emergency_name=%s, emergency_relation=%s,
                        emergency_phone=%s, patient_signature=%s, updated_at=%s
                    WHERE id = %s
                """
                cursor.execute(update_patient_sql, [
                    data.get('patient_name'), data.get('father_husband_name') or None, data.get('mother_name') or None,
                    data.get('parent_spouse_name') or None, data.get('dob') or None, data.get('age') or None,
                    data.get('gender') or None, data.get('marital_status') or None, data.get('nationality') or None,
                    data.get('passport_no') or None, data.get('blood_group') or None, data.get('country_of_birth') or None,
                    data.get('religion') or None, data.get('occupation') or None, data.get('weight') or None,
                    data.get('height') or None, data.get('bmi') or None, data.get('cause_visit_dcc') or None,
                    data.get('referral_source') or None, data.get('referred_by') or None, data.get('consulted_doctor') or None,
                    data.get('doctor_name') or None, data.get('clinic_name') or None, data.get('daily_routine') or None,
                    data.get('daily_diet') or None, data.get('food_preferences') or None, data.get('avoid_foods') or None,
                    data.get('diagnostic_reports') or None, data.get('physical_condition') or None, data.get('family_history') or None,
                    data.get('family_relation') or None, data.get('physical_activity') or None, data.get('diet') or None,
                    data.get('present_address') or None, data.get('present_mobile') or None, data.get('present_email') or None,
                    data.get('permanent_address') or None, data.get('permanent_mobile') or None, data.get('permanent_email') or None,
                    data.get('emergency_name') or None, data.get('emergency_relation') or None, data.get('emergency_phone') or None,
                    data.get('patient_signature') or None, current_now, pk
                ])

                # Sync modification details inside user__infos context reference
                if user_info_id:
                    cursor.execute("""
                        SELECT id FROM transaction__withs 
                        WHERE LOWER(tran_with_name) LIKE '%%diagnosis%%' AND tran_type = 10 LIMIT 1
                    """)
                    u_with = cursor.fetchone()
                    u_with_id = u_with[0] if u_with else None

                    update_user_sql = """
                        UPDATE user__infos SET 
                            user_name=%s, user_email=%s, user_phone=%s, gender=%s, dob=%s, 
                            nationality=%s, religion=%s, address=%s, passport=%s, tran_with_id=%s, updated_at=%s
                        WHERE user_id = %s
                    """
                    cursor.execute(update_user_sql, [
                        data.get('patient_name'), data.get('present_email') or None, data.get('present_mobile') or None,
                        data.get('gender') or None, data.get('dob') or None, data.get('nationality') or None,
                        data.get('religion') or None, data.get('present_address') or None, data.get('passport_no') or None,
                        u_with_id, current_now, user_info_id
                    ])

                return JsonResponse({'success': True})
                
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# =========================================================================
# ❌ 6. CRITICAL DELETE SYSTEM PIPELINE (AJAX POST)
# =========================================================================
def delete_patient(request, pk):
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_info_id FROM patient_info WHERE id = %s", [pk])
                row = cursor.fetchone()
                if row:
                    user_info_id = row[0]
                    cursor.execute("DELETE FROM patient_info WHERE id = %s", [pk])
                    if user_info_id:
                        cursor.execute("DELETE FROM user__infos WHERE user_id = %s", [user_info_id])
                return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    

    from django.http import JsonResponse
from django.db import connection





def autocomplete_doctor(request):
    """🧠 Optimised Real-time Select2 autocomplete mapping using physical custom column"""
    q = request.GET.get('term', request.GET.get('q', '')).strip()
    with connection.cursor() as cursor:
        sql = """
            SELECT id, custom_doc_id, name, specialization, chamber 
            FROM doctors_info 
            WHERE name LIKE %s OR custom_doc_id LIKE %s
            LIMIT 20;
        """
        cursor.execute(sql, [f"%{q}%", f"%{q}%"])
        columns = [col[0] for col in cursor.description]
        raw_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # 🔥 Direct extraction alignment from physical custom data string field container!
    results = [{
        'id': row['id'],
        'text': f"{row['custom_doc_id']} - {row['name']}",
        'speciality': row['specialization'] or 'General',
        'chamber': row['chamber'] or 'N/A'
    } for row in raw_data]
    
    return JsonResponse({"results": results}, safe=False)

# sr/views.py inside autocomplete_sr data object manipulation routing map handler:
def autocomplete_sr(request):
    """🧠 Optimised Real-time Select2 autocomplete mapping targeting physical custom code identity metrics"""
    q = request.GET.get('term', request.GET.get('q', '')).strip()
    
    with connection.cursor() as cursor:
        # 🔥 FIX: Query constraint array parsing variables values logic mapping structure 
        # Checking string tracking columns name matching exact parameters matching format structure:
        sql = """
            SELECT id, custom_sr_id, name 
            FROM item__sr_agents 
            WHERE (name LIKE %s OR custom_sr_id LIKE %s) 
              AND is_active = 1
            LIMIT 20;
        """
        # Exact string query character sequences boundary map criteria conditions checking arrays
        cursor.execute(sql, [f"%{q}%", f"%{q}%"])
        
        columns = [col[0] for col in cursor.description]
        raw_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    results = [{
        'id': row['id'],
        'text': f"{row['custom_sr_id']} - {row['name']}",
        'name_display': row['name']
    } for row in raw_data]
    
    return JsonResponse({"results": results}, safe=False)


# lab report generation


def ensure_lab_parameters_table():
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lab_parameters (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                group_id BIGINT NOT NULL,
                category_id BIGINT NOT NULL,
                head_id BIGINT NULL,
                serial INT NOT NULL DEFAULT 0,
                title VARCHAR(255) NOT NULL,
                title_code VARCHAR(100) NULL,
                investigation VARCHAR(255) NOT NULL,
                investigation_code VARCHAR(100) NULL,
                unit VARCHAR(100) NULL,
                reff_range TEXT NULL,
                added_at DATETIME NULL,
                updated_at DATETIME NULL,
                INDEX idx_lab_parameters_group (group_id),
                INDEX idx_lab_parameters_category (category_id),
                INDEX idx_lab_parameters_head (head_id)
            )
        """)
        cursor.execute("ALTER TABLE lab_parameters ADD COLUMN IF NOT EXISTS title_code VARCHAR(100) NULL AFTER title")
        cursor.execute("ALTER TABLE lab_parameters ADD COLUMN IF NOT EXISTS investigation_code VARCHAR(100) NULL AFTER investigation")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lab_results (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                invoice_id BIGINT NOT NULL,
                group_id BIGINT NOT NULL,
                category_id BIGINT NOT NULL,
                head_id BIGINT NULL,
                serial INT NOT NULL DEFAULT 0,
                title VARCHAR(255) NOT NULL,
                title_code VARCHAR(100) NULL,
                investigation VARCHAR(255) NOT NULL,
                investigation_code VARCHAR(100) NULL,
                unit VARCHAR(100) NULL,
                reff_range TEXT NULL,
                result TEXT NULL,
                added_at DATETIME NULL,
                updated_at DATETIME NULL,
                INDEX idx_lab_results_invoice (invoice_id),
                INDEX idx_lab_results_category (category_id),
                INDEX idx_lab_results_head (head_id)
            )
        """)
        cursor.execute("ALTER TABLE lab_results ADD COLUMN IF NOT EXISTS selected_test_ids TEXT NULL AFTER invoice_id")
        cursor.execute("ALTER TABLE lab_results ADD COLUMN IF NOT EXISTS selected_test_names TEXT NULL AFTER selected_test_ids")


def _optional_int(value):
    return int(value) if str(value or '').strip() else None


def _positive_int(value, default=1):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def normalize_lab_parameter_serials(group_id, category_id, preferred_id=None, preferred_serial=None):
    desired_serial = _positive_int(preferred_serial, 1)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, serial
            FROM lab_parameters
            WHERE group_id = %s AND category_id = %s
            ORDER BY serial ASC, id ASC
        """, [group_id, category_id])
        rows = [{'id': row[0], 'serial': row[1]} for row in cursor.fetchall()]
        target_row = None
        other_rows = []
        for row in rows:
            if preferred_id and str(row['id']) == str(preferred_id):
                target_row = row
            else:
                other_rows.append(row)
        if target_row:
            insert_index = max(0, min(desired_serial - 1, len(other_rows)))
            ordered_rows = other_rows[:insert_index] + [target_row] + other_rows[insert_index:]
        else:
            ordered_rows = other_rows
        for index, row in enumerate(ordered_rows, start=1):
            cursor.execute("UPDATE lab_parameters SET serial = %s WHERE id = %s", [index, row['id']])


def lab_parameter_setup_page(request):
    ensure_lab_parameters_table()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, tran_groupe_name AS name
            FROM transaction__groupes
            WHERE tran_groupe_type = %s AND status = 1
            ORDER BY tran_groupe_name ASC
        """, [DIAGNOSIS_MAIN_HEAD_ID])
        groups = dict_fetchall(cursor)
    return render(request, 'diagnosis/lab_parameter_setup.html', {
        'groups': groups,
    })


def lab_parameter_categories(request):
    group_id = request.GET.get('group_id')
    if not group_id:
        return JsonResponse({'success': True, 'categories': []})
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT c.id, c.name
            FROM transaction__category c
            JOIN transaction__groupes selected_group ON selected_group.id = %s
            JOIN transaction__groupes category_group ON category_group.id = c.group_id
            WHERE c.status = 1
              AND (c.group_id = selected_group.id
                   OR (category_group.tran_groupe_name = selected_group.tran_groupe_name
                       AND category_group.tran_groupe_type = selected_group.tran_groupe_type))
            ORDER BY c.name ASC
        """, [group_id])
        categories = dict_fetchall(cursor)
    return JsonResponse({'success': True, 'categories': categories})


def lab_parameter_heads(request):
    group_id = request.GET.get('group_id')
    if not group_id:
        return JsonResponse({'success': True, 'heads': []})
    params = [group_id]
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT id, tran_head_name AS name
            FROM transaction__heads
            WHERE groupe_id = %s AND status = 1
            ORDER BY tran_head_name ASC
        """, params)
        heads = dict_fetchall(cursor)
    return JsonResponse({'success': True, 'heads': heads})


def lab_parameter_list(request):
    ensure_lab_parameters_table()
    page = int(request.GET.get('page', 1) or 1)
    limit = int(request.GET.get('limit', 20) or 20)
    offset = (page - 1) * limit
    group_id = request.GET.get('group_id')
    category_id = request.GET.get('category_id')
    head_id = request.GET.get('head_id')
    search = (request.GET.get('search') or '').strip()
    where_sql = []
    params = []
    if group_id:
        where_sql.append("lp.group_id = %s")
        params.append(group_id)
    if category_id:
        where_sql.append("lp.category_id = %s")
        params.append(category_id)
    if head_id:
        where_sql.append("lp.head_id = %s")
        params.append(head_id)
    if search:
        where_sql.append("(lp.title LIKE %s OR lp.investigation LIKE %s OR lp.unit LIKE %s OR lp.reff_range LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])
    where_clause = ("WHERE " + " AND ".join(where_sql)) if where_sql else ""
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT lp.id, lp.group_id, g.tran_groupe_name AS group_name, lp.category_id, c.name AS category_name,
                   lp.head_id, h.tran_head_name, lp.serial, lp.title, lp.title_code, lp.investigation, lp.investigation_code, lp.unit, lp.reff_range
            FROM lab_parameters lp
            LEFT JOIN transaction__groupes g ON g.id = lp.group_id
            LEFT JOIN transaction__category c ON c.id = lp.category_id
            LEFT JOIN transaction__heads h ON h.id = lp.head_id
            {where_clause}
            ORDER BY g.tran_groupe_name ASC, c.name ASC, lp.serial ASC, lp.id ASC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = dict_fetchall(cursor)
    return JsonResponse({'success': True, 'lab_parameters': rows})


@csrf_exempt
def lab_parameter_save(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    try:
        ensure_lab_parameters_table()
        data = request.POST
        group_id = data.get('group_id')
        category_id = data.get('category_id')
        title = (data.get('title') or '').strip()
        investigation = (data.get('investigation') or '').strip()
        if not group_id or not category_id or not title or not investigation:
            return JsonResponse({'success': False, 'message': 'Group, category, title and investigation required'}, status=400)
        desired_serial = _positive_int(data.get('serial'), 1)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO lab_parameters (group_id, category_id, head_id, serial, title, title_code, investigation, investigation_code, unit, reff_range, added_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    group_id, category_id, _optional_int(data.get('head_id')), desired_serial,
                    title, (data.get('title_code') or '').strip(), investigation, (data.get('investigation_code') or '').strip(),
                    (data.get('unit') or '').strip(), (data.get('reff_range') or '').strip(),
                    timezone.now(), timezone.now()
                ])
                new_id = cursor.lastrowid
            normalize_lab_parameter_serials(group_id, category_id, new_id, desired_serial)
        return JsonResponse({'success': True, 'message': 'Saved successfully'})
    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


@csrf_exempt
def lab_parameter_update(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    try:
        ensure_lab_parameters_table()
        data = request.POST
        lab_parameter_id = data.get('id')
        group_id = data.get('group_id')
        category_id = data.get('category_id')
        title = (data.get('title') or '').strip()
        investigation = (data.get('investigation') or '').strip()
        if not lab_parameter_id or not group_id or not category_id or not title or not investigation:
            return JsonResponse({'success': False, 'message': 'Required data missing'}, status=400)
        desired_serial = _positive_int(data.get('serial'), 1)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT group_id, category_id FROM lab_parameters WHERE id = %s", [lab_parameter_id])
                old_scope = cursor.fetchone()
                cursor.execute("""
                    UPDATE lab_parameters
                    SET group_id = %s, category_id = %s, head_id = %s, serial = %s, title = %s, title_code = %s, investigation = %s, investigation_code = %s,
                        unit = %s, reff_range = %s, updated_at = %s
                    WHERE id = %s
                """, [
                    group_id, category_id, _optional_int(data.get('head_id')), desired_serial, title, (data.get('title_code') or '').strip(), investigation, (data.get('investigation_code') or '').strip(),
                    (data.get('unit') or '').strip(), (data.get('reff_range') or '').strip(), timezone.now(), lab_parameter_id
                ])
            if old_scope and (str(old_scope[0]) != str(group_id) or str(old_scope[1]) != str(category_id)):
                normalize_lab_parameter_serials(old_scope[0], old_scope[1])
            normalize_lab_parameter_serials(group_id, category_id, lab_parameter_id, desired_serial)
        return JsonResponse({'success': True, 'message': 'Updated successfully'})
    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


@csrf_exempt
def lab_parameter_delete(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    try:
        ensure_lab_parameters_table()
        lab_parameter_id = request.POST.get('id')
        if not lab_parameter_id:
            return JsonResponse({'success': False, 'message': 'ID required'}, status=400)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT group_id, category_id FROM lab_parameters WHERE id = %s", [lab_parameter_id])
                old_scope = cursor.fetchone()
                cursor.execute("DELETE FROM lab_parameters WHERE id = %s", [lab_parameter_id])
            if old_scope:
                normalize_lab_parameter_serials(old_scope[0], old_scope[1])
        return JsonResponse({'success': True, 'message': 'Deleted successfully'})
    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


def biochemistry_result_page(request):
    ensure_lab_parameters_table()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, tran_groupe_name AS name
            FROM transaction__groupes
            WHERE tran_groupe_type = %s AND status = 1
            ORDER BY tran_groupe_name ASC
        """, [DIAGNOSIS_MAIN_HEAD_ID])
        groups = dict_fetchall(cursor)
    return render(request, 'diagnosis/biochemistry_result.html', {'groups': groups})


def biochemistry_result_add_page(request):
    ensure_lab_parameters_table()
    return render(request, 'diagnosis/biochemistry_result_form.html')


def _biochemistry_category_ids():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id FROM transaction__category
            WHERE LOWER(name) = 'biochemistry' AND status = 1
        """)
        return [row[0] for row in cursor.fetchall()]


def _biochemistry_group_ids(category_ids):
    if not category_ids:
        return []
    placeholders = ','.join(['%s'] * len(category_ids))
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT DISTINCT matching_group.id
            FROM transaction__category c
            JOIN transaction__groupes category_group ON category_group.id = c.group_id
            JOIN transaction__groupes matching_group
              ON matching_group.id = category_group.id
              OR (matching_group.tran_groupe_name = category_group.tran_groupe_name
                  AND matching_group.tran_groupe_type = category_group.tran_groupe_type)
            WHERE c.id IN ({placeholders}) AND c.status = 1
        """, category_ids)
        return [row[0] for row in cursor.fetchall()]


def _invoice_info(invoice_id=None, search=None):
    where_sql = "m.id = %s" if invoice_id else "(m.tran_id = %s OR m.invoice_ref = %s OR m.id = %s)"
    params = [invoice_id] if invoice_id else [search, search, search if str(search or '').isdigit() else 0]
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT m.id, m.tran_id, m.invoice_ref, m.tran_date, m.patient_id,
                   COALESCE(p.patient_name, m.user_name, '') AS patient_name,
                   COALESCE(p.age_y, 0) AS age_y, COALESCE(p.age_m, 0) AS age_m, COALESCE(p.age_d, 0) AS age_d,
                   COALESCE(p.gender, '') AS gender, COALESCE(p.present_mobile, m.user_phone, '') AS phone,
                   COALESCE(p.present_address, m.user_address, '') AS address,
                   COALESCE(doc.name, '') AS doctor_name
            FROM transaction__mains m
            LEFT JOIN patient_info p ON p.user_info_id COLLATE utf8mb4_unicode_ci = m.patient_id COLLATE utf8mb4_unicode_ci
            LEFT JOIN doctors_info doc ON doc.custom_doc_id COLLATE utf8mb4_unicode_ci = m.doctor_id COLLATE utf8mb4_unicode_ci
            WHERE {where_sql} AND m.tran_type = %s
            LIMIT 1
        """, params + [DIAGNOSIS_MAIN_HEAD_ID])
        return dict_fetchone(cursor)


def biochemistry_invoice_autocomplete(request):
    ensure_lab_parameters_table()
    term = (request.GET.get('q') or '').strip()
    if len(term) < 1:
        return JsonResponse({'results': []})
    like_term = f"%{term}%"
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT m.id, m.tran_id, m.invoice_ref, COALESCE(p.patient_name, m.user_name, '') AS patient_name
            FROM transaction__mains m
            LEFT JOIN patient_info p ON p.user_info_id COLLATE utf8mb4_unicode_ci = m.patient_id COLLATE utf8mb4_unicode_ci
            WHERE m.tran_type = %s AND (m.tran_id COLLATE utf8mb4_unicode_ci LIKE %s OR m.invoice_ref COLLATE utf8mb4_unicode_ci LIKE %s OR COALESCE(p.patient_name, m.user_name, '') COLLATE utf8mb4_unicode_ci LIKE %s)
            ORDER BY m.id DESC
            LIMIT 12
        """, [DIAGNOSIS_MAIN_HEAD_ID, like_term, like_term, like_term])
        rows = dict_fetchall(cursor)
    results = [{'id': row['id'], 'tran_id': row['tran_id'], 'invoice_ref': row['invoice_ref'], 'patient_name': row['patient_name']} for row in rows]
    return JsonResponse({'results': results})


def biochemistry_invoice_load(request):
    ensure_lab_parameters_table()
    search = (request.GET.get('invoice') or '').strip()
    invoice_id = request.GET.get('invoice_id')
    selected_test_id = request.GET.get('test_id')
    edit_mode = request.GET.get('edit') == '1'
    if not search and not invoice_id:
        return JsonResponse({'success': False, 'message': 'Transaction ID required'}, status=400)
    category_ids = _biochemistry_category_ids()
    if not category_ids:
        return JsonResponse({'success': False, 'message': 'Biochemistry category setup not found'}, status=400)
    invoice = _invoice_info(invoice_id=invoice_id, search=search)
    if not invoice:
        return JsonResponse({'success': False, 'message': 'Diagnosis transaction not found'}, status=404)
    placeholders = ','.join(['%s'] * len(category_ids))
    group_ids = _biochemistry_group_ids(category_ids)
    with connection.cursor() as cursor:
        test_where = "AND COALESCE(d.tran_groupe_id, h.groupe_id) IN ({})".format(','.join(['%s'] * len(group_ids))) if group_ids else ""
        test_params = [invoice['tran_id'], DIAGNOSIS_MAIN_HEAD_ID] + group_ids
        cursor.execute(f"""
            SELECT DISTINCT d.tran_head_id AS id, h.tran_head_name AS name, COALESCE(d.tran_groupe_id, h.groupe_id) AS group_id
            FROM transaction__details d
            JOIN transaction__heads h ON h.id = d.tran_head_id
            WHERE d.tran_id = %s AND d.tran_type = %s AND d.tran_head_id IS NOT NULL {test_where}
              AND (%s = 1 OR NOT EXISTS (SELECT 1 FROM lab_results lr WHERE lr.invoice_id = %s AND lr.category_id IN ({placeholders})))
            ORDER BY h.tran_head_name ASC
        """, test_params + [1 if edit_mode else 0, invoice['id']] + category_ids)
        tests = dict_fetchall(cursor)
        if not tests:
            cursor.execute(f"SELECT COUNT(*) AS saved_count FROM lab_results WHERE invoice_id = %s AND category_id IN ({placeholders})", [invoice['id']] + category_ids)
            saved_row = dict_fetchone(cursor)
            return JsonResponse({'success': True, 'invoice': invoice, 'tests': [], 'rows': [], 'already_added': (saved_row or {}).get('saved_count', 0) > 0})
        params = category_ids[:]
        cursor.execute(f"""
            SELECT p.id AS parameter_id, p.group_id, p.category_id, p.head_id, h.tran_head_name, p.serial,
                   p.title, p.title_code, p.investigation, p.investigation_code, p.unit, p.reff_range,
                   COALESCE(r.result, '') AS result
            FROM lab_parameters p
            LEFT JOIN transaction__heads h ON h.id = p.head_id
            LEFT JOIN lab_results r ON r.invoice_id = %s AND r.category_id = p.category_id AND COALESCE(r.investigation_code, '') = COALESCE(p.investigation_code, '') AND r.investigation = p.investigation
            WHERE p.category_id IN ({placeholders})
            ORDER BY p.serial ASC, p.id ASC
        """, [invoice['id']] + params)
        rows = dict_fetchall(cursor)
        if not rows:
            cursor.execute(f"""
                SELECT p.id AS parameter_id, p.group_id, p.category_id, p.head_id, h.tran_head_name, p.serial,
                       p.title, p.title_code, p.investigation, p.investigation_code, p.unit, p.reff_range, '' AS result
                FROM lab_parameters p
                LEFT JOIN transaction__heads h ON h.id = p.head_id
                WHERE p.category_id IN ({placeholders})
                ORDER BY p.serial ASC, p.id ASC
            """, category_ids)
            rows = dict_fetchall(cursor)
        cursor.execute(f"SELECT selected_test_ids, selected_test_names FROM lab_results WHERE invoice_id = %s AND category_id IN ({placeholders}) LIMIT 1", [invoice['id']] + category_ids)
        selected_row = dict_fetchone(cursor)
    selected_ids = [item for item in str((selected_row or {}).get('selected_test_ids') or '').split(',') if item]
    selected_names = [item.strip() for item in str((selected_row or {}).get('selected_test_names') or '').split(',') if item.strip()]
    return JsonResponse({'success': True, 'invoice': invoice, 'tests': tests, 'rows': rows, 'selected_test_ids': selected_ids, 'selected_test_names': selected_names})


@csrf_exempt
def biochemistry_result_save(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    try:
        ensure_lab_parameters_table()
        payload = json.loads(request.body.decode('utf-8') or '{}')
        invoice_id = payload.get('invoice_id')
        selected_test_ids = ','.join([str(item) for item in (payload.get('selected_test_ids') or []) if str(item).strip()])
        selected_test_names = ', '.join([str(item) for item in (payload.get('selected_test_names') or []) if str(item).strip()])
        rows = [row for row in (payload.get('rows') or []) if str(row.get('result') or '').strip()]
        if not invoice_id or not rows:
            return JsonResponse({'success': False, 'message': 'At least one result value required'}, status=400)
        with transaction.atomic():
            category_ids = sorted({str(row.get('category_id')) for row in rows if row.get('category_id')})
            with connection.cursor() as cursor:
                if category_ids:
                    cursor.execute("DELETE FROM lab_results WHERE invoice_id = %s AND category_id IN ({})".format(','.join(['%s'] * len(category_ids))), [invoice_id] + category_ids)
                insert_rows = []
                for row in rows:
                    row_title = str(row.get('title') or '').strip()
                    row_title = selected_test_names if not row_title or row_title == '-' else row_title
                    insert_rows.append([
                        invoice_id, selected_test_ids, selected_test_names, row.get('group_id'), row.get('category_id'), None, row.get('serial') or 0,
                        row_title, row.get('title_code') or '', row.get('investigation') or '', row.get('investigation_code') or '',
                        row.get('unit') or '', row.get('reff_range') or '', row.get('result') or '', timezone.now(), timezone.now()
                    ])
                cursor.executemany("""
                    INSERT INTO lab_results (invoice_id, selected_test_ids, selected_test_names, group_id, category_id, head_id, serial, title, title_code, investigation, investigation_code, unit, reff_range, result, added_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, insert_rows)
        return JsonResponse({'success': True, 'invoice_id': invoice_id, 'preview_url': f'/diagnosis/lab-report/biochemistry/preview/{invoice_id}/', 'download_url': f'/diagnosis/lab-report/biochemistry/pdf/{invoice_id}/?download=1'})
    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


def biochemistry_result_list(request):
    ensure_lab_parameters_table()
    search = (request.GET.get('search') or '').strip()
    group_id = request.GET.get('group_id')
    category_id = request.GET.get('category_id')
    where_parts = []
    params = []
    if search:
        where_parts.append("(m.tran_id LIKE %s OR m.invoice_ref LIKE %s OR p.patient_name LIKE %s OR m.user_name LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])
    if group_id:
        where_parts.append("r.group_id = %s")
        params.append(group_id)
    if category_id:
        where_parts.append("r.category_id = %s")
        params.append(category_id)
    where_parts.append("COALESCE(r.result, '') <> ''")
    where_sql = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT r.invoice_id, m.tran_id, m.invoice_ref, COALESCE(p.patient_name, m.user_name, '') AS patient_name,
                   MAX(r.updated_at) AS updated_at, COUNT(*) AS total_rows
            FROM lab_results r
            JOIN transaction__mains m ON m.id = r.invoice_id
            LEFT JOIN patient_info p ON p.user_info_id COLLATE utf8mb4_unicode_ci = m.patient_id COLLATE utf8mb4_unicode_ci
            {where_sql}
            GROUP BY r.invoice_id, m.tran_id, m.invoice_ref, patient_name
            ORDER BY MAX(r.updated_at) DESC, r.invoice_id DESC
            LIMIT 100
        """, params)
        results = dict_fetchall(cursor)
    return JsonResponse({'success': True, 'results': results})


def _biochemistry_report_rows(invoice_id):
    ensure_lab_parameters_table()
    invoice = _invoice_info(invoice_id=invoice_id)
    if not invoice:
        return None, []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT r.title, r.investigation, r.result, r.unit, r.reff_range, r.serial, r.head_id, r.selected_test_names,
                   COALESCE(NULLIF(NULLIF(TRIM(r.title), ''), '-'), NULLIF(TRIM(r.selected_test_names), ''), r.investigation) AS test_name, COALESCE(c.name, 'Biochemistry') AS category_name
            FROM lab_results r
            LEFT JOIN transaction__category c ON c.id = r.category_id
            WHERE r.invoice_id = %s AND COALESCE(r.result, '') <> ''
            ORDER BY c.name ASC, r.serial ASC, r.id ASC
        """, [invoice_id])
        rows = dict_fetchall(cursor)
    return invoice, rows


def biochemistry_result_preview(request, invoice_id):
    invoice, rows = _biochemistry_report_rows(invoice_id)
    if not invoice:
        return JsonResponse({'success': False, 'message': 'Invoice not found'}, status=404)
    receipt_no = invoice.get('invoice_ref') or invoice.get('tran_id') or str(invoice_id)
    age_text = f"{invoice.get('age_y') or 0}Y {invoice.get('age_m') or 0}M {invoice.get('age_d') or 0}D"
    selected_names = rows[0].get('selected_test_names') if rows else ''
    html = f"""<div class='bio-report-preview'>
        <div class='bio-report-head'>
            <div><b>Name</b> : {escape(invoice.get('patient_name') or '-')}</div>
            <div><b>Age</b> : {escape(age_text)} {escape(invoice.get('gender') or '')}</div>
            <div><b>Reg No.</b> : {escape(receipt_no)}</div>
            <div><b>Phone</b> : {escape(invoice.get('phone') or '-')}</div>
            <div><b>Ref. By</b> : {escape(invoice.get('doctor_name') or '-')}</div>
            <div><b>Reg. Date</b> : {escape(str(invoice.get('tran_date') or '')[:16])}</div>
            <div class='bio-full'><b>Address</b> : {escape(invoice.get('address') or '-')}</div>
            <div class='bio-full'><b>Investigation</b> : {escape(selected_names or '-')}</div>
        </div>"""
    grouped = {}
    for row in rows:
        grouped.setdefault(row.get('category_name') or 'Biochemistry', {}).setdefault(row.get('test_name') or row.get('title') or 'Test', []).append(row)
    if not grouped:
        html += "<div class='text-center p-4'>No result data found</div>"
    for category, tests in grouped.items():
        html += f"<h4>{escape(str(category).upper())} REPORT</h4><table><colgroup><col style='width:45%'><col style='width:12%'><col style='width:15%'><col style='width:28%'></colgroup><thead><tr><th>Title</th><th>Result</th><th>Unit</th><th>Ref</th></tr></thead><tbody>"
        for test_name, test_rows in tests.items():
            html += f"<tr class='bio-test-title'><td colspan='4'>*{escape(test_name)}</td></tr>"
            for row in test_rows:
                html += f"<tr><td>{escape(row.get('investigation') or '')}</td><td>{escape(row.get('result') or '')}</td><td>{escape(row.get('unit') or '')}</td><td>{escape(row.get('reff_range') or '').replace(chr(10), '<br>')}</td></tr>"
        html += "</tbody></table>"
    html += "</div>"
    return JsonResponse({'success': True, 'html': html, 'download_url': f'/diagnosis/lab-report/biochemistry/pdf/{invoice_id}/?download=1'})


def biochemistry_result_pdf(request, invoice_id):
    invoice, rows = _biochemistry_report_rows(invoice_id)
    if not invoice:
        return HttpResponse("Invoice not found", status=404)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=34, leftMargin=34, topMargin=34, bottomMargin=28)
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("BioNormal", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12)
    small = ParagraphStyle("BioSmall", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=10)
    bold = ParagraphStyle("BioBold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12)
    center_title = ParagraphStyle("BioCenterTitle", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=11, leading=13)
    center_section = ParagraphStyle("BioCenterSection", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica", fontSize=11, leading=13)
    receipt_no = invoice.get('invoice_ref') or invoice.get('tran_id') or str(invoice_id)
    tran_date = str(invoice.get('tran_date') or '')[:16]
    age_text = f"{invoice.get('age_y') or 0} Year {invoice.get('gender') or ''}".strip()
    barcode = code128.Code128(receipt_no, barHeight=0.28 * inch, barWidth=0.7)
    story = []
    header_data = [
        [Paragraph("Name&nbsp;&nbsp;&nbsp;&nbsp;: " + (invoice.get('patient_name') or '-'), normal), Paragraph(age_text, normal), Paragraph("Reg No.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: " + receipt_no, normal), barcode],
        [Paragraph("Ref. By&nbsp;: " + (invoice.get('doctor_name') or '-'), normal), "", Paragraph("Reg. Date&nbsp;&nbsp;: " + tran_date, normal), ""],
        [Paragraph("Address&nbsp;: " + (invoice.get('address') or '-'), normal), "", Paragraph("Collected At&nbsp;: SECL", normal), ""],
        [Paragraph("Phone&nbsp;&nbsp;&nbsp;: " + (invoice.get('phone') or '-'), normal), "", "", ""],
        [Paragraph("Investigation&nbsp;: " + ((rows[0].get('selected_test_names') if rows else '') or '-'), normal), "", "", ""],
    ]
    header = Table(header_data, colWidths=[2.55*inch, 1.35*inch, 1.7*inch, 1.25*inch])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("SPAN", (3, 0), (3, 2)), ("LINEBELOW", (0, 4), (-1, 4), 0.8, colors.black)]))
    story.append(header)
    story.append(Spacer(1, 0.08 * inch))
    grouped = {}
    for row in rows:
        category = row.get('category_name') or 'Biochemistry'
        test_name = row.get('test_name') or row.get('title') or 'Test'
        grouped.setdefault(category, {}).setdefault(test_name, []).append(row)
    for category, tests in grouped.items():
        story.append(Paragraph(f"<u>{str(category).upper()} REPORT</u>", center_title))
        table_data = [[Paragraph("<u>Title</u>", bold), Paragraph("<u>Result</u>", bold), Paragraph("<u>Unit</u>", bold), Paragraph("<u>Ref</u>", bold)]]
        for test_name, test_rows in tests.items():
            table_data.append([Paragraph(f"<b><u>*{test_name}</u></b>", bold), "", "", ""])
            first_row = True
            for row in test_rows:
                label = (row.get('investigation') or row.get('title') or '')
                display_label = f"<b>{label}</b>" if first_row and len(test_rows) == 1 else label
                table_data.append([Paragraph(display_label, normal), Paragraph(row.get('result') or '', normal), Paragraph(row.get('unit') or '', normal), Paragraph((row.get('reff_range') or '').replace('\n', '<br/>'), small)])
                first_row = False
        result_table = Table(table_data, colWidths=[3.2*inch, 0.85*inch, 1.0*inch, 2.0*inch], repeatRows=1)
        result_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("ALIGN", (2, 0), (2, -1), "LEFT"), ("ALIGN", (3, 0), (3, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (2, 0), (2, -1), 8),
        ]))
        story.append(result_table)
        story.append(Spacer(1, 0.12 * inch))
    if not rows:
        story.append(Paragraph("No result data found", center_section))
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type="application/pdf")
    mode = "attachment" if request.GET.get("download") == "1" else "inline"
    response["Content-Disposition"] = f'{mode}; filename="biochemistry_report_{invoice_id}.pdf"'
    return response



