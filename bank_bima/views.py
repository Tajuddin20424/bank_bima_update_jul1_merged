from datetime import datetime
import json
from zoneinfo import ZoneInfo

from django.contrib.sessions.models import Session
from django.db import connection, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from general_transaction.models import LocationInfos, TransactionWiths, UserInfos
from core.payment_mode import set_payment_mode
from core.amount_allocation import allocate_amount


LOCAL_TIMEZONE = ZoneInfo("Asia/Dhaka")


def get_local_tran_datetime(date_value=None):
    now = datetime.now(LOCAL_TIMEZONE).replace(tzinfo=None)
    if date_value:
        return datetime.combine(
            datetime.strptime(date_value, "%Y-%m-%d").date(),
            now.time()
        )
    return now


def get_recent_session_user():
    for session in Session.objects.filter(expire_date__gt=datetime.now(LOCAL_TIMEZONE)).order_by("-expire_date")[:20]:
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


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def advertisement_sales_add(request):
    fixed_location_id, fixed_location_name = get_login_location(request)
    return render(request, "bank_bima/advertisement_sales_payment.html", {
        "fixed_location_id": fixed_location_id or "",
        "fixed_location_name": fixed_location_name or "",
        "page_title": "Advertisement Sales",
        "page_id": request.GET.get("page_id") or "",
    })


def printing_sales_add(request):
    fixed_location_id, fixed_location_name = get_login_location(request)
    return render(request, "bank_bima/printing_sales_payment.html", {
        "fixed_location_id": fixed_location_id or "",
        "fixed_location_name": fixed_location_name or "",
        "page_title": "Printing Sale",
        "page_id": request.GET.get("page_id") or "",
    })


def office_bazar_add(request):
    fixed_location_id, fixed_location_name = get_login_location(request)
    return render(request, "bank_bima/office_bazar_payment.html", {
        "fixed_location_id": fixed_location_id or "",
        "fixed_location_name": fixed_location_name or "",
        "page_title": "Office Bazar",
        "page_id": request.GET.get("page_id") or "",
    })


def advertisement_sales_list(request):
    page_id = request.GET.get("page_id") or "1020300008"
    return render(request, "bank_bima/advertisement_sales_list.html", {
        "page_title": "Advertisement Sales",
        "list_title": "Advertisement Sales List",
        "page_id": page_id,
        "payment_list_url": "/bank-bima/advertisement-sales/load/",
        "payment_edit_url": "/bank-bima/advertisement-sales/edit/",
    })


def printing_sales_list(request):
    page_id = request.GET.get("page_id") or "1020300010"
    return render(request, "bank_bima/printing_sales_list.html", {
        "page_title": "Printing Sale",
        "list_title": "Printing Sale List",
        "page_id": page_id,
        "payment_list_url": "/bank-bima/printing-sales/load/",
        "payment_edit_url": "/bank-bima/printing-sales/edit/",
    })


def office_bazar_list(request):
    page_id = request.GET.get("page_id") or "1020300009"
    return render(request, "bank_bima/office_bazar_list.html", {
        "page_title": "Office Bazar",
        "list_title": "Office Bazar List",
        "page_id": page_id,
        "payment_list_url": "/bank-bima/office-bazar/load/",
        "payment_edit_url": "/bank-bima/office-bazar/edit/",
    })


def bank_bima_party_payment_list(request):
    return render(request, "bank_bima/party_payment_list.html")


