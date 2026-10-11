
import json
import traceback
from datetime import datetime

from django.db import connection, transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from . import tran_views


# =========================================================
# HOTEL CONFIG
# =========================================================

HOTEL_TRAN_TYPE = 8
HOTEL_PREFIX = "HTL"


# =========================================================
# COMMON
# =========================================================

def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def get_login_location(request):

    location_id = (
        request.session.get("loc_id")
        or request.session.get("location_id")
    )

    location_name = (
        request.session.get("location_name")
        or ""
    )

    if location_id:

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    id,
                    division
                FROM location__infos
                WHERE id = %s
                LIMIT 1
            """, [location_id])

            row = cursor.fetchone()

        if row:
            return row[0], row[1]

    return "", ""


def get_transaction_user(request):

    tran_by = None

    if request.user.is_authenticated:
        tran_by = (
            request.user.username
            or str(request.user.id)
        )

    if not tran_by:
        tran_by = (
            request.session.get("username")
            or request.session.get("user_name")
            or request.session.get("name")
            or request.session.get("user_id")
            or ""
        )

    return tran_by


def get_guest_transaction_with():

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                id,
                tran_method,
                user_role
            FROM transaction__withs
            WHERE LOWER(tran_with_name) = 'guest'
            AND status = 1
            ORDER BY id DESC
            LIMIT 1
        """)

        row = cursor.fetchone()

    if row:
        return {
            "id": row[0],
            "tran_method": row[1] or "Both",
            "user_role": row[2]
        }

    return None


# =========================================================
# PAYMENT LIST PAGE
# =========================================================

def hotel_payment_list(request):

    return render(
        request,
        "hotel/transaction_list.html"
    )


# =========================================================
# ADD PAYMENT PAGE
# =========================================================

def add_hotel_payment_page(request):

    fixed_location_id, fixed_location_name = (
        get_login_location(request)
    )

    return render(
        request,
        "hotel/transaction.html",
        {
            "fixed_location_id":
                fixed_location_id or "",

            "fixed_location_name":
                fixed_location_name or "",

            "edit_mode": False,
        }
    )


# ==========================================
# PRODUCT SEARCH
# ==========================================

def product_search(request):

    q = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0))

    tran_main_head_id = request.GET.get(
        'tran_main_head_id',
        ''
    ).strip()

    tran_group_id = request.GET.get(
        'tran_group_id'
    )

    limit = 10

    if not tran_main_head_id or not tran_group_id:
        return JsonResponse({
            'results': []
        })

    with connection.cursor() as cursor:

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

                JOIN transaction__groupes tg
                    ON t.groupe_id = tg.id

                JOIN transaction__main__heads tmh
                    ON tmh.id = tg.tran_groupe_type

                LEFT JOIN item__manufacturers m
                    ON t.manufacturer_id = m.id

                LEFT JOIN item__forms f
                    ON t.form_id = f.id

                LEFT JOIN transaction__category c
                    ON t.category_id = c.id

                WHERE t.tran_head_name LIKE %s
                AND tmh.id = %s
                AND tg.id = %s

                ORDER BY t.id ASC

                LIMIT %s OFFSET %s
            """

            params = [
                f"{q}%",
                tran_main_head_id,
                tran_group_id,
                limit,
                offset
            ]

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

                JOIN transaction__groupes tg
                    ON t.groupe_id = tg.id

                JOIN transaction__main__heads tmh
                    ON tmh.id = tg.tran_groupe_type

                LEFT JOIN item__manufacturers m
                    ON t.manufacturer_id = m.id

                LEFT JOIN item__forms f
                    ON t.form_id = f.id

                LEFT JOIN transaction__category c
                    ON t.category_id = c.id

                WHERE tmh.id = %s
                AND tg.id = %s

                ORDER BY t.id ASC

                LIMIT %s OFFSET %s
            """

            params = [
                tran_main_head_id,
                tran_group_id,
                limit,
                offset
            ]

        cursor.execute(sql, params)

        data = dictfetchall(cursor)

    return JsonResponse({
        'results': data
    })


# ==========================================
# SR AGENT SEARCH
# ==========================================

def autocomplete_sr(request):

    q = request.GET.get(
        'term',
        request.GET.get('q', '')
    ).strip()

    with connection.cursor() as cursor:

        sql = """
            SELECT
                id,
                custom_sr_id,
                name
            FROM item__sr_agents
            WHERE (
                name LIKE %s
                OR custom_sr_id LIKE %s
            )
            AND is_active = 1
            LIMIT 20
        """

        cursor.execute(
            sql,
            [
                f"%{q}%",
                f"%{q}%"
            ]
        )

        columns = [
            col[0]
            for col in cursor.description
        ]

        raw_data = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    results = []

    for row in raw_data:

        results.append({
            'id': row['id'],
            'text': (
                f"{row['custom_sr_id']} - "
                f"{row['name']}"
            ),
            'name_display': row['name']
        })

    return JsonResponse({
        'results': results
    })


# ============================================================
# HOTEL SR COMBO
# ============================================================

