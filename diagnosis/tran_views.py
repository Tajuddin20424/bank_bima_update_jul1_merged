from datetime import timezone
from io import BytesIO
import json
import traceback
from django.http import HttpResponse, JsonResponse
from django.forms import model_to_dict
from django.shortcuts import get_object_or_404, redirect, render
from core.models import TransactionDetails, TransactionMains,UserInfos, TransactionWiths, TransactionHeads, Stores, ItemManufacturers, LocationInfos, TransactionMainsTemps, TransactionDetailsTemps, TransactionMainHeads
from django.core.paginator import Paginator
from django.db import connection
from core.amount_allocation import allocate_amount
from django.db import transaction
from django.db.models import F, Q
from django.db.models import Count, Case, When, IntegerField, Q
from datetime import datetime
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.payment_mode import set_payment_mode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.graphics import renderSVG
from reportlab.graphics.barcode import createBarcodeDrawing
from django.template.loader import get_template
from reportlab.platypus import Table
from django.utils.dateparse import parse_date
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.contrib.sessions.models import Session


def dictfetchall(cursor):
    """Return all rows from a cursor as a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def build_invoice_barcode_svg(invoice_value):
    barcode_value = str(invoice_value or "").strip()
    if not barcode_value:
        return ""
    drawing = createBarcodeDrawing(
        "Code128",
        value=barcode_value,
        barHeight=18,
        humanReadable=False
    )
    svg = renderSVG.drawToString(drawing)
    start = svg.find("<svg")
    end = svg.rfind("</svg>")
    if start != -1 and end != -1:
        return svg[start:end + len("</svg>")]
    return svg

def get_recent_session_user():
    for session in Session.objects.filter(expire_date__gt=timezone.now()).order_by("-expire_date")[:20]:
        data = session.get_decoded()
        if data.get("user_id") and data.get("user_name"):
            return data
    return {}

def get_login_location(request):
    if not request.session.get("user_id") or not request.session.get("user_name"):
        recent_user = get_recent_session_user()
        request.session["user_id"] = recent_user.get("user_id", request.session.get("user_id", ""))
        request.session["user_name"] = recent_user.get("user_name", request.session.get("user_name", ""))
    location_id = request.session.get("loc_id")
    location_name = request.session.get("location_name")
    if not location_id and request.session.get("user_id"):
        user_info = UserInfos.objects.filter(user_id=request.session.get("user_id")).first() or UserInfos.objects.filter(login_user_id=request.session.get("user_id")).first()
        location_id = user_info.loc_id if user_info else None
    if not location_id and request.session.get("user_name"):
        user_info = UserInfos.objects.filter(user_name=request.session.get("user_name"), loc_id__isnull=False).order_by("-id").first()
        location_id = user_info.loc_id if user_info else None
    location = LocationInfos.objects.filter(id=location_id, status=1).first() if location_id else None
    if location:
        request.session["loc_id"] = location.id
        request.session["location_name"] = location.division
        return location.id, location.division
    return "", ""

def add_diagnosis_payment_page(request):
    fixed_location_id, fixed_location_name = get_login_location(request)
    return render(request, 'diagnosis/transaction.html', {
        "fixed_location_id": fixed_location_id or "",
        "fixed_location_name": fixed_location_name or "",
    })

def search_diagnosis_patient(request):
    query = (request.GET.get("q") or "").strip()
    if not query:
        return JsonResponse({"patients": []})

    like = f"%{query}%"
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.user_info_id, '', p.patient_name,
                   COALESCE(p.age_y, 0), COALESCE(p.age_m, 0), COALESCE(p.age_d, 0),
                   COALESCE(p.gender, ''), COALESCE(p.present_mobile, ''),
                   COALESCE(p.present_address, '')
            FROM patient_info p
            WHERE p.patient_name LIKE %s
               OR p.present_mobile LIKE %s
               OR p.present_address LIKE %s
            ORDER BY p.id DESC
            LIMIT 10
        """, [like, like, like])
        rows = cursor.fetchall()

    return JsonResponse({"patients": [
        {
            "patient_id": row[0], "title": row[1], "name": row[2],
            "age_y": row[3], "age_m": row[4], "age_d": row[5],
            "gender": row[6], "phone": row[7], "address": row[8],
        }
        for row in rows
    ]})

def edit_diagnosis_payment_page(request, id):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT
            m.id, m.tran_id, m.invoice_ref, m.loc_id, m.store_id,
            m.tran_type, m.tran_method, m.tran_type_with,
            tw.tran_method AS tran_with_method,
            m.tran_user, COALESCE(m.user_name, m.tran_user, '') AS user_name,
            loc.division AS location_name,
            m.bill_amount, m.discount, m.net_amount, m.payment,m.due_col,m.due_disc, m.due, m.tran_date,
            m.doctor_id, COALESCE(doc.name, '') AS doctor_name,
            COALESCE(doc.specialization, '') AS doctor_speciality, COALESCE(doc.chamber, '') AS doctor_chamber,
            m.sr_id, COALESCE(sr.name, '') AS sr_name,
            m.patient_id, COALESCE(patient_user.title, '') AS patient_title, COALESCE(p.patient_name, m.user_name, '') AS patient_name,
            COALESCE(p.age_y, 0) AS patient_age_y, COALESCE(p.age_m, 0) AS patient_age_m, COALESCE(p.age_d, 0) AS patient_age_d,
            COALESCE(p.gender, '') AS patient_gender, COALESCE(p.present_mobile, '') AS patient_phone, COALESCE(p.present_address, '') AS patient_address
        FROM transaction__mains m
        LEFT JOIN transaction__withs tw ON tw.id = m.tran_type_with
        LEFT JOIN location__infos loc ON loc.id = m.loc_id
        LEFT JOIN doctors_info doc ON doc.custom_doc_id COLLATE utf8mb4_unicode_ci = m.doctor_id COLLATE utf8mb4_unicode_ci
        LEFT JOIN item__sr_agents sr ON sr.custom_sr_id COLLATE utf8mb4_unicode_ci = m.sr_id COLLATE utf8mb4_unicode_ci
        LEFT JOIN patient_info p ON p.user_info_id COLLATE utf8mb4_unicode_ci = m.patient_id COLLATE utf8mb4_unicode_ci
        LEFT JOIN user__infos patient_user ON patient_user.user_id COLLATE utf8mb4_unicode_ci = m.patient_id COLLATE utf8mb4_unicode_ci
        WHERE m.id = %s AND m.tran_type = 10
        LIMIT 1
    """, [id])
    rows = dictfetchall(cursor)
    transaction = rows[0] if rows else None
    if not transaction:
        return redirect('diag_payment_list')
    print("========== EDIT TRANSACTION ==========")
    print("Due      :", transaction["due"])
    print("Due Col  :", transaction["due_col"])
    print("Due Disc :", transaction["due_disc"])
    print("Tran ID  :", transaction["tran_id"])
    print("======================================")
    cursor.execute("""
        SELECT
            d.id, d.tran_head_id AS product_id, h.tran_head_name AS product_name,
            d.quantity, d.cp, d.mrp, d.tot_amount AS total, d.expiry_date,
            COALESCE(d.tran_groupe_id, h.groupe_id) AS tran_groupe_id, g.tran_method AS tran_group_method
        FROM transaction__details d
        LEFT JOIN transaction__heads h ON h.id = d.tran_head_id
        LEFT JOIN transaction__groupes g ON g.id = COALESCE(d.tran_groupe_id, h.groupe_id)
        WHERE d.tran_id = %s
        ORDER BY d.id ASC
    """, [transaction["tran_id"]])
    details = dictfetchall(cursor)
    transaction["tran_group_id"] = details[0].get("tran_groupe_id") if details else ""
    transaction["tran_group_method"] = details[0].get("tran_group_method") if details else ""
    transaction["tran_date"] = transaction["tran_date"].strftime("%Y-%m-%d") if transaction.get("tran_date") else ""
    for item in details:
        item["expiry_date"] = item["expiry_date"].strftime("%Y-%m-%d") if item.get("expiry_date") else ""
    return render(request, 'diagnosis/transaction.html', {
        "edit_transaction": transaction,
        "edit_details": details,
        "edit_transaction_json": json.dumps(transaction, default=str),
        "edit_details_json": json.dumps(details, default=str),
        "edit_mode": True,
        "fixed_location_id": transaction.get("loc_id") or "",
        "fixed_location_name": transaction.get("location_name") or "",
    })



def diag_payment_list(request):
    # return render(request, 'pharmacy/medicine_list.html')
    return render(request, 'diagnosis/transaction_list.html')

def insert_diagnosis_detail_rows(products, tran_id, tran_type, payment_method, invoice_ref, location_id, tran_type_with, user_id, tran_by, store_id, tran_date, status, discount, receive, payment, due, doctor_custom_id, patient_id, sr_id):
    details_data = []
    weights = [row[5] or 0 for row in products]
    discounts = allocate_amount(discount, weights)
    receives = allocate_amount(receive, weights)
    payments = allocate_amount(payment, weights)
    dues = allocate_amount(due, weights)
    for index, row in enumerate(products):
        product_id = row[0]
        qty = row[1] or 0
        cp = row[2] or 0
        mrp = row[3] or 0
        expiry = row[4] or None
        total = row[5] or 0
        details_data.append([
            tran_id, tran_type, payment_method, invoice_ref, location_id, tran_type_with, user_id, tran_by,
            product_id, 1, qty, 0, 0,
            0, total, max(float(total) - float(discounts[index]), 0), cp, mrp, expiry,
            store_id, tran_date, status,
            discounts[index], receives[index], payments[index], dues[index],
            doctor_custom_id, patient_id, sr_id
        ])
    details_query = """
        INSERT INTO transaction__details
        (
            tran_id, tran_type, tran_method, invoice_ref,
            loc_id, tran_type_with, tran_user, tran_by,
            tran_head_id, quantity_actual, quantity,
            quantity_issue, quantity_return,
            unit_id, amount, tot_amount, cp, mrp, expiry_date,
            store_id, tran_date, status,
            discount, receive, payment, due,
            doctor_id, patient_id, sr_id
        )
        VALUES
        (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s
        )
    """
    if details_data:
        with connection.cursor() as cursor:
            cursor.executemany(details_query, details_data)

def product_search(request):
    q = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0))
    tran_main_head_id = request.GET.get('tran_main_head_id').strip()
    tran_group_id = request.GET.get('tran_group_id')
    limit = 10

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

# def add_payment_page(request):
#     return render(request, 'general_transaction/payment.html')

# def payment_list(request):
#     # return render(request, 'pharmacy/medicine_list.html')
#     return render(request, 'general_transaction/payment_list.html')

def get_supplier_combo_g(request):

    cursor = connection.cursor()

    sql = """
        SELECT
        m.id AS id,
        m.manufacturer_name
        FROM item__manufacturers m
        ORDER BY m.manufacturer_name;
    """
    params = []

    cursor.execute(sql, params)
    data = dictfetchall(cursor)
    print("DEBUG",data)

    return JsonResponse({
        "supplier_combo": data
    })

def payment_list_load(request):
    q = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    offset = int(request.GET.get('offset', 0))
    limit = 50

    sql = """
        SELECT 
            m.id,
            m.tran_id AS tran_id,
            m.tran_date AS tran_date,
            m.tran_type_with AS tran_type_with,
            m.tran_user AS tran_user,
            m.bill_amount AS bill_total,
            m.discount AS discount,
            m.net_amount AS net_total,
            m.receive AS advance,
            m.due_col AS due_collection,
            m.due_disc AS due_discount,
            m.due AS due
        FROM transaction__mains m
        WHERE 1=1
    """

    params = []

    # 🔥 SEARCH (optional)
    if q:
        sql += " AND (m.tran_id LIKE %s OR m.tran_user LIKE %s)"
        params.append(f"%{q}%")
        params.append(f"%{q}%")
    sql += " AND m.tran_id LIKE %s"
    params.append("GPA%")

    # 🔥 DATE FILTER (ALWAYS WORKS)
    if start_date:
        sql += " AND DATE(m.tran_date) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(m.tran_date) <= %s"
        params.append(end_date)

    sql += " ORDER BY m.id ASC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor = connection.cursor()
    cursor.execute(sql, params)
    data = dictfetchall(cursor)

    return JsonResponse({'results': data})


def payment_report_pdf(request):

    q = request.GET.get('q', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    sql = """
        SELECT 
            m.tran_id,
            m.tran_date,
            m.tran_type_with,
            m.tran_user,
            m.bill_amount,
            m.discount,
            m.net_amount,
            m.receive,
            m.due_col,
            m.due_disc,
            m.due
        FROM transaction__mains m
        WHERE 1=1
    """

    params = []

    if q:
        sql += " AND (m.tran_id LIKE %s OR m.tran_user LIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " AND m.tran_id LIKE %s"
    params.append("GPA%")

    if start_date:
        sql += " AND DATE(m.tran_date) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(m.tran_date) <= %s"
        params.append(end_date)

    sql += " ORDER BY m.id ASC"
    

    cursor = connection.cursor()
    cursor.execute(sql, params)
    data = dictfetchall(cursor)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    normal_style = styles["Normal"]

    elements = []

    # =========================
    # HEADER
    # =========================
    title = Paragraph("Payment List Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 10))

    date_text = f"""
    <b>Start Date:</b> {start_date if start_date else '-'}  
    <b>End Date:</b> {end_date if end_date else '-'}
    """

    date_para = Paragraph(date_text, normal_style)
    elements.append(date_para)
    elements.append(Spacer(1, 20))

    # =========================
    # TABLE DATA
    # =========================
    table_data = [
        ["SL","Tran ID","Date","Supplier","Tran User","Bill","Disc","Net","Adv","Due Col","Due Disc","Due"]
    ]

    for i, p in enumerate(data, 1):
        table_data.append([
            i,
            p["tran_id"],
            str(p["tran_date"]),
            p["tran_type_with"],
            p["tran_user"],
            
            p["bill_amount"],
            p["discount"],
            p["net_amount"],
            p["receive"],
            p["due_col"],
            p["due_disc"],
            p["due"]
        ])

    table = Table(table_data)

    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))

    elements.append(table)

    # =========================
    # BUILD PDF
    # =========================
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf")

def get_divisions_combo(request):

    cursor = connection.cursor()

    sql = """
        SELECT
        MIN(loc.id) AS id,
        loc.division
        FROM location__infos loc
        GROUP BY loc.division
        ORDER BY loc.division;
    """
    params = []

    cursor.execute(sql, params)
    data = dictfetchall(cursor)
    print("DEBUG",data)

    return JsonResponse({
        "divisions_combo": data
    }, safe=False)

# def get_supplier_combo(request):

#     cursor = connection.cursor()

#     sql = """
#         SELECT
#         m.id AS id,
#         m.manufacturer_name
#         FROM item__manufacturers m
#         ORDER BY m.manufacturer_name;
#     """
#     params = []