def bank_bima_party_payment_list_load(request):
    q = (request.GET.get("q") or request.GET.get("search") or "").strip()
    start_date = (request.GET.get("start_date") or "").strip()
    end_date = (request.GET.get("end_date") or "").strip()
    status = (request.GET.get("status") or "").strip()
    main_head = (request.GET.get("transactionmainheads") or request.GET.get("tran_main_head") or "").strip()
    with_method = (request.GET.get("transaction_with_method") or request.GET.get("tran_with_method") or "").strip()
    with_group = (request.GET.get("transaction_with") or request.GET.get("tran_with") or "").strip()
    supplier = (request.GET.get("transaction_with_user") or request.GET.get("supplier") or "").strip()

    try:
        offset = max(int(request.GET.get("offset", 0)), 0)
    except (TypeError, ValueError):
        offset = 0
    try:
        limit = min(max(int(request.GET.get("limit", 50)), 1), 200)
    except (TypeError, ValueError):
        limit = 50

    base_sql = """
        FROM transaction__mains m
        LEFT JOIN transaction__withs tw ON tw.id = m.tran_type_with
        LEFT JOIN user__infos ui
            ON ui.user_id = m.tran_user OR CAST(ui.id AS CHAR) = m.tran_user
        WHERE m.tran_type = 1
          AND m.tran_id LIKE 'GPA%%'
    """
    filters = []
    params = []

    if q:
        filters.append("""
            AND (m.tran_id LIKE %s OR m.invoice_ref LIKE %s
                 OR m.tran_user LIKE %s OR m.user_name LIKE %s
                 OR tw.tran_with_name LIKE %s OR ui.user_name LIKE %s)
        """)
        params.extend([f"%{q}%"] * 6)
    if status in ("0", "1"):
        filters.append(" AND m.status = %s")
        params.append(status)
    if main_head:
        filters.append(" AND m.tran_type = %s")
        params.append(main_head)
    if with_method:
        filters.append("""
            AND m.tran_type_with IN (
                SELECT id FROM transaction__withs WHERE tran_method = %s
            )
        """)
        params.append(with_method)
    if with_group:
        filters.append(" AND m.tran_type_with = %s")
        params.append(with_group)
    if supplier:
        filters.append("""
            AND (m.tran_user = %s OR ui.user_id = %s OR CAST(ui.id AS CHAR) = %s)
        """)
        params.extend([supplier, supplier, supplier])
    if start_date:
        filters.append(" AND DATE(m.tran_date) >= %s")
        params.append(start_date)
    if end_date:
        filters.append(" AND DATE(m.tran_date) <= %s")
        params.append(end_date)

    select_sql = """
        SELECT m.id, m.tran_id, COALESCE(m.invoice_ref, '') AS invoice_ref,
               DATE_FORMAT(m.tran_date, '%%Y-%%m-%%d %%H:%%i:%%s') AS tran_date,
               COALESCE(tw.tran_with_name, m.tran_type_with, '') AS supplier_name,
               m.tran_user, COALESCE(m.user_name, ui.user_name, m.tran_user, '') AS user_name,
               COALESCE(m.bill_amount, 0) AS bill_total, COALESCE(m.discount, 0) AS discount,
               COALESCE(m.net_amount, 0) AS net_total, COALESCE(m.payment, 0) AS advance,
               COALESCE(m.due_col, 0) AS due_collection, COALESCE(m.due_disc, 0) AS due_discount,
               COALESCE(m.due, 0) AS due, m.status
    """ + base_sql + "".join(filters) + " ORDER BY m.tran_date ASC, m.id ASC LIMIT %s OFFSET %s"
    list_params = params + [limit, offset]
    total_sql = "SELECT COALESCE(SUM(m.due), 0) " + base_sql + "".join(filters)

    with connection.cursor() as cursor:
        cursor.execute(select_sql, list_params)
        rows = dictfetchall(cursor)
        cursor.execute(total_sql, params)
        total_due = cursor.fetchone()[0] or 0

    return JsonResponse({"results": rows, "total_due": float(total_due)})


def bank_bima_party_payment_form(request, id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, tran_id, invoice_ref, tran_date, tran_type_with, tran_user,
                   bill_amount, discount, net_amount, payment, receive, due_col, due_disc, due
            FROM transaction__mains
            WHERE id = %s AND tran_type = 1 AND tran_id LIKE 'GPA%%'
            LIMIT 1
        """, [id])
        rows = dictfetchall(cursor)

    return render(request, "general_transaction/party_payment/payment_form.html", {
        "transaction": rows[0] if rows else None,
        "party_payment_process_url": f"/bank-bima/party-payment/process/{id}/",
        "party_payment_redirect_url": "/bank-bima/party-payment/",
    })


@csrf_exempt
@transaction.atomic
def bank_bima_party_payment_process(request, id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)

    try:
        pay_amount = float(request.POST.get("pay_amount", 0) or 0)
        due_discount = float(request.POST.get("due_discount", 0) or 0)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid amount"}, status=400)

    if pay_amount <= 0 and due_discount <= 0:
        return JsonResponse({"success": False, "error": "Payment or discount must be greater than 0"}, status=400)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT tran_id, invoice_ref, tran_type, tran_method, tran_user, user_name,
                   tran_type_with, store_id, loc_id, tran_date, status, bill_amount,
                   discount, net_amount, due, due_col, due_disc
            FROM transaction__mains
            WHERE id = %s AND tran_type = 1 AND tran_id LIKE 'GPA%%'
            LIMIT 1
        """, [id])
        row = cursor.fetchone()
        if not row:
            return JsonResponse({"success": False, "error": "Bank Bima transaction not found"}, status=404)

        (old_tran_id, invoice_ref, tran_type, tran_method, tran_user, user_name,
         tran_type_with, store_id, loc_id, tran_date, status, bill_amount,
         discount, net_amount, current_due, old_due_col, old_due_disc) = row

        current_due = float(current_due or 0)
        if current_due <= 0:
            return JsonResponse({"success": False, "error": "No due amount found"}, status=400)
        if pay_amount + due_discount > current_due:
            return JsonResponse({"success": False, "error": "Payment + Discount exceeds due"}, status=400)

        new_due = current_due - pay_amount - due_discount
        new_due_col = float(old_due_col or 0) + pay_amount
        new_due_disc = float(old_due_disc or 0) + due_discount

        cursor.execute("""
            SELECT tran_id FROM transaction__party__payments
            WHERE tran_id LIKE 'GPA%%' ORDER BY id DESC LIMIT 1
        """)
        last = cursor.fetchone()
        last_no = int(last[0][3:]) if last and last[0] else 0
        payment_tran_id = "GPA" + str(last_no + 1).zfill(9)

        cursor.execute("""
            UPDATE transaction__mains
            SET due = %s, due_col = %s, due_disc = %s
            WHERE id = %s AND tran_type = 1
        """, [new_due, new_due_col, new_due_disc, id])
        cursor.execute("""
            SELECT id, COALESCE(tot_amount, amount, 0)
            FROM transaction__details
            WHERE tran_id = %s AND tran_type = 1
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
        cursor.execute("""
            INSERT INTO transaction__party__payments
            (tran_id, invoice_ref, tran_type, tran_method, tran_user, user_name,
             tran_type_with, store_id, loc_id, tran_date, status, bill_amount,
             discount, net_amount, payment, due, due_col, due_disc)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, [payment_tran_id, old_tran_id, tran_type, tran_method, tran_user, user_name,
              tran_type_with, store_id, loc_id, tran_date, status, bill_amount,
              discount, net_amount, pay_amount, new_due, pay_amount, due_discount])

    return JsonResponse({
        "success": True,
        "paid": pay_amount,
        "due_discount": due_discount,
        "new_due": new_due,
        "redirect_url": "/bank-bima/party-payment/",
    })