def hotel_filter_sr_combo(request):

    if request.method == 'GET':

        try:

            search_text = request.GET.get('q', '')


            with connection.cursor() as cursor:

                sql = """
                    SELECT
                        custom_sr_id,
                        name

                    FROM item__sr_agents

                    WHERE 1 = 1
                """


                params = []


                # =================================================
                # SEARCH
                # =================================================

                if search_text:

                    sql += """
                        AND (
                            name LIKE %s
                            OR custom_sr_id LIKE %s
                        )
                    """


                    search_value = (
                        '%'
                        + search_text
                        + '%'
                    )


                    params = [
                        search_value,
                        search_value
                    ]


                sql += """
                    ORDER BY
                        name ASC

                    LIMIT 200
                """


                cursor.execute(
                    sql,
                    params
                )


                rows = cursor.fetchall()


            # =====================================================
            # SR LIST
            # =====================================================

            sr_list = []


            for row in rows:

                sr_list.append({

                    'id':
                        row[0] or '',

                    'sr_id':
                        row[0] or '',

                    'sr_name':
                        row[1] or '',

                    'name':
                        (
                            str(row[0] or '')
                            + ' - '
                            + str(row[1] or '')
                        )

                })


            return JsonResponse({

                'status':
                    'success',

                'results':
                    sr_list

            })


        except Exception as e:

            return JsonResponse({

                'status':
                    'error',

                'message':
                    str(e)

            }, status=500)


    return JsonResponse({

        'status':
            'error',

        'message':
            'Invalid request'

    })

#---------------------------------
# Guest_combo
#---------------------------------
def hotel_filter_guest_combo(request):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                guest_id,
                guest_name,
                mobile
            FROM hotel_guests_info
            ORDER BY guest_name ASC
        """)

        rows = cursor.fetchall()

    return JsonResponse({
        "status": "success",
        "results": [
            {
                "id": row[0],
                "guest_id": row[0],
                "guest_name": row[1],
                "mobile": row[2],
                "name": f"{row[0]} - {row[1]}"
            }
            for row in rows
        ]
    })

# =========================================================
# TRANSACTION BY COMBO
# =========================================================

def hotel_filter_tran_by_combo(request):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT DISTINCT
                tran_by
            FROM transaction__mains
            WHERE tran_type = %s
              AND tran_by IS NOT NULL
              AND tran_by != ''
            ORDER BY tran_by ASC
        """, [
            HOTEL_TRAN_TYPE
        ])

        rows = cursor.fetchall()

    return JsonResponse({
        "results": [
            {
                "id": row[0],
                "name": row[0]
            }
            for row in rows
        ]
    })


# =========================================================
# PAGE INIT
# =========================================================

def get_page_init_add_payment(request):

    page_id = request.GET.get(
        "page_id"
    )

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                s.tran_main_head_id,
                s.user_tran_method,
                s.user_tran_with_id,
                s.tran_method,
                s.tran_group_id

            FROM page_init s

            WHERE s.page_id = %s
        """, [page_id])

        rows = cursor.fetchall()

    data = [
        {
            "tran_main_head_id":
                row[0],

            "user_tran_method":
                row[1],

            "user_tran_with_id":
                row[2],

            "tran_method":
                row[3],

            "tran_group_id":
                row[4],
        }

        for row in rows
    ]

    return JsonResponse({
        "get_page_init_data": data
    })


# =========================================================
# GET GUEST
# =========================================================

def get_guest_info(guest_value):

    if not guest_value:
        return None

    guest_value = str(
        guest_value
    ).strip()

    with connection.cursor() as cursor:

        if guest_value.isdigit():

            cursor.execute("""
                SELECT
                    id,
                    user_id,
                    user_name,
                    user_phone,
                    address,
                    tran_user_type,
                    tran_with_id

                FROM user__infos

                WHERE id = %s

                AND status = 1

                LIMIT 1
            """, [guest_value])

        else:

            cursor.execute("""
                SELECT
                    id,
                    user_id,
                    user_name,
                    user_phone,
                    address,
                    tran_user_type,
                    tran_with_id

                FROM user__infos

                WHERE user_id = %s

                AND status = 1

                LIMIT 1
            """, [guest_value])

        row = cursor.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "user_id": row[1],
        "user_name": row[2],
        "user_phone": row[3],
        "address": row[4],
        "tran_user_type": row[5],
        "tran_with_id": row[6],
    }


# =========================================================
# GET SR CUSTOM ID
# =========================================================

def get_sr_custom_id(sr_value):

    if not sr_value:
        return None

    sr_value = str(
        sr_value
    ).strip()

    with connection.cursor() as cursor:

        if sr_value.isdigit():

            cursor.execute("""
                SELECT
                    custom_sr_id

                FROM item__sr_agents

                WHERE id = %s

                LIMIT 1
            """, [sr_value])

        else:

            cursor.execute("""
                SELECT
                    custom_sr_id

                FROM item__sr_agents

                WHERE custom_sr_id = %s

                LIMIT 1
            """, [sr_value])

        row = cursor.fetchone()

    if row:
        return row[0]

    return None


def search_hotel_guest(request):

    if request.method == "GET":

        try:

            cursor = connection.cursor()

            sql = """
                SELECT
                    id,
                    guest_id,
                    title,
                    guest_name,
                    mobile,
                    gender,
                    date_of_birth,
                    nationality,
                    address,
                    booking_source,
                    guest_category,
                    check_in,
                    check_out,
                    Bed_Category,
                    bed_info,
                    emergency_guest_contact,
                    status
                FROM hotel_guests_info
                ORDER BY id DESC
            """

            cursor.execute(sql)

            rows = cursor.fetchall()

            guests = []

            for row in rows:

                guests.append({
                    'id': row[0],
                    'guest_id': row[1],
                    'title': row[2],
                    'guest_name': row[3],
                    'mobile': row[4],
                    'gender': row[5],
                    'date_of_birth': row[6],
                    'nationality': row[7],
                    'address': row[8],
                    'booking_source': row[9],
                    'guest_category': row[10],
                    'check_in': row[11],
                    'check_out': row[12],
                    'bed_category_id': row[13],
                    'bed_info_id': row[14],
                    'emergency_guest_contact': row[15],
                    'status': row[16]
                })

            return JsonResponse({
                'status': 'success',
                'results': guests
            })

        except Exception as e:

            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return JsonResponse({
        'status': 'failed',
        'message': 'Invalid request'
    })


# =========================================================
# GENERATE HOTEL TRANSACTION ID
# =========================================================

def generate_hotel_transaction_id():

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                MAX(
                    CAST(
                        REPLACE(
                            tran_id,
                            %s,
                            ''
                        )
                        AS UNSIGNED
                    )
                )

            FROM transaction__mains

            WHERE tran_id LIKE %s
        """, [
            HOTEL_PREFIX,
            HOTEL_PREFIX + "%"
        ])

        row = cursor.fetchone()

    last_number = (
        int(row[0])
        if row and row[0]
        else 0
    )

    new_number = (
        last_number + 1
    )

    return (
        HOTEL_PREFIX
        + str(new_number).zfill(9)
    )