#     cursor.execute(sql, params)
#     data = dictfetchall(cursor)
#     print("DEBUG",data)

#     return JsonResponse({
#         "supplier_combo": data
#     })

# def get_transaction_with_users_combo(request):

#     data = UserInfos.objects.filter(
#         tran_user_type__tran_type=1,
#         tran_user_type__tran_method='payment'
#     ).values(
#         'id',
#         'user_name',
#         'tran_user_type_id'
#     ).order_by('user_name')

#     return JsonResponse(list(data), safe=False)
def get_transaction_with_combo_p(request):
    data = TransactionWiths.objects.filter(
        tran_type=10,
        tran_method='receive',
        status=1
    ).values('id', 'tran_with_name')

    return JsonResponse(list(data), safe=False)




# @csrf_exempt
# @transaction.atomic
# def save_general_payment(request):

#     if request.method != "POST":
#         return JsonResponse({"success": False}, status=405)

#     try:
#         data = json.loads(request.body)

#         # ---- Form Data ----
#         store_id = data.get("store")
#         location_id = data.get("location")
#         user_id = data.get("supplier")
#         tran_type_with = data.get("tran_type_with")

#         if not tran_type_with:
#             return JsonResponse({"success": False, "message": "Transaction With required"}, status=400)

#         invoice = data.get("invoice")
#         payment_method = data.get("payment_method")

#         bill_amount = data.get("bill_amount") or 0
#         discount = data.get("discount") or 0
#         net_amount = data.get("net_amount") or 0
#         receive = 0   # always 0 from frontend
#         payment = data.get("payment") or 0 
#         due = data.get("due") or 0

#         tran_date = data.get("tran_date")

#         if tran_date:
#             tran_date = datetime.combine(
#                 datetime.strptime(tran_date, "%Y-%m-%d").date(),
#                 timezone.localtime().time()
#             )
#         else:
#             tran_date = timezone.localtime()

#         products = data.get("products", [])

#         # ---- Generate ID ----
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT tran_id 
#                 FROM transaction__mains
#                 WHERE tran_id LIKE 'GPA%'
#                 ORDER BY tran_id DESC
#                 LIMIT 1
#             """)
#             row = cursor.fetchone()

#             last_number = int(row[0][3:]) if row else 0
#             tran_id = "GPA" + str(last_number + 1).zfill(9)

#         tran_type = 1   # ✅ GENERAL
#         status = 1

#         # ---- MAIN TABLE ----
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 INSERT INTO transaction__mains
#                 (tran_id, tran_type, tran_method, tran_user, tran_type_with,
#                  store_id, loc_id, tran_date, status, invoice,
#                  bill_amount, discount, net_amount, payment, due)
#                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#             """, [
#                 tran_id, tran_type, payment_method, user_id, tran_type_with,
#                 store_id, location_id, tran_date, status, invoice,
#                 bill_amount, discount, net_amount, payment, due
#             ])

#         # ---- DETAILS ----
#         details_data = []

#         for row in products:
#             details_data.append([
#                 tran_id,
#                 tran_type,
#                 payment_method,
#                 invoice,
#                 location_id,
#                 tran_type_with,
#                 row[0],   # product id
#                 1,   # qty
#                 row[1],
#                 0,
#                 0,
#                 0,
#                 row[2],   # amount
#                 row[5],   # total
#                 0,   # cp
#                 0,   # mrp
#                 row[4],   # expiry
#                 store_id,
#                 tran_date,
#                 status,
#                 discount,
#                 0,
#                 payment,
#                 due
#             ])

#         query = """
#             INSERT INTO transaction__details
#             (tran_id, tran_type, tran_method, invoice, loc_id, tran_type_with,
#              tran_head_id, quantity_actual, quantity, quantity_issue, quantity_return,
#              unit_id, amount, tot_amount, cp, mrp, expiry_date, store_id,
#              tran_date, status, discount, receive, payment, due)
#             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#         """

#         with connection.cursor() as cursor:
#             cursor.executemany(query, details_data)

#         return JsonResponse({"success": True, "tran_id": tran_id})

#     except Exception as e:
#         print("🔥 GENERAL PAYMENT ERROR:", e)
#         return JsonResponse({"success": False, "error": str(e)}, status=500)
    

def add_receive_page(request):
    return render(request, 'general_transaction/receive.html')
def receive_list(request):
    # return render(request, 'pharmacy/medicine_list.html')
    return render(request, 'general_transaction/receive_list.html')

def receive_list_load(request):
    q = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    offset = int(request.GET.get('offset', 0))
    limit = 50

    sql = """
        SELECT 
            m.id,
            m.tran_id AS tran_id,
            m.tran_date AS tran_date,
            m.tran_type_with AS tran_type_with,
            m.tran_user AS tran_user,
            m.bill_amount AS bill_total,
            m.discount AS discount,
            m.net_amount AS net_total,
            m.receive AS advance,
            m.due_col AS due_collection,
            m.due_disc AS due_discount,
            m.due AS due
        FROM transaction__mains m
        WHERE 1=1
    """

    params = []

    # 🔥 SEARCH (optional)
    if q:
        sql += " AND (m.tran_id LIKE %s OR m.tran_user LIKE %s)"
        params.append(f"%{q}%")
        params.append(f"%{q}%")
    sql += " AND m.tran_id LIKE %s"
    params.append("GRE%")

    # 🔥 DATE FILTER (ALWAYS WORKS)
    if start_date:
        sql += " AND DATE(m.tran_date) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(m.tran_date) <= %s"
        params.append(end_date)

    sql += " ORDER BY m.id ASC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor = connection.cursor()
    cursor.execute(sql, params)
    data = dictfetchall(cursor)

    return JsonResponse({'results': data})



def receive_report_pdf(request):

    q = request.GET.get('q', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    sql = """
        SELECT 
            m.tran_id,
            m.tran_date,
            m.tran_type_with,
            m.tran_user,
            m.bill_amount,
            m.discount,
            m.net_amount,
            m.receive,
            m.due_col,
            m.due_disc,
            m.due
        FROM transaction__mains m
        WHERE 1=1
    """

    params = []

    if q:
        sql += " AND (m.tran_id LIKE %s OR m.tran_user LIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " AND m.tran_id LIKE %s"
    params.append("GRE%")

    if start_date:
        sql += " AND DATE(m.tran_date) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(m.tran_date) <= %s"
        params.append(end_date)

    sql += " ORDER BY m.id ASC"
    

    cursor = connection.cursor()
    cursor.execute(sql, params)
    data = dictfetchall(cursor)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    normal_style = styles["Normal"]

    elements = []

    # =========================
    # HEADER
    # =========================
    title = Paragraph("Receive List Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 10))

    date_text = f"""
    <b>Start Date:</b> {start_date if start_date else '-'}  
    <b>End Date:</b> {end_date if end_date else '-'}
    """

    date_para = Paragraph(date_text, normal_style)
    elements.append(date_para)
    elements.append(Spacer(1, 20))

    # =========================
    # TABLE DATA
    # =========================
    table_data = [
        ["SL","Tran ID","Date","Supplier","Tran User","Bill","Disc","Net","Adv","Due Col","Due Disc","Due"]
    ]

    for i, p in enumerate(data, 1):
        table_data.append([
            i,
            p["tran_id"],
            str(p["tran_date"]),
            p["tran_type_with"],
            p["tran_user"],
            
            p["bill_amount"],
            p["discount"],
            p["net_amount"],
            p["receive"],
            p["due_col"],
            p["due_disc"],
            p["due"]
        ])

    table = Table(table_data)

    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))

    elements.append(table)

    # =========================
    # BUILD PDF
    # =========================
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf")