@csrf_exempt
@transaction.atomic
def bank_bima_party_payment_fifo(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)
    try:
        payment_amount = float(request.POST.get("payment", 0) or 0)
        ids = json.loads(request.POST.get("ids", "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid payment request"}, status=400)
    if payment_amount <= 0 or not ids:
        return JsonResponse({"success": False, "error": "Invalid payment request"}, status=400)

    remaining = payment_amount
    placeholders = ",".join(["%s"] * len(ids))
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT id, invoice_ref, bill_amount, payment, due
            FROM transaction__mains
            WHERE id IN ({placeholders}) AND tran_type = 1 AND tran_id LIKE 'GPA%%'
            ORDER BY tran_date ASC, id ASC
        """, ids)
        for row_id, invoice_ref, bill_amount, old_payment, due in cursor.fetchall():
            if remaining <= 0:
                break
            due = float(due or 0)
            if due <= 0:
                continue
            paid = min(remaining, due)
            new_due = due - paid
            cursor.execute("""
                UPDATE transaction__mains
                SET payment = COALESCE(payment, 0) + %s, due = %s, due_col = COALESCE(due_col, 0) + %s
                WHERE id = %s AND tran_type = 1
            """, [paid, new_due, paid, row_id])
            cursor.execute("""
                UPDATE transaction__details
                SET payment = COALESCE(payment, 0) + %s,
                    due = GREATEST(COALESCE(due, 0) - %s, 0),
                    due_col = COALESCE(due_col, 0) + %s
                WHERE invoice_ref = %s AND tran_type = 1
            """, [paid, paid, paid, invoice_ref])
            remaining -= paid

    return JsonResponse({"success": True, "paid": payment_amount - remaining})


def _page_init_data(page_id):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT
            s.tran_main_head_id AS tran_main_head_id,
            s.user_tran_method AS user_tran_method,
            s.user_tran_with_id AS user_tran_with_id,
            s.tran_method AS tran_method,
            s.tran_group_id AS tran_group_id
        FROM page_init s
        WHERE s.page_id = %s
    """, [page_id])
    return [
        {
            "tran_main_head_id": row[0],
            "user_tran_method": row[1],
            "user_tran_with_id": row[2],
            "tran_method": row[3],
            "tran_group_id": row[4],
        }
        for row in cursor.fetchall()
    ]


def advertisement_sales_page_init(request):
    page_id = request.GET.get("page_id")
    return JsonResponse({"get_page_init_data": _page_init_data(page_id)})


def printing_sales_page_init(request):
    page_id = request.GET.get("page_id")
    return JsonResponse({"get_page_init_data": _page_init_data(page_id)})


def office_bazar_page_init(request):
    page_id = request.GET.get("page_id")
    return JsonResponse({"get_page_init_data": _page_init_data(page_id)})