# =========================================================
# ALLOCATE AMOUNT
# =========================================================

def allocate_amount(total_amount, weights):

    try:
        total_amount = float(
            total_amount or 0
        )
    except Exception:
        total_amount = 0

    if not weights:
        return []

    clean_weights = []

    for weight in weights:

        try:
            clean_weights.append(
                float(weight or 0)
            )

        except Exception:
            clean_weights.append(0)

    total_weight = sum(
        clean_weights
    )

    if total_weight <= 0:

        result = [
            0 for _ in clean_weights
        ]

        if result:
            result[0] = total_amount

        return result

    result = []

    used = 0

    for index, weight in enumerate(
        clean_weights
    ):

        if index == (
            len(clean_weights) - 1
        ):

            amount = (
                total_amount - used
            )

        else:

            amount = round(
                total_amount
                * weight
                / total_weight,
                2
            )

            used += amount

        result.append(
            amount
        )

    return result


# =========================================================
# DETAIL INSERT
# =========================================================

def insert_hotel_detail_rows(
    products,
    tran_id,
    tran_type,
    payment_method,
    invoice_ref,
    location_id,
    tran_type_with,
    user_id,
    tran_by,
    store_id,
    tran_date,
    status,
    discount,
    receive,
    payment,
    due,
    sr_id=None
):

    if not products:
        return

    # =====================================================
    # NORMALIZE PRODUCT DATA
    # Supports both:
    # 1. List format from current frontend
    # 2. Dictionary format
    # =====================================================

    normalized_products = []

    for product in products:

        # ---------------------------------------------
        # CURRENT FRONTEND LIST FORMAT
        #
        # [
        #   product_id,
        #   qty,
        #   cp,
        #   mrp,
        #   expiry_date,
        #   total
        # ]
        # ---------------------------------------------
        if isinstance(product, (list, tuple)):

            product_id = (
                product[0]
                if len(product) > 0
                else None
            )

            qty = (
                product[1]
                if len(product) > 1
                else 1
            )

            cp = (
                product[2]
                if len(product) > 2
                else 0
            )

            mrp = (
                product[3]
                if len(product) > 3
                else 0
            )

            expiry = (
                product[4]
                if len(product) > 4
                else None
            )

            total = (
                product[5]
                if len(product) > 5
                else 0
            )

            tran_group_id = None

        # ---------------------------------------------
        # DICTIONARY FORMAT
        # ---------------------------------------------
        elif isinstance(product, dict):

            product_id = (
                product.get("product_id")
                or product.get("tran_head_id")
                or product.get("id")
            )

            qty = (
                product.get("quantity")
                or product.get("qty")
                or 1
            )

            cp = (
                product.get("cp")
                or 0
            )

            mrp = (
                product.get("mrp")
                or 0
            )

            expiry = (
                product.get("expiry_date")
                or product.get("expiry")
                or None
            )

            total = (
                product.get("total")
                or product.get("tot_amount")
                or product.get("amount")
                or 0
            )

            tran_group_id = (
                product.get("tran_group_id")
                or product.get("tran_groupe_id")
                or None
            )

        else:
            continue

        # Empty string expiry date MySQL-এ সমস্যা করতে পারে
        if not expiry:
            expiry = None

        normalized_products.append({
            "product_id": product_id,
            "qty": qty,
            "cp": cp,
            "mrp": mrp,
            "expiry": expiry,
            "total": total,
            "tran_group_id": tran_group_id,
        })

    if not normalized_products:
        return

    # =====================================================
    # WEIGHTS
    # =====================================================

    weights = []

    for product in normalized_products:

        total = float(
            product["total"] or 0
        )

        weights.append(total)

    # =====================================================
    # ALLOCATE AMOUNTS
    # =====================================================

    discounts = allocate_amount(
        discount,
        weights
    )

    receives = allocate_amount(
        receive,
        weights
    )

    payments = allocate_amount(
        payment,
        weights
    )

    dues = allocate_amount(
        due,
        weights
    )

    # =====================================================
    # DETAILS DATA
    # =====================================================

    details_data = []

    for index, product in enumerate(
        normalized_products
    ):

        product_id = product["product_id"]

        qty = product["qty"] or 1

        cp = product["cp"] or 0

        mrp = product["mrp"] or 0

        expiry = product["expiry"]

        total = float(
            product["total"] or 0
        )

        tran_group_id = (
            product["tran_group_id"]
        )

        net_line = max(
            total
            - float(
                discounts[index] or 0
            ),
            0
        )

        details_data.append([
            tran_id,
            tran_type,
            payment_method,
            invoice_ref,

            location_id,
            tran_type_with,
            user_id,
            tran_by,

            product_id,
            tran_group_id,

            1,
            qty,
            0,
            0,

            0,

            total,
            net_line,

            cp,
            mrp,
            expiry,

            store_id,
            tran_date,
            status,

            discounts[index],
            receives[index],
            payments[index],
            dues[index],

            sr_id,
        ])

    # =====================================================
    # INSERT DETAILS
    # =====================================================

    query = """
        INSERT INTO transaction__details
        (
            tran_id,
            tran_type,
            tran_method,
            invoice_ref,

            loc_id,
            tran_type_with,
            tran_user,
            tran_by,

            tran_head_id,
            tran_groupe_id,

            quantity_actual,
            quantity,
            quantity_issue,
            quantity_return,

            unit_id,

            amount,
            tot_amount,

            cp,
            mrp,
            expiry_date,

            store_id,
            tran_date,
            status,

            discount,
            receive,
            payment,
            due,

            sr_id
        )

        VALUES
        (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s,
            %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s
        )
    """

    with connection.cursor() as cursor:

        cursor.executemany(
            query,
            details_data
        )