@csrf_exempt
@transaction.atomic
def save_general_receive(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        data = json.loads(request.body)

        # ---- Form Data ----
        store_id = data.get("store")
        location_id = data.get("location")
        user_id = data.get("supplier")
        tran_type_with = data.get("tran_type_with")

        if not tran_type_with:
            return JsonResponse({"success": False, "message": "Transaction With required"}, status=400)

        invoice_ref = data.get("invoice_ref")
        payment_method = data.get("payment_method")
        tran_method = payment_method
        bill_amount = data.get("bill_amount") or 0
        discount = data.get("discount") or 0
        net_amount = data.get("net_amount") or 0
        receive = data.get("receive") or 0   # always 0 from frontend
        payment =  0
        due = data.get("due") or 0

        tran_date = data.get("tran_date")

        if tran_date:
            tran_date = datetime.combine(
                datetime.strptime(tran_date, "%Y-%m-%d").date(),
                timezone.localtime().time()
            )
        else:
            tran_date = timezone.localtime()

        products = data.get("products", [])

        bill_amount = sum(float(row[5] or 0) for row in products)
        discount = float(discount or 0)
        net_amount = max(bill_amount - discount, 0)
        due = max(net_amount - receive, 0)

        # ---- Generate ID ----
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tran_id 
                FROM transaction__mains
                WHERE tran_id LIKE 'GRE%'
                ORDER BY tran_id DESC
                LIMIT 1
            """)
            row = cursor.fetchone()

            last_number = int(row[0][3:]) if row else 0
            tran_id = "GRE" + str(last_number + 1).zfill(9)

        tran_type = 1   # ✅ GENERAL
        status = 1

        # ---- MAIN TABLE ----
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO transaction__mains
                (tran_id, tran_type, tran_method, tran_user, tran_type_with,
                 store_id, loc_id, tran_date, status, invoice_ref,
                 bill_amount, discount, net_amount, payment, due)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                tran_id, tran_type, tran_method, user_id, tran_type_with,
                store_id, location_id, tran_date, status, invoice_ref,
                bill_amount, discount, net_amount, payment, due
            ])

        # ---- DETAILS ----
        details_data = []
        weights = [float(row[5] or 0) for row in products]
        discounts = allocate_amount(discount, weights)
        receives = allocate_amount(receive, weights)
        dues = allocate_amount(due, weights)

        for index, row in enumerate(products):
            details_data.append([
                tran_id,
                tran_type,
                tran_method,
                invoice_ref,
                location_id,
                tran_type_with,
                row[0],   # product id
                1,   # qty
                row[1],
                0,
                0,
                0,
                row[5],   # amount (line bill)
                max(float(row[5] or 0) - float(discounts[index]), 0),   # tot_amount (line net)
                0,   # cp
                0,   # mrp
                row[4],   # expiry
                store_id,
                tran_date,
                status,
                discounts[index],
                receives[index],
                0,
                dues[index]
            ])

        query = """
            INSERT INTO transaction__details
            (tran_id, tran_type, tran_method, invoice_ref, loc_id, tran_type_with,
             tran_head_id, quantity_actual, quantity, quantity_issue, quantity_return,
             unit_id, amount, tot_amount, cp, mrp, expiry_date, store_id,
             tran_date, status, discount, receive, payment, due)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        with connection.cursor() as cursor:
            cursor.executemany(query, details_data)  

        set_payment_mode(tran_id, "receive")
        return JsonResponse({"success": True, "tran_id": tran_id})

    except Exception as e:
        print("🔥 GENERAL PAYMENT ERROR:", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
# def get_transaction_with_users_combo_p(request):

#         data = UserInfos.objects.filter(
#             tran_user_type__tran_type=1,
#             tran_user_type__tran_method='receive'
#         ).values(
#             'id',
#             'user_name',
#             'tran_user_type_id'
#         ).order_by('user_name')

#         return JsonResponse(list(data), safe=False)



def get_transaction_with_combo_r(request):
    data = TransactionWiths.objects.filter(
        tran_type=1,
        tran_method='receive',
        status=1
    ).values('id', 'tran_with_name')

    return JsonResponse(list(data), safe=False)

def get_supplier_by_tran_with_g(request):
    tran_with_id = request.GET.get('tran_with_id')

    if not tran_with_id:
        return JsonResponse([], safe=False)

    data = list(UserInfos.objects.filter(
        tran_user_type_id=int(tran_with_id),   # 🔥 FIX HERE
        tran_user_type__tran_type=1
    ).values('id', 'user_name'))
    print("tran_with_id:", tran_with_id, type(tran_with_id))
    return JsonResponse(data, safe=False)


# office bazar

def add_payment_page_ob(request):
    return render(request, 'general_transaction/office_bazar/payment.html')

def payment_list_ob(request):
    # return render(request, 'pharmacy/medicine_list.html')
    return render(request, 'general_transaction/office_bazar/payment_list.html')

def payment_list_load_ob(request):
    q = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    offset = int(request.GET.get('offset', 0))
    limit = 50

    sql = """
        SELECT 
            m.id,
            m.tran_id AS tran_id,
            m.tran_date AS tran_date,
            m.tran_type_with AS tran_type_with,
            m.tran_user AS tran_user,
            m.bill_amount AS bill_total,
            m.discount AS discount,
            m.net_amount AS net_total,
            m.receive AS advance,
            m.due_col AS due_collection,
            m.due_disc AS due_discount,
            m.due AS due
        FROM transaction__mains m
        WHERE 1=1
    """

    params = []

    # 🔥 SEARCH (optional)
    if q:
        sql += " AND (m.tran_id LIKE %s OR m.tran_user LIKE %s)"
        params.append(f"%{q}%")
        params.append(f"%{q}%")
    sql += " AND m.tran_id LIKE %s"
    params.append("OBZ%")

    # 🔥 DATE FILTER (ALWAYS WORKS)
    if start_date:
        sql += " AND DATE(m.tran_date) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(m.tran_date) <= %s"
        params.append(end_date)

    sql += " ORDER BY m.id ASC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor = connection.cursor()
    cursor.execute(sql, params)
    data = dictfetchall(cursor)

    return JsonResponse({'results': data})

def get_transaction_with_combo_ob(request):
    data = TransactionWiths.objects.filter(
        tran_type=1,
        tran_method='payment',
        status=1
    ).values('id', 'tran_with_name')

    return JsonResponse(list(data), safe=False)

def get_supplier_by_tran_with_ob(request):
    tran_with_id = request.GET.get('tran_with_id')

    if not tran_with_id:
        return JsonResponse([], safe=False)

    data = list(UserInfos.objects.filter(
        tran_user_type_id=int(tran_with_id),   # 🔥 FIX HERE
        tran_user_type__tran_type=1
    ).values('id', 'user_name'))
    print("tran_with_id:", tran_with_id, type(tran_with_id))
    return JsonResponse(data, safe=False)

@csrf_exempt
@transaction.atomic
def save_general_payment_ob(request):

    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        data = json.loads(request.body)

        # ---- Form Data ----
        store_id = data.get("store")
        location_id = data.get("location")
        user_id = data.get("supplier")
        tran_type_with = data.get("tran_type_with")

        if not tran_type_with:
            return JsonResponse({"success": False, "message": "Transaction With required"}, status=400)

        invoice_ref = data.get("invoice_ref")
        payment_method = data.get("payment_method")

        bill_amount = data.get("bill_amount") or 0
        discount = data.get("discount") or 0
        net_amount = data.get("net_amount") or 0
        receive = 0   # always 0 from frontend
        payment = data.get("payment") or 0 
        due = data.get("due") or 0

        tran_date = data.get("tran_date")

        if tran_date:
            tran_date = datetime.combine(
                datetime.strptime(tran_date, "%Y-%m-%d").date(),
                timezone.localtime().time()
            )
        else:
            tran_date = timezone.localtime()

        products = data.get("products", [])

        bill_amount = sum(float(row[5] or 0) for row in products)
        discount = float(discount or 0)
        net_amount = max(bill_amount - discount, 0)
        due = max(net_amount - payment, 0)

        # ---- Generate ID ----
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tran_id 
                FROM transaction__mains
                WHERE tran_id LIKE 'OBZ%'
                ORDER BY tran_id DESC
                LIMIT 1
            """)
            row = cursor.fetchone()

            last_number = int(row[0][3:]) if row else 0
            tran_id = "OBZ" + str(last_number + 1).zfill(9)

        tran_type = 1   # ✅ GENERAL
        status = 1

        # ---- MAIN TABLE ----
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO transaction__mains
                (tran_id, tran_type, tran_method, tran_user, tran_type_with,
                 store_id, loc_id, tran_date, status, invoice_ref,
                 bill_amount, discount, net_amount, payment, due)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                tran_id, tran_type, payment_method, user_id, tran_type_with,
                store_id, location_id, tran_date, status, invoice_ref,
                bill_amount, discount, net_amount, payment, due
            ])

        # ---- DETAILS ----
        details_data = []
        weights = [float(row[5] or 0) for row in products]
        discounts = allocate_amount(discount, weights)
        payments = allocate_amount(payment, weights)
        dues = allocate_amount(due, weights)

        for index, row in enumerate(products):
            details_data.append([
                tran_id,
                tran_type,
                payment_method,
                invoice,
                location_id,
                tran_type_with,
                row[0],   # product id
                1,   # qty
                row[1],
                0,
                0,
                0,
                row[5],   # amount (line bill)
                max(float(row[5] or 0) - float(discounts[index]), 0),   # tot_amount (line net)
                0,   # cp
                0,   # mrp
                row[4],   # expiry
                store_id,
                tran_date,
                status,
                discounts[index],
                0,
                payments[index],
                dues[index]
            ])

        query = """
            INSERT INTO transaction__details
            (tran_id, tran_type, tran_method, invoice, loc_id, tran_type_with,
             tran_head_id, quantity_actual, quantity, quantity_issue, quantity_return,
             unit_id, amount, tot_amount, cp, mrp, expiry_date, store_id,
             tran_date, status, discount, receive, payment, due)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        with connection.cursor() as cursor:
            cursor.executemany(query, details_data)

        set_payment_mode(tran_id, "payment")
        return JsonResponse({"success": True, "tran_id": tran_id})

    except Exception as e:
        print("🔥 GENERAL PAYMENT ERROR:", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)





def get_page_init_add_payment(request):
    
    page_id = request.GET.get('page_id')

    print("DEBUG======>>>>>>>>>>>>",page_id)

    cursor = connection.cursor()

    sql = """
        SELECT
        s.tran_main_head_id AS tran_main_head_id,
        s.user_tran_method AS user_tran_method,
        s.user_tran_with_id AS user_tran_with_id,
        s.tran_method AS tran_method,
        s.tran_group_id AS tran_group_id
        FROM page_init s
        WHERE s.page_id = %s

    """
    params = [page_id]

    cursor.execute(sql, params)
    # data = dictfetchall(cursor)

    data  = [
        {
            "tran_main_head_id": row[0],
            "user_tran_method": row[1],
            "user_tran_with_id": row[2],
            "tran_method": row[3],
            "tran_group_id": row[4]
        }
        for row in cursor.fetchall()
    ]    
    print("DEBUG-------<><><><><><><><>",data)

    return JsonResponse({
        "get_page_init_data": data
    })    

    # diagnosis


@csrf_exempt
@transaction.atomic
def save_diagnosis_payment(request):

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Invalid request method"
        }, status=405)

    try:
        data = json.loads(request.body)

        # TRANSACTION BY
        # logged-in user je transaction create korbe
        # =========================
        tran_by = None

        # 1) Django auth user
        if request.user.is_authenticated:
            tran_by = request.user.username or str(request.user.id)

        # 2) Custom session login fallback
        if not tran_by:
            tran_by = (
                request.session.get("username")
                or request.session.get("user_name")
                or request.session.get("name")
                or request.session.get("user_id")
                or request.session.get("id")
            )

        # 3) Final fallback
        if tran_by:
            tran_by = str(tran_by)
        else:
            tran_by = "Unknown"

        # =========================
        # FORM DATA
        # =========================
        store_id = data.get("store")
        location_id, _location_name = get_login_location(request)
        location_id = location_id or data.get("location")
        if not location_id:
            return JsonResponse({"success": False, "message": "Login user location not found"}, status=400)
        user_id = data.get("supplier")
        user_name = data.get("user_name")

        tran_type_with = data.get("tran_type_with")
        if not tran_type_with:
            return JsonResponse({
                "success": False,
                "message": "Transaction With required"
            }, status=400)

        invoice_ref = data.get("invoice_ref")
        edit_id = data.get("edit_id")
        payment_method = data.get("payment_method") or "cash"

        bill_amount = data.get("bill_amount") or 0
        discount = data.get("discount") or 0
        net_amount = data.get("net_amount") or 0

        receive = data.get("receive") or 0
        payment = data.get("payment") or 0
        due = data.get("due") or 0

        products = data.get("products", [])

        if not products:
            return JsonResponse({
                "success": False,
                "message": "No products selected"
            }, status=400)

        bill_amount = sum(float(row[5] or 0) for row in products)
        discount = float(discount or 0)
        net_amount = max(bill_amount - discount, 0)
        due = max(net_amount - (receive or payment), 0)

        # =========================
        # DATE
        # =========================
        tran_date = data.get("tran_date")

        if tran_date:
            tran_date = datetime.combine(
                datetime.strptime(tran_date, "%Y-%m-%d").date(),
                timezone.localtime().time()
            )
        else:
            tran_date = timezone.localtime()

        # =========================
        # DOCTOR CUSTOM DOC ID
        # frontend theke numeric doctor id ashleo
        # transaction table e custom_doc_id save hobe
        # =========================
        referred_doctor_id = data.get("referred_doctor_id")
        doctor_custom_id = None

        if referred_doctor_id:
            referred_doctor_id = str(referred_doctor_id).strip()

            with connection.cursor() as cursor:
                if referred_doctor_id.isdigit():
                    cursor.execute("""
                        SELECT custom_doc_id
                        FROM doctors_info
                        WHERE id = %s
                        LIMIT 1
                    """, [int(referred_doctor_id)])
                else:
                    cursor.execute("""
                        SELECT custom_doc_id
                        FROM doctors_info
                        WHERE custom_doc_id = %s
                        LIMIT 1
                    """, [referred_doctor_id])

                doc_row = cursor.fetchone()

            if doc_row and doc_row[0]:
                doctor_custom_id = doc_row[0]

        if not doctor_custom_id:
            return JsonResponse({
                "success": False,
                "message": "Doctor ID not found. Please select a valid doctor."
            }, status=400)

        print("REFERRED DOCTOR ID:", referred_doctor_id)
        print("DOCTOR CUSTOM ID:", doctor_custom_id)

        # =========================
        # PATIENT ENTRY
        # 1) user__infos e common data
        # 2) patient_info e patient data
        # 3) user__infos.user_id save hobe mains/details patient_id te
        # =========================
        patient_title = (data.get("patient_title") or "").strip()
        patient_name = (data.get("patient_name") or "").strip()

        patient_age_y = data.get("patient_age_y") or 0
        patient_age_m = data.get("patient_age_m") or 0
        patient_age_d = data.get("patient_age_d") or 0

        try:
            patient_age_y = int(patient_age_y)
        except Exception:
            patient_age_y = 0

        try:
            patient_age_m = int(patient_age_m)
        except Exception:
            patient_age_m = 0

        try:
            patient_age_d = int(patient_age_d)
        except Exception:
            patient_age_d = 0

        patient_gender = (data.get("patient_gender") or "").strip()
        patient_phone = (data.get("patient_phone") or "").strip()
        patient_address = (data.get("patient_address") or "").strip()

        if not patient_name:
            return JsonResponse({
                "success": False,
                "message": "Patient name required"
            }, status=400)

        patient_id = None
        patient_row = None
        incoming_patient_id = (data.get("patient_id") or "").strip() if data.get("patient_id") else ""

        # user_role column bigint, tai patient role er actual numeric id dite hobe
        PATIENT_ROLE_ID = 2

        with connection.cursor() as cursor:

            # 1) Phone diye existing patient user__infos check
            if incoming_patient_id:
                patient_id = incoming_patient_id
            elif patient_phone:
                cursor.execute("""
                    SELECT user_id
                    FROM user__infos
                    WHERE user_phone = %s
                    LIMIT 1
                """, [patient_phone])

                patient_row = cursor.fetchone()

            if patient_id:
                pass
            elif patient_row and patient_row[0]:
                patient_id = patient_row[0]

            else:
                # 2) New user__infos.user_id generate
                cursor.execute("""
                    SELECT user_id
                    FROM user__infos
                    WHERE user_id LIKE 'PAT%%'
                    ORDER BY user_id DESC
                    LIMIT 1
                """)

                last_patient = cursor.fetchone()

                if last_patient and last_patient[0]:
                    last_number = int(last_patient[0][3:])
                else:
                    last_number = 0

                patient_id = "PAT" + str(last_number + 1).zfill(9)

                # 3) Insert common patient data into user__infos
                cursor.execute("""
                    INSERT INTO user__infos
                    (
                        user_id,
                        title,
                        user_name,
                        user_phone,
                        gender,
                        loc_id,
                        user_role,
                        tran_method,
                        tran_with_id,
                        address,
                        store_id,
                        status,
                        added_at,
                        updated_at
                    )
                    VALUES
                    (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        NOW(), NOW()
                    )
                """, [
                    patient_id,
                    patient_title,
                    patient_name,
                    patient_phone,
                    patient_gender,
                    location_id,
                    PATIENT_ROLE_ID,
                    payment_method,
                    tran_type_with,
                    patient_address,
                    store_id,
                    1
                ])

            # 4) patient_info table e oi patient already ache kina check
            cursor.execute("""
                SELECT id
                FROM patient_info
                WHERE user_info_id = %s
                LIMIT 1
            """, [patient_id])

            diagnosis_patient_row = cursor.fetchone()

            if not diagnosis_patient_row:
                # 5) Insert patient-specific data into patient_info
                cursor.execute("""
                    INSERT INTO patient_info
                    ( 
                        patient_name,
                        age_y,
                        age_m,
                        age_d,
                        gender,
                        present_mobile,
                        present_address,
                        user_info_id,
                        created_at,
                        updated_at
                    )
                    VALUES
                    (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        NOW(), NOW()
                    )
                """, [
                    patient_name,
                    patient_age_y,
                    patient_age_m,
                    patient_age_d,
                    patient_gender,
                    patient_phone,
                    patient_address,
                    patient_id
                ])

        print("PATIENT USER_INFO ID:", patient_id)

        if not patient_id:
            return JsonResponse({
                "success": False,
                "message": "Patient ID could not be generated."
            }, status=400)

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE user__infos
                SET title = %s, user_name = %s, user_phone = %s, gender = %s, loc_id = %s, tran_method = %s, tran_with_id = %s, address = %s, store_id = %s, updated_at = NOW()
                WHERE user_id = %s
            """, [patient_title, patient_name, patient_phone, patient_gender, location_id, payment_method, tran_type_with, patient_address, store_id, patient_id])
            cursor.execute("""
                UPDATE patient_info
                SET patient_name = %s, age_y = %s, age_m = %s, age_d = %s, gender = %s, present_mobile = %s, present_address = %s, updated_at = NOW()
                WHERE user_info_id = %s
            """, [patient_name, patient_age_y, patient_age_m, patient_age_d, patient_gender, patient_phone, patient_address, patient_id])

        # =========================
        # SR CUSTOM ID
        # item__sr_agents.custom_sr_id save hobe transaction table e
        # =========================
        referred_sr_id = data.get("referred_sr_id")
        sr_id = None
        sr_row = None

        if referred_sr_id:
            referred_sr_id = str(referred_sr_id).strip()

            with connection.cursor() as cursor:
                if referred_sr_id.isdigit():
                    cursor.execute("""
                        SELECT custom_sr_id
                        FROM item__sr_agents
                        WHERE id = %s
                        LIMIT 1
                    """, [int(referred_sr_id)])
                else:
                    cursor.execute("""
                        SELECT custom_sr_id
                        FROM item__sr_agents
                        WHERE custom_sr_id = %s
                        LIMIT 1
                    """, [referred_sr_id])

                sr_row = cursor.fetchone()

            if sr_row and sr_row[0]:
                sr_id = sr_row[0]

        print("REFERRED SR ID:", referred_sr_id)
        print("SR ROW:", sr_row)
        print("FINAL SR ID:", sr_id)

        tran_type = 10
        status = 1

        if edit_id:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tran_id, COALESCE(invoice_ref, tran_id)
                    FROM transaction__mains
                    WHERE id = %s AND tran_type = 10
                    LIMIT 1
                """, [edit_id])
                edit_row = cursor.fetchone()
                if not edit_row:
                    return JsonResponse({"success": False, "message": "Diagnosis transaction not found"}, status=404)
                tran_id = edit_row[0]
                invoice_ref = edit_row[1] or tran_id
                cursor.execute("""
                    UPDATE transaction__mains
                    SET tran_method = %s, invoice_ref = %s, loc_id = %s, tran_type_with = %s, tran_user = %s, tran_by = %s, user_name = %s,
                        store_id = %s, tran_date = %s, status = %s, bill_amount = %s, discount = %s, net_amount = %s, receive = %s, payment = %s, due = %s,
                        doctor_id = %s, patient_id = %s, sr_id = %s, updated_at = NOW()
                    WHERE id = %s
                """, [payment_method, invoice_ref, location_id, tran_type_with, user_id, tran_by, user_name, store_id, tran_date, status, bill_amount, discount, net_amount, receive, payment, due, doctor_custom_id, patient_id, sr_id, edit_id])
                cursor.execute("DELETE FROM transaction__details WHERE tran_id = %s", [tran_id])
                cursor.execute("""
                SELECT due_col, due_disc
                FROM transaction__mains
                WHERE tran_id=%s
                """,[tran_id])
    
                row = cursor.fetchone()
    
                due_col = row[0] or 0
                due_disc = row[1] or 0
            insert_diagnosis_detail_rows(products, tran_id, tran_type, payment_method, invoice_ref, location_id, tran_type_with, user_id, tran_by, store_id, tran_date, status, discount, receive, payment, due, doctor_custom_id, patient_id, sr_id)
            
            return JsonResponse({
                "success": True,
                "updated": True,
                "tran_id": tran_id,
                "invoice_ref": invoice_ref,
                "invoice": invoice_ref,
                "invoice_barcode_svg": build_invoice_barcode_svg(invoice_ref),
                "patient_barcode_svg": build_invoice_barcode_svg(patient_id),
                "doctor_id": doctor_custom_id,
                "patient_id": patient_id,
                "sr_id": sr_id,
                "tran_by": tran_by,
                "due_col": due_col,
                "due_disc": due_disc
                
            })

        # =========================
        # GENERATE TRANSACTION ID
        # Diagnosis Payment prefix: DPA
        # =========================
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tran_id
                FROM transaction__mains
                WHERE tran_id LIKE 'DPA%%'
                ORDER BY tran_id DESC
                LIMIT 1
            """)

            row = cursor.fetchone()

        last_number = int(row[0][3:]) if row else 0
        tran_id = "DPA" + str(last_number + 1).zfill(9)
        invoice_ref = tran_id

        # =========================
        # INSERT MAIN TABLE
        # tran_by tran_user er pore save hobe
        # =========================
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO transaction__mains
                (
                    tran_id, tran_type, tran_method, invoice_ref,
                    loc_id, tran_type_with, tran_user, tran_by, user_name,
                    store_id, tran_date, status,
                    bill_amount, discount, net_amount,
                    receive, payment, due,
                    doctor_id, patient_id, sr_id
                )
                VALUES
                (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
            """, [
                tran_id, tran_type, payment_method, invoice_ref,
                location_id, tran_type_with, user_id, tran_by, user_name,
                store_id, tran_date, status,
                bill_amount, discount, net_amount,
                receive, payment, due,
                doctor_custom_id, patient_id, sr_id
            ])

        insert_diagnosis_detail_rows(products, tran_id, tran_type, payment_method, invoice_ref, location_id, tran_type_with, user_id, tran_by, store_id, tran_date, status, discount, receive, payment, due, doctor_custom_id, patient_id, sr_id)

        set_payment_mode(tran_id, "payment")
        return JsonResponse({
            "success": True,
            "tran_id": tran_id,
            "invoice_ref": invoice_ref,
            "invoice": invoice_ref,
            "invoice_barcode_svg": build_invoice_barcode_svg(invoice_ref),
            "patient_barcode_svg": build_invoice_barcode_svg(patient_id),
            "doctor_id": doctor_custom_id,
            "patient_id": patient_id,
            "sr_id": sr_id,
            
            "tran_by": tran_by
        })

    except Exception as e:
        print("🔥 DIAGNOSIS PAYMENT SAVE ERROR")
        traceback.print_exc()

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