def advertisement_sales_load(request):
    q = (request.GET.get("q") or request.GET.get("search") or "").strip()
    status_filter = request.GET.get("status", "").strip()
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    page_id = request.GET.get("page_id")
    tran_main_head = request.GET.get("tran_main_head") or request.GET.get("transactionmainheads")
    tran_with_method = request.GET.get("tran_with_method") or request.GET.get("transaction_with_method")
    tran_with = request.GET.get("tran_with") or request.GET.get("transaction_with")
    supplier = request.GET.get("supplier") or request.GET.get("transaction_with_user")
    tran_group = request.GET.get("tran_group") or request.GET.get("tran_group_id")

    if page_id:
        page_rows = _page_init_data(page_id)
        if page_rows:
            tran_main_head = page_rows[0].get("tran_main_head_id")
            tran_with_method = page_rows[0].get("user_tran_method")
            tran_with = page_rows[0].get("user_tran_with_id")
            tran_group = page_rows[0].get("tran_group_id")

    try:
        offset = int(request.GET.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0

    try:
        limit = int(request.GET.get("limit") or request.GET.get("per_page") or 50)
    except (TypeError, ValueError):
        limit = 50

    if limit <= 0:
        limit = 50
    limit = min(limit, 200)

    sql = """
        SELECT
            m.id,
            m.tran_id AS tran_id,
            m.invoice_ref AS invoice_ref,
            DATE_FORMAT(m.tran_date, '%%Y-%%m-%%d') AS tran_date,
            DATE_FORMAT(m.tran_date, '%%H:%%i:%%s') AS tran_time,
            m.tran_type_with AS tran_type_with_id,
            COALESCE(tw.tran_with_name, CAST(m.tran_type_with AS CHAR)) AS tran_type_with,
            m.tran_user AS tran_user_id,
            COALESCE(NULLIF(m.user_name, ''), ui.user_name, m.tran_user) AS tran_user,
            m.bill_amount AS bill_total,
            m.discount AS discount,
            m.net_amount AS net_total,
            COALESCE(m.receive, m.payment, 0) AS advance,
            m.due_col AS due_collection,
            m.due_disc AS due_discount,
            m.due AS due,
            m.status AS status
        FROM transaction__mains m
        LEFT JOIN transaction__withs tw ON tw.id = m.tran_type_with
        LEFT JOIN user__infos ui
            ON ui.user_id = m.tran_user
            OR CAST(ui.id AS CHAR) = m.tran_user
        WHERE 1=1
    """
    total_sql = """
        SELECT COALESCE(SUM(m.due), 0)
        FROM transaction__mains m
        LEFT JOIN user__infos ui
            ON ui.user_id = m.tran_user
            OR CAST(ui.id AS CHAR) = m.tran_user
        WHERE 1=1
    """

    params = []
    total_params = []

    if q:
        sql += """
            AND (
                m.tran_id LIKE %s
                OR m.invoice_ref LIKE %s
                OR m.tran_user LIKE %s
                OR m.user_name LIKE %s
                OR ui.user_name LIKE %s
            )
        """
        params.extend([f"%{q}%"] * 5)
        total_sql += """
            AND (
                m.tran_id LIKE %s
                OR m.invoice_ref LIKE %s
                OR m.tran_user LIKE %s
                OR m.user_name LIKE %s
                OR ui.user_name LIKE %s
            )
        """
        total_params.extend([f"%{q}%"] * 5)

    if status_filter in ("0", "1"):
        sql += " AND m.status = %s"
        params.append(status_filter)
        total_sql += " AND m.status = %s"
        total_params.append(status_filter)

    if tran_main_head:
        sql += """
            AND (
                m.tran_type = %s
                OR EXISTS (
                    SELECT 1
                    FROM transaction__details d
                    JOIN transaction__groupes g ON g.id = d.tran_groupe_id
                    WHERE d.tran_id = m.tran_id
                    AND g.tran_groupe_type = %s
                )
            )
        """
        params.extend([tran_main_head, tran_main_head])
        total_sql += """
            AND (
                m.tran_type = %s
                OR EXISTS (
                    SELECT 1
                    FROM transaction__details d
                    JOIN transaction__groupes g ON g.id = d.tran_groupe_id
                    WHERE d.tran_id = m.tran_id
                    AND g.tran_groupe_type = %s
                )
            )
        """
        total_params.extend([tran_main_head, tran_main_head])

    if tran_with_method:
        sql += """
            AND m.tran_type_with IN (
                SELECT id FROM transaction__withs
                WHERE tran_method = %s
            )
        """
        params.append(tran_with_method)
        total_sql += """
            AND m.tran_type_with IN (
                SELECT id FROM transaction__withs
                WHERE tran_method = %s
            )
        """
        total_params.append(tran_with_method)

    if tran_with:
        sql += " AND m.tran_type_with = %s"
        params.append(tran_with)
        total_sql += " AND m.tran_type_with = %s"
        total_params.append(tran_with)

    if tran_group:
        sql += """
            AND EXISTS (
                SELECT 1
                FROM transaction__details d
                WHERE d.tran_id = m.tran_id
                AND d.tran_groupe_id = %s
            )
        """
        params.append(tran_group)
        total_sql += """
            AND EXISTS (
                SELECT 1
                FROM transaction__details d
                WHERE d.tran_id = m.tran_id
                AND d.tran_groupe_id = %s
            )
        """
        total_params.append(tran_group)

    if supplier:
        sql += """
            AND (
                m.tran_user = %s
                OR ui.user_id = %s
                OR CAST(ui.id AS CHAR) = %s
            )
        """
        params.extend([supplier, supplier, supplier])
        total_sql += """
            AND (
                m.tran_user = %s
                OR ui.user_id = %s
                OR CAST(ui.id AS CHAR) = %s
            )
        """
        total_params.extend([supplier, supplier, supplier])

    # The shared list query serves both Bank Bima payment and receive pages.
    # Keep their transaction streams separate: receive rows use GRE IDs.
    tran_id_prefix = "GRE%" if "/general-transaction/receive/" in request.path else "GPA%"
    sql += " AND m.tran_id LIKE %s"
    params.append(tran_id_prefix)
    total_sql += " AND m.tran_id LIKE %s"
    total_params.append(tran_id_prefix)

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

    sql += " ORDER BY m.id ASC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor = connection.cursor()
    cursor.execute(sql, params)
    data = dictfetchall(cursor)
    cursor.execute(total_sql, total_params)
    total_due = cursor.fetchone()[0] or 0

    return JsonResponse({
        "results": data,
        "total_due": float(total_due),
    })


def printing_sales_load(request):
    return advertisement_sales_load(request)


def _bank_bima_edit_data(transaction_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT m.id, m.tran_id, m.invoice_ref, m.loc_id, m.store_id,
                   m.tran_type, m.tran_method, m.tran_type_with,
                   tw.tran_method AS tran_with_method,
                   COALESCE(CAST(ui.id AS CHAR), m.tran_user) AS tran_user,
                   COALESCE(ui.user_name, m.user_name) AS user_name,
                   loc.division AS location_name, m.bill_amount, m.discount,
                   m.net_amount, m.receive, m.payment, m.due, m.tran_date,
                   m.payment_mode
            FROM transaction__mains m
            LEFT JOIN transaction__withs tw ON tw.id = m.tran_type_with
            LEFT JOIN user__infos ui ON ui.user_id = m.tran_user
                                      OR CAST(ui.id AS CHAR) = m.tran_user
            LEFT JOIN location__infos loc ON loc.id = m.loc_id
            WHERE m.id = %s LIMIT 1
        """, [transaction_id])
        rows = dictfetchall(cursor)
        main = rows[0] if rows else None
        if not main:
            return None, []
        cursor.execute("""
            SELECT d.id, d.tran_head_id AS product_id,
                   h.tran_head_name AS product_name, d.quantity, d.cp, d.mrp,
                   d.amount AS total, d.expiry_date,
                   COALESCE(d.tran_groupe_id, h.groupe_id) AS tran_group_id,
                   g.tran_method AS tran_group_method
            FROM transaction__details d
            LEFT JOIN transaction__heads h ON h.id = d.tran_head_id
            LEFT JOIN transaction__groupes g
                   ON g.id = COALESCE(d.tran_groupe_id, h.groupe_id)
            WHERE d.tran_id = %s OR d.invoice_ref = %s
            ORDER BY d.id ASC
        """, [main["tran_id"], main.get("invoice_ref") or main["tran_id"]])
        details = dictfetchall(cursor)
        if details:
            main["tran_group_id"] = details[0].get("tran_group_id")
            main["tran_group_method"] = details[0].get("tran_group_method")
        else:
            cursor.execute("""
                SELECT p.tran_group_id, g.tran_method
                FROM page_init p
                LEFT JOIN transaction__groupes g ON g.id = p.tran_group_id
                WHERE p.tran_main_head_id = %s
                  AND p.user_tran_with_id = %s
                ORDER BY p.id ASC LIMIT 1
            """, [main.get("tran_type"), main.get("tran_type_with")])
            page_row = cursor.fetchone()
            main["tran_group_id"] = page_row[0] if page_row else ""
            main["tran_group_method"] = page_row[1] if page_row else ""
    main["tran_date"] = main["tran_date"].strftime("%Y-%m-%d") if main.get("tran_date") else ""
    for item in details:
        if item.get("expiry_date"):
            item["expiry_date"] = item["expiry_date"].strftime("%Y-%m-%d")
    return main, details


def _render_bank_bima_edit(request, id, template_name, page_title, receive_mode=False):
    main, details = _bank_bima_edit_data(id)
    if not main:
        return redirect("bank_bima_general_transaction_receive_list" if receive_mode else "bank_bima_advertisement_sales")
    return render(request, template_name, {
        "edit_transaction": main,
        "edit_details": details,
        "edit_transaction_json": json.dumps(main, default=str),
        "edit_details_json": json.dumps(details, default=str),
        "edit_mode": True,
        "bank_bima_receive_mode": receive_mode,
        "page_id": request.GET.get("page_id") or "",
        "page_title": page_title,
        "fixed_location_id": main.get("loc_id") or "",
        "fixed_location_name": main.get("location_name") or "",
    })


def advertisement_sales_edit(request, id):
    if "/office-bazar/" in request.path:
        template, title = "bank_bima/office_bazar_payment.html", "Office Bazar"
    elif "/printing-sales/" in request.path:
        template, title = "bank_bima/printing_sales_payment.html", "Printing Sale"
    else:
        template, title = "bank_bima/advertisement_sales_payment.html", "Advertisement Sales"
    return _render_bank_bima_edit(request, id, template, title)


def printing_sales_edit(request, id):
    return advertisement_sales_edit(request, id)


def add_payment_page(request):
    return advertisement_sales_add(request)


def advertisement_sales_product_search(request):
    q = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0))
    tran_main_head_id = (request.GET.get('tran_main_head_id') or '').strip()
    tran_group_id = (request.GET.get('tran_group_id') or '').strip()
    limit = 10

    if not tran_main_head_id or not tran_group_id:
        return JsonResponse({'results': []})

    cursor = connection.cursor()
    if q:
        sql = """
            SELECT
                t.id,
                t.tran_head_name AS name,
                t.cp,
                m.manufacturer_name AS manufacturer,
                f.form_name AS form,
                c.category_name,
                t.quantity,
                t.mrp
            FROM transaction__heads t
            JOIN transaction__groupes tg ON t.groupe_id = tg.id
            JOIN transaction__main__heads tmh ON tmh.id = tg.tran_groupe_type
            LEFT JOIN item__manufacturers m ON t.manufacturer_id = m.id
            LEFT JOIN item__forms f ON t.form_id = f.id
            LEFT JOIN item__categories c ON t.category_id = c.id
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
                c.category_name,
                t.quantity,
                t.mrp
            FROM transaction__heads t
            JOIN transaction__groupes tg ON t.groupe_id = tg.id
            JOIN transaction__main__heads tmh ON tmh.id = tg.tran_groupe_type
            LEFT JOIN item__manufacturers m ON t.manufacturer_id = m.id
            LEFT JOIN item__forms f ON t.form_id = f.id
            LEFT JOIN item__categories c ON t.category_id = c.id
            WHERE tmh.id = %s
            AND tg.id = %s
            ORDER BY t.id ASC
            LIMIT %s OFFSET %s
        """
        params = [tran_main_head_id, tran_group_id, limit, offset]

    cursor.execute(sql, params)
    return JsonResponse({'results': dictfetchall(cursor)})


def printing_sales_product_search(request):
    return advertisement_sales_product_search(request)


@csrf_exempt
@transaction.atomic
def advertisement_sales_save(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        data = json.loads(request.body)
        store_id = data.get("store")
        location_id = data.get("location")
        user_info_id = data.get("supplier")
        user_name = data.get("user_name")
        tran_type_with = data.get("tran_type_with")
        tran_group_id = data.get("tran_group_id")
        tran_type = data.get("tran_type") or 1
        payment_method = data.get("payment_method")
        payment_mode = "receive" if str(data.get("tran_method") or "").strip().lower() == "receive" else "payment"
        edit_id = data.get("edit_id")
        bill_amount = float(data.get("bill_amount") or 0)
        discount = float(data.get("discount") or 0)
        net_amount = float(data.get("net_amount") or 0)
        amount = float(
            (data.get("receive") or 0)
            if payment_mode == "receive"
            else (data.get("payment") or 0)
        )
        receive = amount if payment_mode == "receive" else 0
        payment = amount if payment_mode == "payment" else 0
        due = float(data.get("due") or 0)
        products = data.get("products") or []

        bill_amount = sum(float(r[5] or 0) if len(r) > 5 else 0 for r in products)
        discount = float(discount or 0)
        net_amount = max(bill_amount - discount, 0)
        due = max(net_amount - amount, 0)

        if not user_info_id:
            return JsonResponse({"success": False, "message": "User required"}, status=400)

        if not tran_type_with:
            return JsonResponse({"success": False, "message": "Transaction With required"}, status=400)

        tran_date = get_local_tran_datetime(data.get("tran_date"))

        edit_tran_id = data.get("edit_tran_id")
        invoice = data.get("invoice")
        tran_id = None
        with connection.cursor() as cursor:
            # During edit, resolve the original main row first.  Never fall
            # back to generating a new GPA ID when an edit identifier exists.
            if edit_id:
                cursor.execute(
                    "SELECT id, tran_id, invoice_ref FROM transaction__mains WHERE id = %s LIMIT 1",
                    [edit_id],
                )
                existing = cursor.fetchone()
            elif edit_tran_id:
                cursor.execute(
                    "SELECT id, tran_id, invoice_ref FROM transaction__mains WHERE tran_id = %s LIMIT 1",
                    [edit_tran_id],
                )
                existing = cursor.fetchone()
            elif invoice:
                cursor.execute("""
                    SELECT id, tran_id, invoice_ref
                    FROM transaction__mains
                    WHERE tran_id = %s OR invoice_ref = %s
                    LIMIT 1
                """, [invoice, invoice])
                existing = cursor.fetchone()
            else:
                existing = None

            if edit_id or edit_tran_id:
                if not existing:
                    return JsonResponse({"success": False, "message": "Transaction not found"}, status=404)
                edit_id, tran_id, old_invoice = existing
                # Keep the original invoice reference unless the edit form
                # explicitly supplies a different one.
                invoice = invoice or old_invoice or tran_id
            elif existing:
                edit_id, tran_id, old_invoice = existing
                invoice = invoice or old_invoice or tran_id

            if not tran_id:
                cursor.execute("""
                    SELECT tran_id FROM transaction__mains
                    WHERE tran_id LIKE 'GPA%'
                    ORDER BY tran_id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                last_number = int(row[0][3:]) if row else 0
                tran_id = "GPA" + str(last_number + 1).zfill(9)
                invoice = tran_id

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT user_name
                FROM user__infos
                WHERE user_id = %s OR CAST(id AS CHAR) = %s
                LIMIT 1
            """, [user_info_id, user_info_id])
            row = cursor.fetchone()
            user_name = row[0] if row else "UNKNOWN"

        if edit_id:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE transaction__mains
                    SET tran_type=%s, tran_method=%s, tran_user=%s, user_name=%s,
                        tran_type_with=%s, store_id=%s, loc_id=%s, tran_date=%s,
                        invoice_ref=%s, bill_amount=%s, discount=%s, net_amount=%s,
                        receive=%s, payment=%s, due=%s
                    WHERE id=%s
                """, [tran_type, payment_method, user_info_id, user_name,
                      tran_type_with, store_id, location_id, tran_date, invoice,
                      bill_amount, discount, net_amount, receive, payment, due,
                      edit_id])
                cursor.execute("DELETE FROM transaction__details WHERE tran_id=%s", [tran_id])

        if not edit_id:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO transaction__mains
                    (tran_id, tran_type, tran_method, tran_user, user_name,
                     tran_type_with, store_id, loc_id, tran_date, status,
                     invoice_ref, bill_amount, discount, net_amount, receive, payment, due)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, [tran_id, tran_type, payment_method, user_info_id, user_name,
                      tran_type_with, store_id, location_id, tran_date, 1, invoice,
                      bill_amount, discount, net_amount, receive, payment, due])

        details_data = []
        weights = [float(r[5] or 0) if len(r) > 5 else 0 for r in products]
        discounts = allocate_amount(discount, weights)
        receives = allocate_amount(receive, weights)
        payments = allocate_amount(payment, weights)
        dues = allocate_amount(due, weights)
        for index, r in enumerate(products):
            product_id = r[0] if len(r) > 0 else None
            qty = float(r[1] or 0) if len(r) > 1 else 0
            cp = float(r[2] or 0) if len(r) > 2 else 0
            mrp = float(r[3] or 0) if len(r) > 3 else 0
            expiry = r[4] if len(r) > 4 else None
            total = float(r[5] or 0) if len(r) > 5 else 0
            details_data.append([
                tran_id,
                tran_type,
                payment_method,
                invoice,
                location_id,
                tran_type_with,
                tran_group_id,
                product_id,
                1,
                qty,
                0,
                0,
                cp,
                mrp,
                total,
                max(total - discounts[index], 0),
                expiry,
                user_name,
                store_id,
                tran_date,
                1,
                discounts[index],
                receives[index],
                payments[index],
                dues[index],
            ])

        with connection.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO transaction__details
                (tran_id, tran_type, tran_method, invoice_ref, loc_id,
                tran_type_with, tran_groupe_id, tran_head_id, quantity_actual,
                quantity, quantity_issue, quantity_return, cp, mrp, amount, tot_amount,
                expiry_date, user_name, store_id,
                tran_date, status, discount, receive, payment, due)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, details_data)

        set_payment_mode(tran_id, payment_mode)

        return JsonResponse({"success": True, "tran_id": tran_id})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def printing_sales_save(request):
    return advertisement_sales_save(request)