# =========================================================
# SAVE HOTEL PAYMENT
# =========================================================

@csrf_exempt
@transaction.atomic
def save_hotel_payment(request):

    if request.method != "POST":

        return JsonResponse({
            "success": False,
            "message":
                "Invalid request method"
        }, status=405)

    try:

        # =================================================
        # JSON DATA
        # =================================================

        data = json.loads(
            request.body
        )

        print(
            "HOTEL PAYMENT DATA >>>",
            data
        )

        # =================================================
        # EDIT ID
        # =================================================

        edit_id = (
            data.get("edit_id")
            or data.get("id")
        )

        # =================================================
        # TRANSACTION BY
        # =================================================

        tran_by = (
            get_transaction_user(
                request
            )
        )

        # =================================================
        # LOCATION
        # =================================================

        location_id = (
            data.get("location")
            or data.get("location_id")
            or None
        )

        # =================================================
        # STORE
        # =================================================

        store_id = (
            data.get("store")
            or data.get("store_id")
            or None
        )

        # =================================================
        # PAYMENT METHOD
        # =================================================

        payment_method = (
            data.get("payment_method")
            or data.get("tran_method")
            or "Both"
        )

        # =================================================
        # TRANSACTION WITH
        # =================================================

        tran_type_with = (
            data.get("tran_type_with")
            or data.get("transaction_with")
        )

        # Frontend না পাঠালে Guest automatically
        if not tran_type_with:

            guest_meta = (
                get_guest_transaction_with()
            )

            if guest_meta:
                tran_type_with = (
                    guest_meta["id"]
                )

        if not tran_type_with:

            return JsonResponse({
                "success": False,
                "message":
                    "Guest Transaction With not found"
            }, status=400)

        # =================================================
        # GUEST
        # =================================================

        guest_value = (
            data.get("guest_id")
            or data.get("guest")
            or data.get(
                "transaction_with_user"
            )
            or data.get("user_id")
            or data.get("tran_user")
        )

        if not guest_value:

            return JsonResponse({
                "success": False,
                "message":
                    "Please select Guest"
            }, status=400)

        guest = get_guest_info(
            guest_value
        )

        if not guest:

            return JsonResponse({
                "success": False,
                "message":
                    "Guest not found"
            }, status=400)

        # IMPORTANT
        # transaction table e custom user_id save
        user_id = guest["user_id"]

        user_name = (
            guest["user_name"]
            or ""
        )

        # =================================================
        # SR
        # =================================================

        referred_sr_id = (
            data.get("referred_sr_id")
            or data.get("sr_id")
        )

        sr_id = get_sr_custom_id(
            referred_sr_id
        )

        # =================================================
        # AMOUNT
        # =================================================

        bill_amount = float(
            data.get("bill_amount")
            or 0
        )

        discount = float(
            data.get("discount")
            or 0
        )

        net_amount = float(
            data.get("net_amount")
            or (
                bill_amount
                - discount
            )
        )

        receive = float(
            data.get("receive")
            or data.get("advance")
            or 0
        )

        payment = float(
            data.get("payment")
            or 0
        )

        due = float(
            data.get("due")
            or (
                net_amount
                - receive
                - payment
            )
        )

        if due < 0:
            due = 0

        # =================================================
        # DATE
        # =================================================

        tran_date = (
            data.get("tran_date")
            or data.get("date")
        )

        if tran_date:

            try:

                tran_date = datetime.combine(
                    datetime.strptime(
                        tran_date,
                        "%Y-%m-%d"
                    ).date(),

                    timezone.localtime().time()
                )

            except Exception:

                tran_date = (
                    timezone.localtime()
                )

        else:

            tran_date = (
                timezone.localtime()
            )

        # =================================================
        # PRODUCTS / HOTEL SERVICES
        # =================================================

        products = (
            data.get("products")
            or data.get("services")
            or []
        )

        status = int(
            data.get("status")
            or 1
        )

        tran_type = (
            HOTEL_TRAN_TYPE
        )

        # =================================================
        # EDIT MODE
        # =================================================

        if edit_id:

            with connection.cursor() as cursor:

                cursor.execute("""
                    SELECT
                        tran_id,
                        COALESCE(
                            invoice_ref,
                            tran_id
                        )

                    FROM transaction__mains

                    WHERE id = %s

                    AND tran_type = %s

                    LIMIT 1
                """, [
                    edit_id,
                    HOTEL_TRAN_TYPE
                ])

                edit_row = (
                    cursor.fetchone()
                )

                if not edit_row:

                    return JsonResponse({
                        "success": False,
                        "message":
                            "Hotel transaction not found"
                    }, status=404)

                tran_id = edit_row[0]

                invoice_ref = (
                    edit_row[1]
                    or tran_id
                )

                cursor.execute("""
                    UPDATE transaction__mains

                    SET
                        tran_method = %s,

                        invoice_ref = %s,

                        loc_id = %s,

                        tran_type_with = %s,

                        tran_user = %s,

                        tran_by = %s,

                        user_name = %s,

                        store_id = %s,

                        tran_date = %s,

                        status = %s,

                        bill_amount = %s,

                        discount = %s,

                        net_amount = %s,

                        receive = %s,

                        payment = %s,

                        due = %s,

                        sr_id = %s,

                        updated_at = NOW()

                    WHERE id = %s

                    AND tran_type = %s
                """, [
                    payment_method,
                    invoice_ref,
                    location_id,
                    tran_type_with,
                    user_id,
                    tran_by,
                    user_name,
                    store_id,
                    tran_date,
                    status,
                    bill_amount,
                    discount,
                    net_amount,
                    receive,
                    payment,
                    due,
                    sr_id,
                    edit_id,
                    HOTEL_TRAN_TYPE
                ])

                cursor.execute("""
                    DELETE
                    FROM transaction__details
                    WHERE tran_id = %s
                """, [tran_id])

            insert_hotel_detail_rows(
                products=products,

                tran_id=tran_id,

                tran_type=tran_type,

                payment_method=
                    payment_method,

                invoice_ref=
                    invoice_ref,

                location_id=
                    location_id,

                tran_type_with=
                    tran_type_with,

                user_id=
                    user_id,

                tran_by=
                    tran_by,

                store_id=
                    store_id,

                tran_date=
                    tran_date,

                status=
                    status,

                discount=
                    discount,

                receive=
                    receive,

                payment=
                    payment,

                due=
                    due,

                sr_id=
                    sr_id,
            )

            return JsonResponse({
                "success": True,
                "updated": True,

                "tran_id":
                    tran_id,

                "invoice_ref":
                    invoice_ref,

                "invoice":
                    invoice_ref,

                "guest_id":
                    guest["id"],

                "guest_user_id":
                    guest["user_id"],

                "guest_name":
                    guest["user_name"],

                "tran_by":
                    tran_by
            })

        # =================================================
        # NEW TRANSACTION
        # =================================================

        tran_id = (
            generate_hotel_transaction_id()
        )

        invoice_ref = tran_id

        # =================================================
        # INSERT MAIN
        # =================================================

        with connection.cursor() as cursor:

            cursor.execute("""
                INSERT INTO transaction__mains
                (
                    tran_id,
                    tran_type,
                    tran_method,
                    invoice_ref,

                    loc_id,
                    tran_type_with,
                    tran_user,
                    tran_by,
                    user_name,

                    store_id,
                    tran_date,
                    status,

                    bill_amount,
                    discount,
                    net_amount,

                    receive,
                    payment,
                    due,

                    sr_id
                )

                VALUES
                (
                    %s, %s, %s, %s,

                    %s, %s, %s, %s, %s,

                    %s, %s, %s,

                    %s, %s, %s,

                    %s, %s, %s,

                    %s
                )
            """, [
                tran_id,
                tran_type,
                payment_method,
                invoice_ref,

                location_id,
                tran_type_with,
                user_id,
                tran_by,
                user_name,

                store_id,
                tran_date,
                status,

                bill_amount,
                discount,
                net_amount,

                receive,
                payment,
                due,

                sr_id
            ])

        # =================================================
        # INSERT DETAILS
        # =================================================

        insert_hotel_detail_rows(
            products=products,

            tran_id=tran_id,

            tran_type=tran_type,

            payment_method=
                payment_method,

            invoice_ref=
                invoice_ref,

            location_id=
                location_id,

            tran_type_with=
                tran_type_with,

            user_id=
                user_id,

            tran_by=
                tran_by,

            store_id=
                store_id,

            tran_date=
                tran_date,

            status=
                status,

            discount=
                discount,

            receive=
                receive,

            payment=
                payment,

            due=
                due,

            sr_id=
                sr_id,
        )

        return JsonResponse({
            "success": True,

            "tran_id":
                tran_id,

            "invoice_ref":
                invoice_ref,

            "invoice":
                invoice_ref,

            "guest_id":
                guest["id"],

            "guest_user_id":
                guest["user_id"],

            "guest_name":
                guest["user_name"],

            "tran_by":
                tran_by
        })

    except Exception as e:

        print(
            "HOTEL PAYMENT SAVE ERROR"
        )

        traceback.print_exc()

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# =========================================================
# HOTEL PAYMENT LIST LOAD
# =========================================================