def diagnosis_payment_list_load(request):
    q = request.GET.get("q", "").strip()

    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()

    status = request.GET.get("status", "").strip()

    # support both names
    transactionmainheads = (
        request.GET.get("transactionmainheads")
        or request.GET.get("tran_main_head")
        or ""
    ).strip()

    doctor_id = request.GET.get("doctor_id", "").strip()
    sr_id = request.GET.get("sr_id", "").strip()
    patient_id = request.GET.get("patient_id", "").strip()
    tran_by = request.GET.get("tran_by", "").strip()

    try:
        offset = int(request.GET.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0

    try:
        limit = int(request.GET.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50

    if limit <= 0:
        limit = 50

    if limit > 500:
        limit = 500

    sql = """
        SELECT
            m.id,
            m.tran_id AS tran_id,
            COALESCE(m.invoice_ref, '') AS invoice_ref,
            DATE_FORMAT(m.tran_date, '%%Y-%%m-%%d') AS tran_date,

            COALESCE(tw.tran_with_name, m.tran_type_with, '') AS supplier_name,
            m.tran_user AS tran_user,
            COALESCE(m.tran_by, '') AS tran_by,            COALESCE(m.user_name, m.tran_user, '') AS user_name,
            COALESCE(d.name, m.doctor_id, '') AS doctor_name,            COALESCE(sr.name, m.sr_id, '') AS sr_name,            COALESCE(p.patient_name, m.patient_id, '') AS patient_name,
            COALESCE(m.bill_amount, 0) AS bill_total,
            COALESCE(m.discount, 0) AS discount,
            COALESCE(m.net_amount, 0) AS net_total,
            COALESCE(m.payment, 0) AS advance,
            COALESCE(m.due_col, 0) AS due_collection,
            COALESCE(m.due_disc, 0) AS due_discount,
            COALESCE(m.due, 0) AS due,
            m.status AS status

        FROM transaction__mains m
        LEFT JOIN transaction__withs tw ON tw.id = m.tran_type_with
        LEFT JOIN doctors_info d ON d.custom_doc_id COLLATE utf8mb4_unicode_ci = m.doctor_id COLLATE utf8mb4_unicode_ci        LEFT JOIN item__sr_agents sr ON sr.custom_sr_id COLLATE utf8mb4_unicode_ci = m.sr_id COLLATE utf8mb4_unicode_ci        LEFT JOIN patient_info p ON p.user_info_id COLLATE utf8mb4_unicode_ci = m.patient_id COLLATE utf8mb4_unicode_ci        WHERE 1=1
    """

    total_sql = """
        SELECT COALESCE(SUM(m.due), 0)
        FROM transaction__mains m
        LEFT JOIN transaction__withs tw ON tw.id = m.tran_type_with
        LEFT JOIN doctors_info d ON d.custom_doc_id COLLATE utf8mb4_unicode_ci = m.doctor_id COLLATE utf8mb4_unicode_ci        LEFT JOIN item__sr_agents sr ON sr.custom_sr_id COLLATE utf8mb4_unicode_ci = m.sr_id COLLATE utf8mb4_unicode_ci        LEFT JOIN patient_info p ON p.user_info_id COLLATE utf8mb4_unicode_ci = m.patient_id COLLATE utf8mb4_unicode_ci        WHERE 1=1
    """

    params = []
    total_params = []

    # Diagnosis only
    sql += " AND m.tran_type = %s"
    params.append(10)

    total_sql += " AND m.tran_type = %s"
    total_params.append(10)

    # Search
    if q:
        sql += """
            AND (
                m.tran_id LIKE %s
                OR m.invoice_ref LIKE %s
                OR m.tran_user LIKE %s
                OR m.tran_by LIKE %s                OR m.user_name LIKE %s
                OR d.name LIKE %s                OR sr.name LIKE %s                OR p.patient_name LIKE %s            )
        """

        params.extend([
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%"
        ])

        total_sql += """
            AND (
                m.tran_id LIKE %s
                OR m.invoice_ref LIKE %s
                OR m.tran_user LIKE %s
                OR m.tran_by LIKE %s                OR m.user_name LIKE %s
                OR d.name LIKE %s                OR sr.name LIKE %s                OR p.patient_name LIKE %s            )
        """

        total_params.extend([
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%",
            f"%{q}%"
        ])

    # Status
    if status:
        sql += " AND m.status = %s"
        params.append(status)

        total_sql += " AND m.status = %s"
        total_params.append(status)

    # Main head
    # note: diagnosis already fixed as tran_type=10
    # tai same value 10 hole ok, different hole no data
    if transactionmainheads:
        sql += " AND m.tran_type = %s"
        params.append(transactionmainheads)

        total_sql += " AND m.tran_type = %s"
        total_params.append(transactionmainheads)

    # Doctor
    if doctor_id:
        sql += " AND m.doctor_id = %s"
        params.append(doctor_id)

        total_sql += " AND m.doctor_id = %s"
        total_params.append(doctor_id)

    # SR
    if sr_id:
        sql += " AND m.sr_id = %s"
        params.append(sr_id)

        total_sql += " AND m.sr_id = %s"
        total_params.append(sr_id)

    # Patient
    if patient_id:
        sql += " AND m.patient_id = %s"
        params.append(patient_id)

        total_sql += " AND m.patient_id = %s"
        total_params.append(patient_id)

    # Transaction By
    if tran_by:
        sql += " AND m.tran_by = %s"
        params.append(tran_by)

        total_sql += " AND m.tran_by = %s"
        total_params.append(tran_by)

    # Date
    if start_date:
        sql += " AND DATE(m.tran_date) >= %s"
        params.append(start_date)

        total_sql += " AND DATE(m.tran_date) >= %s"
        total_params.append(start_date)

    if end_date:
        sql += " AND DATE(m.tran_date) <= %s"
        params.append(end_date)

        total_sql += " AND DATE(m.tran_date) <= %s"
        total_params.append(end_date)

    sql += """
        ORDER BY m.id DESC
        LIMIT %s OFFSET %s
    """

    params.extend([limit, offset])

    print("DIAGNOSIS LIST SQL:", sql)
    print("DIAGNOSIS LIST PARAMS:", params)

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        data = dictfetchall(cursor)

        cursor.execute(total_sql, total_params)
        total_due = cursor.fetchone()[0] or 0

    return JsonResponse({
        "results": data,
        "total_due": float(total_due)
    })

# =========================
# PARTY PAYMENTS
# =========================
def diagnosis_party_payment_list(request):
    return render(request, "diagnosis/party_payment/payment_list.html")

def diagnosis_party_payment_list_load(request):
    return diagnosis_payment_list_load(request)

def diagnosis_filter_doctor_combo(request):
    q = request.GET.get("q", "").strip()
    with connection.cursor() as cursor:
        cursor.execute("""            SELECT custom_doc_id AS id, CONCAT(custom_doc_id, ' - ', name) AS name  
            FROM doctors_info  
            WHERE (%s = '' OR name LIKE %s OR custom_doc_id LIKE %s)  
            ORDER BY name ASC  
            LIMIT 200  
        """, [q, f"%{q}%", f"%{q}%"])
        data = dictfetchall(cursor)
    return JsonResponse({"results": data})

def diagnosis_filter_sr_combo(request):
    q = request.GET.get("q", "").strip()
    with connection.cursor() as cursor:
        cursor.execute("""  
            SELECT custom_sr_id AS id, CONCAT(custom_sr_id, ' - ', name) AS name  
            FROM item__sr_agents  
            WHERE (%s = '' OR name LIKE %s OR custom_sr_id LIKE %s)  
            ORDER BY name ASC  
            LIMIT 200  
        """, [q, f"%{q}%", f"%{q}%"])
        data = dictfetchall(cursor)
    return JsonResponse({"results": data})

def diagnosis_filter_patient_combo(request):
    q = request.GET.get("q", "").strip()
    with connection.cursor() as cursor:
        cursor.execute("""  
            SELECT user_info_id AS id, CONCAT(user_info_id, ' - ', patient_name) AS name  
            FROM patient_info  
            WHERE user_info_id IS NOT NULL  
              AND (%s = '' OR patient_name LIKE %s OR user_info_id LIKE %s)  
            ORDER BY id DESC  
            LIMIT 200  
        """, [q, f"%{q}%", f"%{q}%"])
        data = dictfetchall(cursor)
    return JsonResponse({"results": data})

def diagnosis_filter_tran_by_combo(request):
    q = request.GET.get("q", "").strip()
    with connection.cursor() as cursor:
        cursor.execute(""" 
            SELECT DISTINCT tran_by AS id, tran_by AS name  
            FROM transaction__mains 
            WHERE tran_type = 10 
              AND tran_by IS NOT NULL  
              AND tran_by <> '' 
              AND (%s = '' OR tran_by LIKE %s)  
            ORDER BY tran_by ASC 
            LIMIT 200  
        """, [q, f"%{q}%"])
        data = dictfetchall(cursor)
    return JsonResponse({"results": data})

def diagnosis_salesman_transaction_summary_page(request):
    return render(request, "diagnosis/reports/salesman/transaction_summary.html")

def diagnosis_salesman_transaction_details_page(request):
    return render(request, "diagnosis/reports/salesman/transaction_details.html")

def diagnosis_salesman_transaction_details_load(request):
    q = request.GET.get("q", "").strip()
    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()
    status = request.GET.get("status", "").strip()
    transactionmainheads = (
        request.GET.get("transactionmainheads")
        or request.GET.get("tran_main_head")
        or ""
    ).strip()
    doctor_id = request.GET.get("doctor_id", "").strip()
    sr_id = request.GET.get("sr_id", "").strip()
    patient_id = request.GET.get("patient_id", "").strip()
    tran_by = request.GET.get("tran_by", "").strip()

    try:
        offset = int(request.GET.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0

    try:
        limit = int(request.GET.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50

    if limit <= 0:
        limit = 50

    if limit > 500:
        limit = 500

    sql = """
        SELECT
            d.id,
            d.tran_id,
            COALESCE(d.invoice_ref, '') AS invoice_ref,
            DATE_FORMAT(d.tran_date, '%%Y-%%m-%%d') AS tran_date,
            d.tran_type,
            d.tran_method,
            d.loc_id,
            COALESCE(tw.tran_with_name, d.tran_type_with, '') AS tran_type_with,
            d.tran_bank,
            d.tran_user,
            COALESCE(d.tran_by, '') AS tran_by,
            d.ptn_id,
            d.user_name,
            d.user_phone,
            d.user_address,
            d.tran_groupe_id,
            d.tran_head_id,
            COALESCE(h.tran_head_name, '') AS tran_head_name,
            d.quantity_actual,
            d.quantity,
            d.quantity_issue,
            d.quantity_return,
            d.unit_id,
            d.amount,
            d.tot_amount,
            d.discount,
            d.cp,
            d.mrp,
            d.receive,
            d.payment,
            d.due,
            d.due_col,
            d.due_disc,
            d.expiry_date,
            d.store_id,
            d.payment_mode,
            d.batch_id,
            d.booking_id,
            d.status,
            d.doctor_id,
            COALESCE(doc.name, d.doctor_id, '') AS doctor_name,
            d.patient_id,
            COALESCE(p.patient_name, d.patient_id, '') AS patient_name,
            d.sr_id,
            COALESCE(sr.name, d.sr_id, '') AS sr_name
        FROM transaction__details d
        LEFT JOIN transaction__heads h ON h.id = d.tran_head_id
        LEFT JOIN transaction__withs tw ON tw.id = d.tran_type_with
        LEFT JOIN doctors_info doc ON doc.custom_doc_id COLLATE utf8mb4_unicode_ci = d.doctor_id COLLATE utf8mb4_unicode_ci
        LEFT JOIN patient_info p ON p.user_info_id COLLATE utf8mb4_unicode_ci = d.patient_id COLLATE utf8mb4_unicode_ci
        LEFT JOIN item__sr_agents sr ON sr.custom_sr_id COLLATE utf8mb4_unicode_ci = d.sr_id COLLATE utf8mb4_unicode_ci
        WHERE d.tran_type = %s
    """

    params = [10]

    if q:
        sql += " AND h.tran_head_name LIKE %s"
        params.append(f"%{q}%")

    if status:
        sql += " AND d.status = %s"
        params.append(status)

    if transactionmainheads:
        sql += " AND d.tran_type = %s"
        params.append(transactionmainheads)

    if doctor_id:
        sql += " AND d.doctor_id = %s"
        params.append(doctor_id)

    if sr_id:
        sql += " AND d.sr_id = %s"
        params.append(sr_id)

    if patient_id:
        sql += " AND d.patient_id = %s"
        params.append(patient_id)

    if tran_by:
        sql += " AND d.tran_by = %s"
        params.append(tran_by)

    if start_date:
        sql += " AND DATE(d.tran_date) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(d.tran_date) <= %s"
        params.append(end_date)

    sql += """
        ORDER BY d.id DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        data = dictfetchall(cursor)

    return JsonResponse({
        "results": data
    })


def diagnosis_salesman_transaction_summary_report_pdf(request):
    """Use the same diagnosis report query for the salesman summary screen."""
    return diagnosis_payment_report_pdf(request)


def diagnosis_salesman_transaction_details_report_pdf(request):
    """Build a details PDF using the same filters as the details list."""
    q = (request.GET.get("q") or request.GET.get("search") or "").strip()
    start_date = (request.GET.get("start_date") or "").strip()
    end_date = (request.GET.get("end_date") or "").strip()
    status = (request.GET.get("status") or "").strip()
    main_head = (request.GET.get("transactionmainheads") or request.GET.get("tran_main_head") or "10").strip()
    doctor_id = (request.GET.get("doctor_id") or "").strip()
    sr_id = (request.GET.get("sr_id") or "").strip()
    patient_id = (request.GET.get("patient_id") or "").strip()
    tran_by = (request.GET.get("tran_by") or "").strip()

    sql = """
        SELECT d.tran_id, COALESCE(d.invoice_ref, '') AS invoice_ref,
               d.tran_date, d.tran_head_id,
               COALESCE(h.tran_head_name, '') AS tran_head_name,
               COALESCE(tw.tran_with_name, d.tran_type_with, '') AS tran_type_with,
               d.tran_user, COALESCE(d.tran_by, '') AS tran_by,
               d.tran_method, d.amount, d.tot_amount, d.discount, d.payment, d.receive,
               d.due_col, d.due_disc, d.due,
               COALESCE(doc.name, d.doctor_id, '') AS doctor_name,
               COALESCE(sr.name, d.sr_id, '') AS sr_name,
               COALESCE(p.patient_name, d.patient_id, '') AS patient_name
        FROM transaction__details d
        LEFT JOIN transaction__heads h ON h.id = d.tran_head_id
        LEFT JOIN transaction__withs tw ON tw.id = d.tran_type_with
        LEFT JOIN doctors_info doc ON doc.custom_doc_id COLLATE utf8mb4_unicode_ci = d.doctor_id COLLATE utf8mb4_unicode_ci
        LEFT JOIN patient_info p ON p.user_info_id COLLATE utf8mb4_unicode_ci = d.patient_id COLLATE utf8mb4_unicode_ci
        LEFT JOIN item__sr_agents sr ON sr.custom_sr_id COLLATE utf8mb4_unicode_ci = d.sr_id COLLATE utf8mb4_unicode_ci
        WHERE d.tran_type = %s
    """
    params = [10]
    if q:
        sql += """ AND (d.tran_id LIKE %s OR d.invoice_ref LIKE %s OR d.tran_user LIKE %s
            OR d.tran_by LIKE %s OR h.tran_head_name LIKE %s OR doc.name LIKE %s
            OR sr.name LIKE %s OR p.patient_name LIKE %s)"""
        params.extend([f"%{q}%"] * 8)
    if status:
        sql += " AND d.status = %s"
        params.append(status)
    if doctor_id:
        sql += " AND d.doctor_id = %s"
        params.append(doctor_id)
    if sr_id:
        sql += " AND d.sr_id = %s"
        params.append(sr_id)
    if patient_id:
        sql += " AND d.patient_id = %s"
        params.append(patient_id)
    if tran_by:
        sql += " AND d.tran_by = %s"
        params.append(tran_by)
    if start_date:
        sql += " AND DATE(d.tran_date) >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(d.tran_date) <= %s"
        params.append(end_date)
    opening_sql = sql
    opening_params = list(params)
    if start_date:
        opening_sql = opening_sql.replace(
            "AND DATE(d.tran_date) >= %s",
            "AND DATE(d.tran_date) < %s",
            1,
        )
        if end_date:
            opening_sql = opening_sql.replace(
                "AND DATE(d.tran_date) <= %s",
                "",
                1,
            )
            try:
                opening_params.remove(end_date)
            except ValueError:
                pass
    else:
        opening_sql += " AND 1 = 0"
    opening_sql = f"""
        SELECT COALESCE(SUM(
            CASE WHEN LOWER(COALESCE(report_rows.tran_method, '')) = 'receive'
                 THEN COALESCE(report_rows.receive, report_rows.payment, 0)
                 ELSE -COALESCE(report_rows.payment, report_rows.receive, 0)
            END
        ), 0)
        FROM ({opening_sql}) report_rows
    """

    sql += " ORDER BY d.id ASC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = dictfetchall(cursor)
        cursor.execute(opening_sql, opening_params)
        opening_balance = float(cursor.fetchone()[0] or 0)

    def filter_label(value, default="All"):
        return str(value) if value not in (None, "", "null") else default

    status_label = {"1": "Verified", "0": "Non Verified"}.get(status, filter_label(status))
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    table_cell_style = styles["Normal"].clone("DiagnosisDetailsReportCell")
    table_cell_style.fontName = "Helvetica"
    table_cell_style.fontSize = 6.4
    table_cell_style.leading = 8.2
    table_cell_style.alignment = 1
    table_cell_style.spaceBefore = 0
    table_cell_style.spaceAfter = 0

    table_header_style = table_cell_style.clone("DiagnosisDetailsReportHeader")
    table_header_style.fontName = "Helvetica-Bold"
    table_header_style.textColor = colors.white

    def report_cell(value, header=False):
        """Wrap long detail values so table borders stay outside the text."""
        text = escape(str(value if value is not None else ""))
        return Paragraph(text or "&nbsp;", table_header_style if header else table_cell_style)

    elements = [Paragraph("Diagnosis Transaction Details Report", styles["Title"]), Spacer(1, 10)]
    filter_table = Table([
        ["Start Date", filter_label(start_date, "-"), "End Date", filter_label(end_date, "-"), "Status", status_label],
        ["Main Head", "Diagnosis" if main_head == "10" else filter_label(main_head), "Doctor", filter_label(doctor_id), "SR", filter_label(sr_id)],
        ["Patient", filter_label(patient_id), "Transaction By", filter_label(tran_by), "Search", filter_label(q, "-")],
        ["Opening Balance", f"{opening_balance:.2f}", "", "", "", ""],
    ], colWidths=[65, 95, 65, 95, 65, 148])
    filter_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c7cdd4")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f6")),
        ("BACKGROUND", (2, 0), (2, -2), colors.HexColor("#eef2f6")),
        ("BACKGROUND", (4, 0), (4, -2), colors.HexColor("#eef2f6")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -2), "Helvetica-Bold"),
        ("FONTNAME", (4, 0), (4, -2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(filter_table)
    elements.append(Spacer(1, 12))
    table_data = [[
        report_cell("SL", True), report_cell("Tran ID", True), report_cell("Invoice", True),
        report_cell("Date", True), report_cell("Product ID", True), report_cell("Product", True),
        report_cell("Tran With", True), report_cell("Doctor", True), report_cell("SR", True),
        report_cell("Patient", True), report_cell("Tran By", True), report_cell("Bill", True),
        report_cell("Discount", True), report_cell("Net", True), report_cell("Advance", True),
        report_cell("Due Col", True), report_cell("Due Disc", True), report_cell("Due", True)
    ]]
    for index, row in enumerate(rows, 1):
        table_data.append([
            report_cell(index), report_cell(row["tran_id"] or ""), report_cell(row["invoice_ref"] or ""),
            report_cell(str(row["tran_date"] or "")), report_cell(row["tran_head_id"] or ""),
            report_cell(row["tran_head_name"] or ""), report_cell(row["tran_type_with"] or ""),
            report_cell(row["doctor_name"] or ""), report_cell(row["sr_name"] or ""),
            report_cell(row["patient_name"] or ""), report_cell(row["tran_by"] or ""),
            report_cell(f'{float(row["tot_amount"] or 0):.2f}'), report_cell(f'{float(row["discount"] or 0):.2f}'),
            report_cell(f'{float(row["amount"] or 0):.2f}'),
            report_cell(f'{float(row["payment"] or row["receive"] or 0):.2f}'),
            report_cell(f'{float(row["due_col"] or 0):.2f}'), report_cell(f'{float(row["due_disc"] or 0):.2f}'),
            report_cell(f'{float(row["due"] or 0):.2f}')
        ])
    if not rows:
        table_data.append([report_cell(""), report_cell("No diagnosis transaction details found")] + [report_cell("")] * 16)
    table = Table(table_data, repeatRows=1, colWidths=[14, 36, 36, 34, 25, 36, 34, 31, 27, 31, 31, 26, 26, 26, 28, 27, 27, 26])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 5.2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)
    def balance_movement(row):
        amount = float(row.get("receive") or row.get("payment") or 0)
        return amount if str(row.get("tran_method") or "").lower() == "receive" else -amount

    closing_balance = opening_balance + sum(balance_movement(row) for row in rows)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Closing Balance:</b> {closing_balance:.2f}", styles["Normal"]))
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="diagnosis_transaction_details_report.pdf"'
    return response

def diagnosis_payment_form(request, id):

    sql = """
        SELECT
            m.id,            m.tran_id,            m.invoice_ref,            m.tran_date,            m.tran_type_with,            m.tran_user,            m.user_name,            m.bill_amount,            m.discount,            m.net_amount,            m.payment,            m.receive,            m.due_col,            m.due_disc,            m.due,            m.patient_id,            p.patient_name,            CONCAT(COALESCE(p.age_y, 0), 'Y ', COALESCE(p.age_m, 0), 'M ', COALESCE(p.age_d, 0), 'D') AS patient_age,            p.gender AS patient_gender,            p.blood_group AS patient_blood_group,            p.present_mobile AS patient_mobile,            p.present_address AS patient_address        FROM transaction__mains m        LEFT JOIN patient_info p ON p.user_info_id COLLATE utf8mb4_unicode_ci = m.patient_id COLLATE utf8mb4_unicode_ci        WHERE m.id = %s          AND m.tran_type = 10        LIMIT 1
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [id])
        row = dictfetchall(cursor)

    transaction_data = row[0] if row else None

    return render(
        request,
        "diagnosis/party_payment/payment_form.html",
        {
            "transaction": transaction_data
        }
    )

def diagnosis_party_payment_form(request, id):
    return diagnosis_payment_form(request, id)

@csrf_exempt
@transaction.atomic
def process_diagnosis_payment(request, id):

    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Invalid request method"
        }, status=405)

    try:
        pay_amount = float(request.POST.get("pay_amount", 0) or 0)
        due_discount = float(request.POST.get("due_discount", 0) or 0)

    except Exception:
        return JsonResponse({
            "success": False,
            "error": "Invalid amount"
        }, status=400)

    # ================= VALIDATION =================
    if pay_amount <= 0 and due_discount <= 0:
        return JsonResponse({
            "success": False,
            "error": "Payment or discount must be greater than 0"
        }, status=400)

    with connection.cursor() as cursor:

        # ================= FETCH MAIN =================
        cursor.execute("""
            SELECT 
                id,
                tran_id,
                invoice_ref,
                tran_type,
                tran_method,
                tran_user,
                user_name,
                tran_type_with,
                store_id,
                loc_id,
                tran_date,
                status,
                bill_amount,
                discount,
                net_amount,
                payment,
                receive,
                due,
                due_col,
                due_disc,
                doctor_id,
                patient_id,
                sr_id
            FROM transaction__mains
            WHERE id = %s
              AND tran_type = 10
            LIMIT 1
        """, [id])

        row = cursor.fetchone()

        if not row:
            return JsonResponse({
                "success": False,
                "error": "Diagnosis transaction not found"
            }, status=404)

        (
            main_id,
            old_tran_id,
            invoice_ref,
            tran_type,
            tran_method,
            tran_user,
            user_name,
            tran_type_with,
            store_id,
            loc_id,
            tran_date,
            status,
            bill_amount,
            discount,
            net_amount,
            old_payment,
            old_receive,
            current_due,
            old_due_col,
            old_due_disc,
            doctor_id,
            patient_id,
            sr_id
        ) = row

        current_due = float(current_due or 0)
        old_due_col = float(old_due_col or 0)
        old_due_disc = float(old_due_disc or 0)

        # ================= VALIDATION =================
        if current_due <= 0:
            return JsonResponse({
                "success": False,
                "error": "No due amount found"
            }, status=400)

        if (pay_amount + due_discount) > current_due:
            return JsonResponse({
                "success": False,
                "error": "Payment + Discount exceeds due"
            }, status=400)

        # ================= CALCULATION =================
        new_due = current_due - pay_amount - due_discount
        new_due_col = old_due_col + pay_amount
        new_due_disc = old_due_disc + due_discount

        # ================= NEW TRAN ID =================
        cursor.execute("""
            SELECT tran_id
            FROM transaction__party__payments
            WHERE tran_id LIKE 'DPA%'
            ORDER BY id DESC
            LIMIT 1
        """)

        last = cursor.fetchone()

        last_no = int(last[0].replace("DPA", "")) if last and last[0] else 0

        new_tran_id = "DPA" + str(last_no + 1).zfill(9)

        # ================= UPDATE MAIN =================
        cursor.execute("""
            UPDATE transaction__mains
            SET
                due = %s,
                due_col = %s,
                due_disc = %s
            WHERE id = %s
              AND tran_type = 10
        """, [
            new_due,
            new_due_col,
            new_due_disc,
            id
        ])

                # ================= UPDATE DETAILS =================
        cursor.execute("""
            SELECT id, COALESCE(tot_amount, amount, 0)
            FROM transaction__details
            WHERE tran_id = %s
            ORDER BY id
        """, [old_tran_id])
        detail_rows = cursor.fetchall()
        detail_weights = [float(row[1] or 0) for row in detail_rows]
        detail_due = allocate_amount(new_due, detail_weights)
        detail_due_col = allocate_amount(new_due_col, detail_weights)
        detail_due_disc = allocate_amount(new_due_disc, detail_weights)
        for index, (detail_id, _) in enumerate(detail_rows):
            cursor.execute("""
                UPDATE transaction__details
                SET due = %s, due_col = %s, due_disc = %s
                WHERE id = %s
            """, [detail_due[index], detail_due_col[index], detail_due_disc[index], detail_id])

        # ================= INSERT PARTY PAYMENT HISTORY =================
        cursor.execute("""
            INSERT INTO transaction__party__payments
            (
                tran_id,
                invoice_ref,
                tran_type,
                tran_method,
                tran_user,
                user_name,
                tran_type_with,
                store_id,
                loc_id,
                tran_date,
                status,
                bill_amount,
                discount,
                net_amount,
                payment,
                due,
                due_col,
                due_disc
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s
            )
        """, [
            new_tran_id,
            old_tran_id,
            

            tran_type,
            tran_method,
            tran_user,
            user_name,
            tran_type_with,
            store_id,
            loc_id,
            tran_date,
            status,
            bill_amount,
            discount,
            net_amount,

            pay_amount,
            new_due,
            pay_amount,
            due_discount
        ])

        if new_due <= 0:
            cursor.execute("""
                UPDATE transaction__details
                SET due = 0
                WHERE tran_id = %s
                  AND tran_type = 10
            """, [old_tran_id])

    return JsonResponse({
        "success": True,
        "paid": pay_amount,
        "due_discount": due_discount,
        "new_due": new_due,
        "new_due_col": new_due_col,
        "new_due_disc": new_due_disc,
        "redirect_url": "/diagnosis/party-payment/"
    })

@csrf_exempt
def process_diagnosis_party_payment(request, id):
    return process_diagnosis_payment(request, id)

@csrf_exempt
@transaction.atomic
def process_diagnosis_party_fifo_payment(request):
    payment_amount = float(request.POST.get("payment", 0) or 0)
    ids = json.loads(request.POST.get("ids", "[]"))

    if payment_amount <= 0 or not ids:
        return JsonResponse({"success": False, "error": "Invalid payment request"})

    remaining = payment_amount

    with connection.cursor() as cursor:
        placeholders = ",".join(["%s"] * len(ids))

        cursor.execute(f"""            SELECT id, invoice_ref, bill_amount, payment, due
            FROM transaction__mains
            WHERE id IN ({placeholders})
              AND tran_type = 10
            ORDER BY tran_date ASC, id ASC
        """, ids)

        rows = cursor.fetchall()

        for row in rows:
            row_id, invoice_ref, bill_amount, old_payment, due = row
            bill_amount = float(bill_amount or 0)
            old_payment = float(old_payment or 0)
            due = float(due or 0)

            if remaining <= 0:
                break

            if due <= 0:
                continue

            pay = min(remaining, due)
            new_payment = old_payment + pay
            new_due = bill_amount - new_payment

            cursor.execute("""                UPDATE transaction__mains
                SET payment = %s,
                    due = %s
                WHERE id = %s
                  AND tran_type = 10
            """, [new_payment, new_due, row_id])

            cursor.execute("""                UPDATE transaction__details
                SET payment = payment + %s,
                    due = due - %s
                WHERE invoice_ref = %s
                  AND tran_type = 10
            """, [pay, pay, invoice_ref])

            if new_due <= 0:
                cursor.execute("""                    UPDATE transaction__details
                    SET due = 0
                    WHERE invoice_ref = %s
                      AND tran_type = 10
                """, [invoice_ref])

            remaining -= pay

    return JsonResponse({
        "success": True,
        "paid": payment_amount - remaining,
    })

from io import BytesIO

from django.db import connection
from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from xml.sax.saxutils import escape


def dictfetchall(cursor):
    columns = [
        column[0]
        for column in cursor.description
    ]

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def diagnosis_payment_report_pdf(request):

    # =========================
    # REQUEST FILTERS
    # =========================
    q = (request.GET.get("q") or request.GET.get("search") or "").strip()

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    main_head = (
        request.GET.get("transactionmainheads")
        or request.GET.get("main_head")
        or "10"
    )

    doctor_id = (
        request.GET.get("doctor_id")
        or ""
    )

    sr_id = (
        request.GET.get("sr_id")
        or ""
    )

    patient_id = (
        request.GET.get("patient_id")
        or ""
    )

    tran_by = (
        request.GET.get("tran_by")
        or ""
    )

    status = (
        request.GET.get("status")
        or ""
    )

    # =========================
    # BASE SQL
    # =========================
    sql = """
        SELECT
            m.id,
            m.tran_id,
            m.invoice_ref,
            m.tran_date,
            m.tran_type,
            m.tran_method,
            m.tran_type_with,

            mh.type_name AS main_head_name,
            tw.tran_with_name AS tran_with_name,

            m.tran_user,
            m.user_name,
            m.tran_by,

            m.bill_amount,
            m.discount,
            m.net_amount,
            m.payment,
            m.receive,
            m.due_col,
            m.due_disc,
            m.due,

            m.doctor_id,
            m.patient_id,
            m.sr_id,

            d.name AS doctor_name,

            patient_user.user_name AS patient_name,

            sr.name AS sr_name

        FROM transaction__mains m

        LEFT JOIN transaction__main__heads mh
            ON mh.id = m.tran_type

        LEFT JOIN transaction__withs tw
            ON tw.id = m.tran_type_with

        LEFT JOIN doctors_info d
            ON d.custom_doc_id = m.doctor_id

        LEFT JOIN user__infos patient_user
            ON patient_user.user_id = m.patient_id

        LEFT JOIN item__sr_agents sr
            ON sr.custom_sr_id = m.sr_id

        WHERE 1 = 1
    """

    params = []

    # Match the list endpoint by transaction type. Do not use the old
    # GPA/DPA prefix here because the list is not filtered by that prefix.
    sql += " AND m.tran_type = %s"
    params.append(10)

    # =========================
    # SEARCH
    # =========================
    if q:
        search_value = f"%{q}%"

        sql += """
            AND (
                m.tran_id LIKE %s
                OR m.invoice_ref LIKE %s
                OR m.tran_user LIKE %s
                OR m.user_name LIKE %s
                OR m.tran_by LIKE %s
                OR m.doctor_id LIKE %s
                OR m.patient_id LIKE %s
                OR m.sr_id LIKE %s
                OR d.name LIKE %s
                OR patient_user.user_name LIKE %s
                OR sr.name LIKE %s
            )
        """

        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    # =========================
    # DATE FILTER
    # =========================
    if start_date:
        sql += """
            AND DATE(m.tran_date) >= %s
        """
        params.append(start_date)

    if end_date:
        sql += """
            AND DATE(m.tran_date) <= %s
        """
        params.append(end_date)

    # =========================
    # MAIN HEAD FILTER
    # =========================
    if main_head and main_head != "null":
        sql += """
            AND m.tran_type = %s
        """
        params.append(main_head)

    # =========================
    # DOCTOR FILTER
    # Frontend numeric id/custom id
    # দুটোই handle করবে
    # =========================
    doctor_text = "All"

    if doctor_id and doctor_id != "null":

        with connection.cursor() as cursor:

            if str(doctor_id).isdigit():
                cursor.execute("""
                    SELECT custom_doc_id, name
                    FROM doctors_info
                    WHERE id = %s
                    LIMIT 1
                """, [doctor_id])
            else:
                cursor.execute("""
                    SELECT custom_doc_id, name
                    FROM doctors_info
                    WHERE custom_doc_id = %s
                    LIMIT 1
                """, [doctor_id])

            doctor_row = cursor.fetchone()

        if doctor_row:
            doctor_custom_id = doctor_row[0]
            doctor_text = doctor_row[1] or doctor_row[0]

            sql += """
                AND m.doctor_id = %s
            """
            params.append(doctor_custom_id)

    # =========================
    # SR FILTER
    # =========================
    sr_text = "All"

    if sr_id and sr_id != "null":

        with connection.cursor() as cursor:

            if str(sr_id).isdigit():
                cursor.execute("""
                    SELECT custom_sr_id, name
                    FROM item__sr_agents
                    WHERE id = %s
                    LIMIT 1
                """, [sr_id])
            else:
                cursor.execute("""
                    SELECT custom_sr_id, name
                    FROM item__sr_agents
                    WHERE custom_sr_id = %s
                    LIMIT 1
                """, [sr_id])

            sr_row = cursor.fetchone()

        if sr_row:
            sr_custom_id = sr_row[0]
            sr_text = sr_row[1] or sr_row[0]

            sql += """
                AND m.sr_id = %s
            """
            params.append(sr_custom_id)

    # =========================
    # PATIENT FILTER
    # =========================
    patient_text = "All"

    if patient_id and patient_id != "null":

        with connection.cursor() as cursor:

            if str(patient_id).isdigit():
                cursor.execute("""
                    SELECT user_id, user_name
                    FROM user__infos
                    WHERE id = %s
                    LIMIT 1
                """, [patient_id])
            else:
                cursor.execute("""
                    SELECT user_id, user_name
                    FROM user__infos
                    WHERE user_id = %s
                    LIMIT 1
                """, [patient_id])

            patient_row = cursor.fetchone()

        if patient_row:
            patient_custom_id = patient_row[0]
            patient_text = patient_row[1] or patient_row[0]

            sql += """
                AND m.patient_id = %s
            """
            params.append(patient_custom_id)

    # =========================
    # TRANSACTION BY FILTER
    # =========================
    tran_by_text = "All"

    if tran_by and tran_by != "null":
        tran_by_text = tran_by

        sql += """
            AND m.tran_by = %s
        """
        params.append(tran_by)

    # =========================
    # STATUS FILTER
    # =========================
    status_text = "All"

    if status not in ["", None, "null"]:
        sql += """
            AND m.status = %s
        """
        params.append(status)

        if str(status) == "1":
            status_text = "Verified"
        elif str(status) == "0":
            status_text = "Non Verified"
        else:
            status_text = str(status)

    # Keep a copy of the filtered query before ordering so the opening
    # balance uses exactly the same non-date filters as the report rows.
    opening_sql = sql
    opening_params = list(params)

    if start_date:
        opening_sql = opening_sql.replace(
            "AND DATE(m.tran_date) >= %s",
            "AND DATE(m.tran_date) < %s",
            1,
        )
        if end_date:
            opening_sql = opening_sql.replace(
                "AND DATE(m.tran_date) <= %s",
                "",
                1,
            )
            try:
                opening_params.remove(end_date)
            except ValueError:
                pass
    else:
        opening_sql += " AND 1 = 0"

    opening_sql = f"""
        SELECT COALESCE(SUM(
            CASE WHEN LOWER(COALESCE(report_rows.tran_method, '')) = 'receive'
                 THEN COALESCE(report_rows.receive, report_rows.payment, 0)
                 ELSE -COALESCE(report_rows.payment, report_rows.receive, 0)
            END
        ), 0)
        FROM ({opening_sql}) report_rows
    """

    # =========================
    # ORDER
    # =========================
    sql += """
        ORDER BY m.id ASC
    """

    # =========================
    # EXECUTE QUERY
    # =========================
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        data = dictfetchall(cursor)
        cursor.execute(opening_sql, opening_params)
        opening_balance = float(cursor.fetchone()[0] or 0)

    def balance_movement(row):
        amount = float(row.get("receive") or row.get("payment") or 0)
        return amount if str(row.get("tran_method") or "").lower() == "receive" else -amount

    closing_balance = opening_balance + sum(balance_movement(row) for row in data)

    # =========================
    # MAIN HEAD TEXT
    # =========================
    main_head_text = "All"

    if main_head and main_head != "null":

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT type_name
                FROM transaction__main__heads
                WHERE id = %s
                LIMIT 1
            """, [main_head])

            main_head_row = cursor.fetchone()

        if main_head_row:
            main_head_text = main_head_row[0]

    # =========================
    # PDF SETUP
    # Landscape used because
    # many columns are present
    # =========================
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20,
        rightMargin=20,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    normal_style = styles["Normal"]
    table_cell_style = styles["Normal"].clone("DiagnosisReportCell")
    table_cell_style.fontName = "Helvetica"
    table_cell_style.fontSize = 5.2
    table_cell_style.leading = 7
    table_cell_style.alignment = 1
    table_cell_style.spaceBefore = 0
    table_cell_style.spaceAfter = 0

    table_header_style = table_cell_style.clone("DiagnosisReportHeader")
    table_header_style.fontName = "Helvetica-Bold"
    table_header_style.textColor = colors.white

    def report_cell(value, header=False):
        """Wrap report text so long names expand the row instead of crossing its border."""
        text = escape(str(value if value is not None else ""))
        return Paragraph(text or "&nbsp;", table_header_style if header else table_cell_style)

    elements = []

    # =========================
    # TITLE
    # =========================
    report_title = "Diagnosis Party Payment Report" if "party-payment" in request.path else "Diagnosis Payment Report"
    elements.append(
        Paragraph(
            report_title,
            title_style
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    # =========================
    # HEADER INFORMATION
    # =========================
    filter_table = Table([
        ["Start Date", start_date or "-", "End Date", end_date or "-", "Status", status_text],
        ["Main Head", main_head_text, "Doctor", doctor_text, "SR", sr_text],
        ["Patient", patient_text, "Transaction By", tran_by_text, "Search", q or "-"],
        ["Opening Balance", f"{opening_balance:.2f}", "", "", "", ""],
    ], colWidths=[65, 95, 65, 95, 65, 148])
    filter_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c7cdd4")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f6")),
        ("BACKGROUND", (2, 0), (2, -2), colors.HexColor("#eef2f6")),
        ("BACKGROUND", (4, 0), (4, -2), colors.HexColor("#eef2f6")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -2), "Helvetica-Bold"),
        ("FONTNAME", (4, 0), (4, -2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(filter_table)

    elements.append(
        Spacer(1, 15)
    )

    # =========================
    # TABLE HEADER
    # =========================
    table_data = [[
        report_cell("SL", True),
        report_cell("Tran ID", True),
        report_cell("Invoice", True),
        report_cell("Date", True),
        report_cell("Tran With", True),
        report_cell("Doctor", True),
        report_cell("SR", True),
        report_cell("Patient", True),
        report_cell("Tran By", True),
        report_cell("Bill", True),
        report_cell("Discount", True),
        report_cell("Net", True),
        report_cell("Advance", True),
        report_cell("Due Col", True),
        report_cell("Due Disc", True),
        report_cell("Due", True)
    ]]

    # =========================
    # TABLE ROWS
    # =========================
    for index, row in enumerate(data, 1):

        tran_date_text = ""

        if row["tran_date"]:
            try:
                tran_date_text = (
                    row["tran_date"]
                    .strftime("%Y-%m-%d")
                )
            except Exception:
                tran_date_text = str(
                    row["tran_date"]
                )

        table_data.append([
            report_cell(index),
            report_cell(row["tran_id"] or ""),
            report_cell(row["invoice_ref"] or ""),
            report_cell(tran_date_text),
            report_cell(row["tran_with_name"] or ""),
            report_cell(row["doctor_name"] or row["doctor_id"] or ""),
            report_cell(row["sr_name"] or row["sr_id"] or ""),
            report_cell(row["patient_name"] or row["patient_id"] or ""),
            report_cell(row["tran_by"] or ""),
            report_cell(f'{float(row["bill_amount"] or 0):.2f}'),
            report_cell(f'{float(row["discount"] or 0):.2f}'),
            report_cell(f'{float(row["net_amount"] or 0):.2f}'),
            report_cell(f'{float(row["payment"] or 0):.2f}'),
            report_cell(f'{float(row["due_col"] or 0):.2f}'),
            report_cell(f'{float(row["due_disc"] or 0):.2f}'),
            report_cell(f'{float(row["due"] or 0):.2f}')
        ])

    # =========================
    # EMPTY RESULT
    # =========================
    if not data:
        table_data.append([
            report_cell(""), report_cell("No diagnosis payment data found"),
            report_cell(""), report_cell(""), report_cell(""), report_cell(""),
            report_cell(""), report_cell(""), report_cell(""), report_cell(""),
            report_cell(""), report_cell(""), report_cell(""), report_cell(""),
            report_cell(""), report_cell("")
        ])

    # =========================
    # TABLE
    # =========================
    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[16, 43, 43, 37, 40, 36, 30, 39, 37, 28, 31, 28, 33, 32, 32, 28]
    )

    table.setStyle(
        TableStyle([
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.black
            ),

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.grey
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                6.4
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                2
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                2
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "ALIGN",
                (9, 1),
                (-1, -1),
                "RIGHT"
            )
        ])
    )

    elements.append(table)

    elements.append(
        Spacer(1, 12)
    )

    elements.append(
        Paragraph(
            f"<b>Closing Balance:</b> {closing_balance:.2f}",
            normal_style
        )
    )

    # =========================
    # BUILD PDF
    # =========================
    doc.build(elements)

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        'inline; '
        f'filename="{report_title.lower().replace(" ", "_")}.pdf"'
    )

    return response

def diagnosis_party_payment_report_pdf(request):
    return diagnosis_payment_report_pdf(request)

def diagnosis_invoice_print(request, tran_id):

    cursor = connection.cursor()

    # ===========================
    # MAIN INFO
    # ===========================
    cursor.execute("""
        SELECT
            tran_id,
            invoice_ref,
            DATE_FORMAT(tran_date,'%%d-%%m-%%Y'),
            user_name,
            tran_type_with,
            bill_amount,
            discount,
            net_amount,
            payment,
            due_col,
            due_disc,
            due,
            doctor_id,
            patient_id
        FROM transaction__mains
        WHERE tran_id=%s
        LIMIT 1
    """, [tran_id])

    row = cursor.fetchone()

    if not row:
        return render(request, "404.html")

    invoice = {
        "tran_id": row[0],
        "invoice_ref": row[1],
        "tran_date": row[2],
        "patient_name": row[3],
        "tran_type_with": row[4],
        "bill_amount": row[5],
        "discount": row[6],
        "net_amount": row[7],
        "payment": row[8],
        "due_col": row[9],
        "due_disc": row[10],
        "due": row[11],
        "doctor_id": row[12],
        "patient_id": row[13],
    }

    # ===========================
    # DETAILS
    # ===========================
    cursor.execute("""
        SELECT
            tran_head,
            quantity,
            amount,
            tot_amount
        FROM transaction__details
        WHERE tran_id=%s
        ORDER BY id
    """, [tran_id])

    columns = [col[0] for col in cursor.description]

    details = [
        dict(zip(columns, r))
        for r in cursor.fetchall()
    ]

    return render(
        request,
        "diagnosis/payment/print_invoice.html",
        {
            "invoice": invoice,
            "details": details
        }
    )

def diagnosis_party_payment_preview(request, transaction_id):
    try:
        with connection.cursor() as cursor:

            # =========================
            # MAIN + PATIENT + DOCTOR + SR
            # =========================
            cursor.execute("""
                SELECT
                    tm.id,
                    tm.tran_id,
                    tm.invoice_ref,
                    tm.tran_date,
                    tm.patient_id,

                    pi.patient_name,
                    pi.age_y,
                    pi.age_m,
                    pi.age_d,
                    pi.gender,
                    pi.present_mobile,
                    pi.present_address,

                    d.name AS doctor_name,
                    COALESCE(d.specialization, '') AS doctor_speciality,
                    COALESCE(d.chamber, '') AS doctor_chamber,
                    sr.name AS sr_name,

                    tm.bill_amount,
                    tm.discount,
                    tm.net_amount,
                    tm.payment,
                    tm.due_col,
                    tm.due_disc,
                    tm.due

                FROM transaction__mains tm

                LEFT JOIN patient_info pi
                    ON pi.user_info_id COLLATE utf8mb4_general_ci
                    = tm.patient_id COLLATE utf8mb4_general_ci

                LEFT JOIN doctors_info d
                    ON d.custom_doc_id COLLATE utf8mb4_general_ci
                    = tm.doctor_id COLLATE utf8mb4_general_ci

                LEFT JOIN item__sr_agents sr
                    ON sr.custom_sr_id COLLATE utf8mb4_general_ci
                    = tm.sr_id COLLATE utf8mb4_general_ci

                WHERE tm.id = %s
                LIMIT 1
            """, [transaction_id])

            row = cursor.fetchone()

            if not row:
                return JsonResponse({
                    "success": False,
                    "error": "Transaction not found"
                }, status=404)

            transaction = {
                "id": row[0],
                "tran_id": row[1],
                "invoice_ref": row[2],
                "tran_date": str(row[3]) if row[3] else "",

                "patient_id": row[4],
                "patient_name": row[5] or "",
                "patient_age": f"{row[6] or 0}Y - {row[7] or 0}M - {row[8] or 0}D",
                "patient_gender": row[9] or "",
                "patient_phone": row[10] or "",
                "patient_address": row[11] or "",

                "doctor_name": row[12] or "",
                "doctor_speciality": row[13] or "",
                "doctor_chamber": row[14] or "",
                "sr_name": row[15] or "",

                "bill_amount": row[16] or 0,
                "discount": row[17] or 0,
                "net_amount": row[18] or 0,
                "payment": row[19] or 0,
                "due_col": row[20] or 0,
                "due_disc": row[21] or 0,
                "due": row[22] or 0,
            }

            # =========================
            # TRANSACTION DETAILS + PRODUCT NAME
            # =========================
            cursor.execute("""
                SELECT
                    td.tran_head_id,
                    th.tran_head_name,
                    td.quantity,
                    td.mrp,
                    td.tot_amount

                FROM transaction__details td

                LEFT JOIN transaction__heads th
                    ON th.id = td.tran_head_id

                WHERE td.tran_id = %s

                ORDER BY td.id ASC
            """, [transaction["tran_id"]])

            detail_rows = cursor.fetchall()

            details = []

            for item in detail_rows:
                details.append({
                    "product_id": item[0],
                    "product_name": item[1] or "",
                    "quantity": item[2] or 0,
                    "mrp": item[3] or 0,
                    "total": item[4] or 0,
                })

        return JsonResponse({
            "success": True,
            "transaction": transaction,
            "details": details,
            "invoice_barcode_svg": build_invoice_barcode_svg(transaction.get("invoice_ref") or transaction.get("tran_id")),
            "patient_barcode_svg": build_invoice_barcode_svg(transaction.get("patient_id")),
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

# refferal