def bank_bima_general_transaction_payment_list(request):
    page_id = request.GET.get("page_id") or "1020300014"
    return render(request, "bank_bima/general_transaction_payment_list.html", {
        "page_title": "Bank Bima General Transaction Payment",
        "list_title": "Bank Bima General Transaction Payment List",
        "page_id": page_id,
        "payment_list_url": "/bank-bima/general-transaction/payment/load/",
        "payment_edit_url": "/bank-bima/general-transaction/payment/edit/",
        "add_payment_url": "/bank-bima/general-transaction/payment/add/",
    })


def bank_bima_general_transaction_payment_add(request):
    fixed_location_id, fixed_location_name = get_login_location(request)
    return render(request, "bank_bima/general_transaction_payment.html", {
        "fixed_location_id": fixed_location_id or "",
        "fixed_location_name": fixed_location_name or "",
        "page_id": request.GET.get("page_id") or "",
        "page_title": "Bank Bima General Transaction Payment",
    })


def bank_bima_general_transaction_receive_list(request):
    return render(request, "bank_bima/general_transaction_payment_list.html", {
        "page_title": "Bank Bima General Transaction Receive",
        "list_title": "Bank Bima General Transaction Receive List",
        "page_id": request.GET.get("page_id") or "1020300015",
        "receive_mode": True,
        "payment_list_url": "/bank-bima/general-transaction/receive/load/",
        "payment_edit_url": "/bank-bima/general-transaction/receive/edit/",
        "add_payment_url": "/bank-bima/general-transaction/receive/add/",
    })