def hotel_payment_list_load(request):

    q = (
        request.GET.get("q")
        or ""
    ).strip()

    start_date = (
        request.GET.get("start_date")
        or ""
    ).strip()

    end_date = (
        request.GET.get("end_date")
        or ""
    ).strip()

    status = (
        request.GET.get("status")
        or ""
    ).strip()

    guest_id = (
        request.GET.get("guest_id")
        or ""
    ).strip()

    sr_id = (
        request.GET.get("sr_id")
        or ""
    ).strip()

    tran_by = (
        request.GET.get("tran_by")
        or ""
    ).strip()

    try:
        offset = int(
            request.GET.get(
                "offset",
                0
            )
        )

    except Exception:
        offset = 0

    try:
        limit = int(
            request.GET.get(
                "limit",
                50
            )
        )

    except Exception:
        limit = 50

    if limit <= 0:
        limit = 50

    if limit > 500:
        limit = 500

    sql = """
        SELECT
            m.id,

            m.tran_id,

            COALESCE(
                m.invoice_ref,
                ''
            ) AS invoice_ref,

            DATE_FORMAT(
                m.tran_date,
                '%%Y-%%m-%%d'
            ) AS tran_date,

            m.tran_type,

            COALESCE(
                tw.tran_with_name,
                ''
            ) AS transaction_with,

            m.tran_user,

            COALESCE(
                u.user_name,
                m.user_name,
                ''
            ) AS guest_name,

            COALESCE(
                u.user_phone,
                ''
            ) AS guest_phone,

            COALESCE(
                m.tran_by,
                ''
            ) AS tran_by,

            COALESCE(
                sr.name,
                ''
            ) AS sr_name,

            COALESCE(
                m.bill_amount,
                0
            ) AS bill_amount,

            COALESCE(
                m.discount,
                0
            ) AS discount,

            COALESCE(
                m.net_amount,
                0
            ) AS net_amount,

            COALESCE(
                m.receive,
                0
            ) AS receive,

            COALESCE(
                m.payment,
                0
            ) AS payment,

            COALESCE(
                m.due_col,
                0
            ) AS due_col,

            COALESCE(
                m.due_disc,
                0
            ) AS due_disc,

            COALESCE(
                m.due,
                0
            ) AS due,

            m.status

        FROM transaction__mains m

        LEFT JOIN transaction__withs tw
            ON tw.id = m.tran_type_with

        LEFT JOIN user__infos u
            ON (
                u.user_id = m.tran_user
                OR
                CAST(u.id AS CHAR)
                    = m.tran_user
            )

        LEFT JOIN item__sr_agents sr
            ON
                sr.custom_sr_id
                    COLLATE utf8mb4_unicode_ci
                =
                m.sr_id
                    COLLATE utf8mb4_unicode_ci

        WHERE m.tran_type = %s
    """

    params = [
        HOTEL_TRAN_TYPE
    ]

    # =====================================================
    # SEARCH
    # =====================================================

    if q:

        sql += """
            AND (
                m.tran_id LIKE %s

                OR m.invoice_ref LIKE %s

                OR m.tran_user LIKE %s

                OR m.user_name LIKE %s

                OR u.user_name LIKE %s

                OR u.user_phone LIKE %s
            )
        """

        like = f"%{q}%"

        params.extend([
            like,
            like,
            like,
            like,
            like,
            like
        ])

    # =====================================================
    # STATUS
    # =====================================================

    if status != "":

        sql += """
            AND m.status = %s
        """

        params.append(
            status
        )

    # =====================================================
    # GUEST
    # =====================================================

    if guest_id:

        guest = get_guest_info(
            guest_id
        )

        if guest:

            sql += """
                AND m.tran_user = %s
            """

            params.append(
                guest["user_id"]
            )

    # =====================================================
    # SR
    # =====================================================

    if sr_id:

        final_sr_id = (
            get_sr_custom_id(
                sr_id
            )
        )

        if final_sr_id:

            sql += """
                AND m.sr_id = %s
            """

            params.append(
                final_sr_id
            )

    # =====================================================
    # TRAN BY
    # =====================================================

    if tran_by:

        sql += """
            AND m.tran_by = %s
        """

        params.append(
            tran_by
        )

    # =====================================================
    # DATE
    # =====================================================

    if start_date:

        sql += """
            AND DATE(m.tran_date) >= %s
        """

        params.append(
            start_date
        )

    if end_date:

        sql += """
            AND DATE(m.tran_date) <= %s
        """

        params.append(
            end_date
        )

    # =====================================================
    # ORDER / LIMIT
    # =====================================================

    sql += """
        ORDER BY m.id DESC

        LIMIT %s OFFSET %s
    """

    params.extend([
        limit,
        offset
    ])

    # =====================================================
    # TOTAL DUE
    # =====================================================

    total_sql = """
        SELECT
            COALESCE(
                SUM(m.due),
                0
            )

        FROM transaction__mains m

        WHERE m.tran_type = %s
    """

    total_params = [
        HOTEL_TRAN_TYPE
    ]

    with connection.cursor() as cursor:

        cursor.execute(
            sql,
            params
        )

        data = dictfetchall(
            cursor
        )

        cursor.execute(
            total_sql,
            total_params
        )

        total_due = (
            cursor.fetchone()[0]
            or 0
        )

    return JsonResponse({
        "results": data,
        "total_due": float(
            total_due
        )
    })


# =========================================================
# EDIT HOTEL PAYMENT
# =========================================================

def edit_hotel_payment_page(
    request,
    id
):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                m.id,
                m.tran_id,
                m.invoice_ref,

                m.loc_id,
                m.store_id,

                m.tran_type,
                m.tran_method,

                m.tran_type_with,

                tw.tran_method
                    AS tran_with_method,

                COALESCE(
                    CAST(u.id AS CHAR),
                    m.tran_user
                ) AS tran_user,

                COALESCE(
                    u.user_name,
                    m.user_name,
                    ''
                ) AS guest_name,

                COALESCE(
                    u.user_phone,
                    ''
                ) AS guest_phone,

                COALESCE(
                    u.address,
                    ''
                ) AS guest_address,

                COALESCE(
                    loc.division,
                    ''
                ) AS location_name,

                m.bill_amount,
                m.discount,
                m.net_amount,

                m.receive,
                m.payment,

                m.due_col,
                m.due_disc,
                m.due,

                m.tran_date,

                m.sr_id,

                COALESCE(
                    sr.name,
                    ''
                ) AS sr_name

            FROM transaction__mains m

            LEFT JOIN transaction__withs tw
                ON tw.id =
                    m.tran_type_with

            LEFT JOIN user__infos u
                ON (
                    u.user_id =
                        m.tran_user

                    OR

                    CAST(
                        u.id AS CHAR
                    ) =
                        m.tran_user
                )

            LEFT JOIN location__infos loc
                ON loc.id =
                    m.loc_id

            LEFT JOIN item__sr_agents sr
                ON
                    sr.custom_sr_id
                        COLLATE utf8mb4_unicode_ci
                    =
                    m.sr_id
                        COLLATE utf8mb4_unicode_ci

            WHERE
                m.id = %s

                AND m.tran_type = %s

            LIMIT 1
        """, [
            id,
            HOTEL_TRAN_TYPE
        ])

        rows = dictfetchall(
            cursor
        )

        transaction_data = (
            rows[0]
            if rows
            else None
        )

        if not transaction_data:

            return redirect(
                "hotel_payment_list"
            )

        cursor.execute("""
            SELECT
                d.id,

                d.tran_head_id
                    AS product_id,

                COALESCE(
                    h.tran_head_name,
                    ''
                ) AS product_name,

                d.quantity,

                d.cp,
                d.mrp,

                d.tot_amount
                    AS total,

                d.expiry_date,

                COALESCE(
                    d.tran_groupe_id,
                    h.groupe_id
                ) AS tran_groupe_id,

                g.tran_method
                    AS tran_group_method

            FROM transaction__details d

            LEFT JOIN transaction__heads h
                ON h.id =
                    d.tran_head_id

            LEFT JOIN transaction__groupes g
                ON g.id =
                    COALESCE(
                        d.tran_groupe_id,
                        h.groupe_id
                    )

            WHERE
                d.tran_id = %s

            ORDER BY d.id ASC
        """, [
            transaction_data[
                "tran_id"
            ]
        ])

        details = dictfetchall(
            cursor
        )

    transaction_data[
        "tran_group_id"
    ] = (
        details[0].get(
            "tran_groupe_id"
        )
        if details
        else ""
    )

    transaction_data[
        "tran_group_method"
    ] = (
        details[0].get(
            "tran_group_method"
        )
        if details
        else ""
    )

    if transaction_data.get(
        "tran_date"
    ):

        transaction_data[
            "tran_date"
        ] = transaction_data[
            "tran_date"
        ].strftime(
            "%Y-%m-%d"
        )

    for item in details:

        if item.get(
            "expiry_date"
        ):

            item[
                "expiry_date"
            ] = item[
                "expiry_date"
            ].strftime(
                "%Y-%m-%d"
            )

    return render(
        request,
        "hotel/transaction.html",
        {
            "edit_transaction":
                transaction_data,

            "edit_details":
                details,

            "edit_transaction_json":
                json.dumps(
                    transaction_data,
                    default=str
                ),

            "edit_details_json":
                json.dumps(
                    details,
                    default=str
                ),

            "edit_mode":
                True,

            "fixed_location_id":
                transaction_data.get(
                    "loc_id"
                )
                or "",

            "fixed_location_name":
                transaction_data.get(
                    "location_name"
                )
                or "",
        }
    )


# =========================================================
# HOTEL PAYMENT FORM
# =========================================================

def hotel_payment_form(
    request,
    id
):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                m.id,

                m.tran_id,

                m.invoice_ref,

                m.tran_date,

                m.tran_type_with,

                m.tran_user,

                COALESCE(
                    u.user_name,
                    m.user_name,
                    ''
                ) AS guest_name,

                COALESCE(
                    u.user_phone,
                    ''
                ) AS guest_phone,

                COALESCE(
                    u.address,
                    ''
                ) AS guest_address,

                m.bill_amount,

                m.discount,

                m.net_amount,

                m.payment,

                m.receive,

                m.due_col,

                m.due_disc,

                m.due

            FROM transaction__mains m

            LEFT JOIN user__infos u
                ON (
                    u.user_id =
                        m.tran_user

                    OR

                    CAST(
                        u.id AS CHAR
                    ) =
                        m.tran_user
                )

            WHERE
                m.id = %s

                AND m.tran_type = %s

            LIMIT 1
        """, [
            id,
            HOTEL_TRAN_TYPE
        ])

        rows = dictfetchall(
            cursor
        )

    transaction_data = (
        rows[0]
        if rows
        else None
    )

    return render(
        request,
        "hotel/party_payment/payment_form.html",
        {
            "transaction":
                transaction_data
        }
    )