def bank_bima_general_transaction_receive_add(request):
    fixed_location_id, fixed_location_name = get_login_location(request)
    return render(request, "bank_bima/general_transaction_payment.html", {
        "fixed_location_id": fixed_location_id or "",
        "fixed_location_name": fixed_location_name or "",
        "page_id": request.GET.get("page_id") or "1020300015",
        "page_title": "Bank Bima General Transaction Receive",
        "bank_bima_receive_mode": True,
    })


def bank_bima_general_transaction_payment_load(request):
    return advertisement_sales_load(request)


def bank_bima_general_transaction_receive_load(request):
    return advertisement_sales_load(request)


@csrf_exempt
@transaction.atomic
def bank_bima_general_transaction_receive_save(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    try:
        edit_data = json.loads(request.body)
    except (TypeError, ValueError):
        edit_data = {}
    if edit_data.get("edit_id") or edit_data.get("edit_tran_id"):
        return advertisement_sales_save(request)

    try:
        data = json.loads(request.body)
        user_info_id = data.get("supplier")
        tran_type_with = data.get("tran_type_with")
        products = data.get("products") or []

        if not user_info_id:
            return JsonResponse({"success": False, "message": "User required"}, status=400)
        if not tran_type_with:
            return JsonResponse({"success": False, "message": "Transaction With required"}, status=400)
        if not products:
            return JsonResponse({"success": False, "message": "Products required"}, status=400)

        location_id = data.get("location")
        store_id = data.get("store")
        tran_type = int(data.get("tran_type") or 1)
        tran_group_id = data.get("tran_group_id")
        tran_date = get_local_tran_datetime(data.get("tran_date"))
        bill_amount = float(data.get("bill_amount") or 0)
        discount = float(data.get("discount") or 0)
        net_amount = float(data.get("net_amount") or 0)
        receive = float(data.get("receive") or 0)
        due = float(data.get("due") or 0)
        invoice = data.get("invoice")

        bill_amount = sum(float(r[5] or 0) if len(r) > 5 else 0 for r in products)
        discount = float(discount or 0)
        net_amount = max(bill_amount - discount, 0)
        due = max(net_amount - receive, 0)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tran_id FROM transaction__mains
                WHERE tran_id LIKE 'GRE%' ORDER BY tran_id DESC LIMIT 1
            """)
            row = cursor.fetchone()
            last_number = int(row[0][3:]) if row else 0
            tran_id = "GRE" + str(last_number + 1).zfill(9)
            invoice = invoice or tran_id

            cursor.execute("""
                SELECT user_name FROM user__infos
                WHERE user_id = %s OR CAST(id AS CHAR) = %s LIMIT 1
            """, [user_info_id, user_info_id])
            user_row = cursor.fetchone()
            user_name = user_row[0] if user_row else "UNKNOWN"

            cursor.execute("""
                INSERT INTO transaction__mains
                (tran_id, tran_type, tran_method, tran_user, user_name,
                 tran_type_with, store_id, loc_id, tran_date, status,
                 invoice_ref, bill_amount, discount, net_amount, payment, due)
                VALUES (%s,%s,'receive',%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,0,%s)
            """, [tran_id, tran_type, user_info_id, user_name, tran_type_with,
                  store_id, location_id, tran_date, invoice, bill_amount,
                  discount, net_amount, due])

            details_data = []
            weights = [float(item[5] or 0) for item in products]
            discounts = allocate_amount(discount, weights)
            receives = allocate_amount(receive, weights)
            dues = allocate_amount(due, weights)
            for index, item in enumerate(products):
                details_data.append([
                    tran_id, tran_type, "receive", invoice, location_id,
                    tran_type_with, tran_group_id, item[0], 1,
                    float(item[1] or 0), 0, 0, float(item[2] or 0),
                    float(item[3] or 0), float(item[5] or 0), max(float(item[5] or 0) - discounts[index], 0), item[4] or None,
                    user_name, store_id, tran_date, 1, discounts[index], receives[index], 0, dues[index]
                ])

            cursor.executemany("""
                INSERT INTO transaction__details
                (tran_id, tran_type, tran_method, invoice_ref, loc_id,
                 tran_type_with, tran_groupe_id, tran_head_id, quantity_actual,
                 quantity, quantity_issue, quantity_return, cp, mrp, amount, tot_amount,
                 expiry_date, user_name, store_id, tran_date, status, discount,
                 receive, payment, due)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, details_data)

        set_payment_mode(tran_id, "receive")

        return JsonResponse({"success": True, "tran_id": tran_id})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def bank_bima_general_transaction_payment_edit(request, id):
    return _render_bank_bima_edit(
        request, id, "bank_bima/general_transaction_payment.html",
        "Bank Bima General Transaction Payment",
    )


def bank_bima_general_transaction_receive_edit(request, id):
    return _render_bank_bima_edit(
        request, id, "bank_bima/general_transaction_payment.html",
        "Bank Bima General Transaction Receive", receive_mode=True,
    )


def bank_bima_general_transaction_payment_save(request):
    return advertisement_sales_save(request)