# =========================================================
# PARTY PAYMENT LIST
# =========================================================

def hotel_party_payment_list(
    request
):

    return render(
        request,
        "hotel/party_payment/payment_list.html"
    )


def hotel_party_payment_list_load(
    request
):

    return hotel_payment_list_load(
        request
    )


def hotel_party_payment_form(
    request,
    id
):

    return hotel_payment_form(
        request,
        id
    )


# =========================================================
# PROCESS DUE PAYMENT
# =========================================================

@csrf_exempt
@transaction.atomic
def process_hotel_payment(
    request,
    id
):

    if request.method != "POST":

        return JsonResponse({
            "success": False,
            "error":
                "Invalid request method"
        }, status=405)

    try:

        pay_amount = float(
            request.POST.get(
                "pay_amount",
                0
            )
            or 0
        )

        due_discount = float(
            request.POST.get(
                "due_discount",
                0
            )
            or 0
        )

    except Exception:

        return JsonResponse({
            "success": False,
            "error":
                "Invalid amount"
        }, status=400)

    if (
        pay_amount <= 0
        and due_discount <= 0
    ):

        return JsonResponse({
            "success": False,
            "error":
                "Payment or discount must be greater than 0"
        }, status=400)

    with connection.cursor() as cursor:

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
                due_disc

            FROM transaction__mains

            WHERE
                id = %s

                AND tran_type = %s

            LIMIT 1
        """, [
            id,
            HOTEL_TRAN_TYPE
        ])

        row = cursor.fetchone()

        if not row:

            return JsonResponse({
                "success": False,
                "error":
                    "Hotel transaction not found"
            }, status=404)

        current_due = float(
            row[17]
            or 0
        )

        old_due_col = float(
            row[18]
            or 0
        )

        old_due_disc = float(
            row[19]
            or 0
        )

        total_adjustment = (
            pay_amount
            + due_discount
        )

        if (
            total_adjustment
            > current_due
        ):

            return JsonResponse({
                "success": False,

                "error":
                    "Payment + Discount cannot be greater than current due"
            }, status=400)

        new_due_col = (
            old_due_col
            + pay_amount
        )

        new_due_disc = (
            old_due_disc
            + due_discount
        )

        new_due = (
            current_due
            - total_adjustment
        )

        cursor.execute("""
            UPDATE transaction__mains

            SET
                due_col = %s,

                due_disc = %s,

                due = %s,

                updated_at = NOW()

            WHERE id = %s

            AND tran_type = %s
        """, [
            new_due_col,
            new_due_disc,
            new_due,
            id,
            HOTEL_TRAN_TYPE
        ])

    return JsonResponse({
        "success": True,

        "pay_amount":
            pay_amount,

        "due_discount":
            due_discount,

        "due_col":
            new_due_col,

        "due_disc":
            new_due_disc,

        "due":
            new_due
    })

#-------------privew------------
# =========================================================
# HOTEL TRANSACTION PREVIEW
# =========================================================

def hotel_party_payment_preview(request, transaction_id):

    try:

        cursor = connection.cursor()


        # ==============================
        # MAIN TRANSACTION + GUEST + SR
        # ==============================

        cursor.execute("""
            SELECT
                tm.id,
                tm.tran_id,
                tm.invoice_ref,
                tm.tran_date,

                tm.tran_user,

                hg.guest_id,
                hg.guest_name,
                hg.mobile,
                hg.address,
                hg.gender,

                sr.custom_sr_id,
                sr.name,

                tm.bill_amount,
                tm.discount,
                tm.net_amount,
                tm.receive,
                tm.payment,
                tm.due_col,
                tm.due_disc,
                tm.due

            FROM transaction__mains tm

            LEFT JOIN hotel_guests_info hg
                ON hg.guest_id = tm.tran_user

            LEFT JOIN item__sr_agents sr
                ON sr.custom_sr_id = tm.sr_id

            WHERE tm.id = %s
            AND tm.tran_type = %s

            LIMIT 1

        """, [
            transaction_id,
            HOTEL_TRAN_TYPE
        ])


        row = cursor.fetchone()


        if not row:

            return JsonResponse({
                "success": False,
                "error": "Hotel transaction not found"
            }, status=404)


        # ==============================
        # TRANSACTION DATA
        # ==============================

        transaction_data = {

            "id": row[0],

            "tran_id": row[1],

            "invoice_ref": row[2] or row[1],

            "tran_date": str(row[3]) if row[3] else "",


            # GUEST
            "guest_id": row[5] or row[4] or "",

            "guest_name": row[6] or "",

            "guest_phone": row[7] or "",

            "guest_address": row[8] or "",

            "guest_gender": row[9] or "",


            # SR
            "sr_id": row[10] or "",

            "sr_name": row[11] or "",


            # AMOUNT
            "bill_amount": row[12] or 0,

            "discount": row[13] or 0,

            "net_amount": row[14] or 0,

            "receive": row[15] or 0,

            "payment": row[16] or 0,

            "due_col": row[17] or 0,

            "due_disc": row[18] or 0,

            "due": row[19] or 0
        }


        # ==============================
        # PRODUCT / SERVICE DETAILS
        # ==============================

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

        """, [
            transaction_data["tran_id"]
        ])


        rows = cursor.fetchall()


        details = []


        for item in rows:

            details.append({

                "product_id": item[0],

                "product_name": item[1] or "",

                "quantity": item[2] or 0,

                "mrp": item[3] or 0,

                "total": item[4] or 0

            })


        # ==============================
        # RESPONSE
        # ==============================

        return JsonResponse({

            "success": True,

            "transaction": transaction_data,

            "details": details

        })


    except Exception as e:

        print(
            "HOTEL PREVIEW ERROR >>>",
            str(e)
        )

        return JsonResponse({

            "success": False,

            "error": str(e)

        }, status=500)