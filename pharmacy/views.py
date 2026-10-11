from datetime import timezone
import json
from django.http import JsonResponse
from django.forms import model_to_dict
from django.shortcuts import get_object_or_404, redirect, render
from .models import TransactionHeads, Stores, ItemManufacturers, LocationInfos, TransactionMainsTemps, TransactionDetailsTemps, TransactionMainHeads
from django.core.paginator import Paginator
from django.db import connection
from django.db import transaction
from django.db.models import F, Q
from django.db.models import Count, Case, When, IntegerField, Q
from datetime import datetime
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.payment_mode import set_payment_mode
from decimal import ROUND_HALF_UP
from core.amount_allocation import allocate_amount


def dictfetchall(cursor):
    """Return all rows from a cursor as a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


_allocate_amount = allocate_amount
# def medicine_list(request):
#     products = TransactionHeads.objects.all().defer('added_at', 'updated_at', 'expiry_date').order_by('id')
#     paginator = Paginator(products, 10)  # 10 per page
#     page_number = request.GET.get('page', 1)
#     page_obj = paginator.get_page(page_number)
    
#     return render(request, 'pharmacy/medicine_list.html', {
#         'products': page_obj
# })

def medicine_list(request):
    # 🔹 Get filters from GET parameters
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # 🔹 Base queryset: only PURCHASE transactions
    data = TransactionMainsTemps.objects.all().order_by('tran_id')
    status_filter = request.GET.get('status')

    if status_filter in ['1', '0']:
        data = data.filter(status=int(status_filter))

    if search:
        data = data.filter(user_name__icontains=search)

    if start_date:
        data = data.filter(tran_date__date__gte=start_date)
    if end_date:
        data = data.filter(tran_date__date__lte=end_date)

    # 🔹 Pagination
    per_page = int(request.GET.get("per_page", 15))
    paginator = Paginator(data, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 🔹 Per-page options for dropdown
    per_page_options = [15, 30, 50, 100, 500]
    stores = Stores.objects.all()
    context = {
        'data': page_obj,              # paginated data
        'status_filter': status_filter,
        'search': search,
        'start_date': start_date,
        'end_date': end_date,
        'per_page': per_page,
        'per_page_options': per_page_options,
        'paginator': paginator,
        'page_number': page_number,
        'stores': stores,
    }

    return render(request, 'pharmacy/medicine_list.html', context)



def medicine_add(request):
    # Add Medicine modal/page
    return render(request, 'pharmacy/add.html')


def product_search(request):
    q = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0))
    tran_group_id = request.GET.get('tran_group_id') or 6
    limit = 10

    # Fetch the limited product set first. Joining the catalog tables before
    # LIMIT makes this endpoint take several seconds on the current database.
    sql = """
        SELECT id, tran_head_name AS name, cp, mrp, manufacturer_id,
               form_id, category_id, quantity
        FROM transaction__heads
        WHERE groupe_id = %s
    """
    params = [tran_group_id]
    if q:
        sql += " AND tran_head_name LIKE %s"
        params.append(f"{q}%")
    sql += " ORDER BY id ASC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = dictfetchall(cursor)

        ids = {
            key: {row[key] for row in rows if row.get(key) is not None}
            for key in ("manufacturer_id", "form_id", "category_id")
        }

        def load_names(table, name_column, values):
            if not values:
                return {}
            placeholders = ",".join(["%s"] * len(values))
            cursor.execute(
                f"SELECT id, {name_column} FROM {table} WHERE id IN ({placeholders})",
                list(values),
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

        manufacturers = load_names("item__manufacturers", "manufacturer_name", ids["manufacturer_id"])
        forms = load_names("item__forms", "form_name", ids["form_id"])
        categories = load_names("item__categories", "category_name", ids["category_id"])

    for row in rows:
        row["manufacturer"] = manufacturers.get(row.pop("manufacturer_id"), "")
        row["form"] = forms.get(row.pop("form_id"), "")
        row["category_name"] = categories.get(row.pop("category_id"), "")

    return JsonResponse({'results': rows})

def purchase_list(request):
    # return render(request, 'pharmacy/medicine_list.html')
    return render(request, 'pharmacy/purchase_list.html', {
        'page_id': request.GET.get('page_id') or '1020300016',
    })

def issue_list(request):
    return render(request, 'pharmacy/issue_list.html')

def purchase_list_load(request):
    q = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    offset = int(request.GET.get('offset', 0))
    limit = 50

    cursor = connection.cursor()

    # If no search text → show all
    if q:
        # Search by name startswith
        # sql = """
        #     SELECT 
        #         m.id,
        #         m.tran_id AS tran_id,
        #         m.tran_date AS tran_date,
        #         m.tran_user AS tran_supplier,
        #         m.bill_amount AS bill_total,
        #         m.discount AS discount,
        #         m.net_amount AS net_total,
        #         m.receive AS advance,
        #         m.due_col AS due_collection,
        #         m.due_disc AS due_discount,
        #         m.due AS due
        #     FROM transaction__mains m
        #     ORDER BY m.id ASC
        #     LIMIT %s OFFSET %s
        # """
        # params = [limit, offset]        
        # # params = [f"{q}%", 6, limit, offset]  
              
        # sql = """
        #     SELECT 
        #         m.id,
        #         m.tran_id AS tran_id,
        #         m.tran_date AS tran_date,
        #         m.tran_user AS tran_supplier,
        #         m.bill_amount AS bill_total,
        #         m.discount AS discount,
        #         m.net_amount AS net_total,
        #         m.receive AS advance,
        #         m.due_col AS due_collection,
        #         m.due_disc AS due_discount,
        #         m.due AS due
        #     FROM transaction__mains m
        #     WHERE (%s IS NULL OR m.tran_date >= %s)
        #     AND (%s IS NULL OR m.tran_date <= %s)
        #     ORDER BY m.id
        #     LIMIT %s OFFSET %s
        # """
        # params = [start_date, start_date, end_date, end_date, limit, offset]

        sql = """
            SELECT 
                m.id,
                m.tran_id AS tran_id,
                m.tran_date AS tran_date,
                m.tran_user AS tran_supplier,
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

        # date filter
        if start_date:
            sql += " AND DATE(m.tran_date) >= %s"
            params.append(start_date)

        if end_date:
            sql += " AND DATE(m.tran_date) <= %s"
            params.append(end_date)

        sql += " ORDER BY m.id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])        


    else:
        # sql = """
        #     SELECT 
        #         m.id,
        #         m.tran_id AS tran_id,
        #         m.tran_date AS tran_date,
        #         m.tran_user AS tran_supplier,
        #         m.bill_amount AS bill_total,
        #         m.discount AS discount,
        #         m.net_amount AS net_total,
        #         m.receive AS advance,
        #         m.due_col AS due_collection,
        #         m.due_disc AS due_discount,
        #         m.due AS due
        #     FROM transaction__mains m
        #     ORDER BY m.id
        #     LIMIT %s OFFSET %s
        # """
        # params = [limit, offset]

        sql = """
            SELECT 
                m.id,
                m.tran_id AS tran_id,
                m.tran_date AS tran_date,
                m.tran_user AS tran_supplier,
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

        # date filter
        if start_date:
            sql += " AND DATE(m.tran_date) >= %s"
            params.append(start_date)

        if end_date:
            sql += " AND DATE(m.tran_date) <= %s"
            params.append(end_date)

        sql += " ORDER BY m.id ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

    cursor.execute(sql, params)
    data = dictfetchall(cursor)

    print("SQL",sql)
    return JsonResponse({'results': data})


def add_medicine(request):
    # Fetch only active stores (status=1)
    stores = Stores.objects.filter(status=1).order_by('store_name')
    return render(request, 'pharmacy/add.html', {'stores': stores})

def get_stores(request):
    stores = Stores.objects.filter(status=1).order_by('store_name')
    data = [
        {"id": s.id, "name": s.store_name}
        for s in stores
    ]
    return JsonResponse({"stores": data})

def get_suppliers(request):
    # Status 1 er manufacturer fetch
    manufacturers = ItemManufacturers.objects.filter(status=1).order_by('manufacturer_name')
    data = [{"id": m.id, "name": m.manufacturer_name} for m in manufacturers]
    return JsonResponse({"suppliers": data})

def get_divisions(request):
    # Only active locations (status=1)    
    divisions = LocationInfos.objects.filter(status=1).order_by('division')
    data = [{"id": d.id, "name": d.division} for d in divisions]
    return JsonResponse({"divisions": data})


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

def get_supplier_combo(request):

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

def get_store_combo(request):

    cursor = connection.cursor()

    sql = """
        SELECT
        s.id AS id,
        s.store_name
        FROM stores s
        ORDER BY s.store_name;
    """
    params = []

    cursor.execute(sql, params)
    # data = dictfetchall(cursor)

    # data = [
    #     {"id": s.id, "store_name": s.store_name}
    #     for s in cursor.fetchall()
    # ]    

    data  = [
        {
            "id": row[0],
            "store_name": row[1]
        }
        for row in cursor.fetchall()
    ]    
    print("DEBUG",data)

    return JsonResponse({
        "store_combo": data
    })


def add_purchase_page(request):
    return render(request, 'pharmacy/add_4.html', {
        'page_id': request.GET.get('page_id') or '1020300016',
    })


def pharmacy_page_init(request):
    page_id = request.GET.get('page_id') or '1020300016'
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT location_id, company_id, tran_main_head_id,
                   user_tran_method, user_tran_with_id,
                   tran_method, tran_group_id
            FROM page_init
            WHERE page_id = %s
            LIMIT 1
        """, [page_id])
        row = cursor.fetchone()

    if not row:
        return JsonResponse({'page_init': {}})

    return JsonResponse({
        'page_init': {
            'location_id': row[0],
            'company_id': row[1],
            'tran_main_head_id': row[2],
            'user_tran_method': row[3],
            'user_tran_with_id': row[4],
            'tran_method': row[5],
            'tran_group_id': row[6],
        }
    })

def add_issue_page(request):
    return render(request, 'pharmacy/issue.html')

@csrf_exempt   # AJAX hole thakbe, na hole CSRF use koro
def create_transaction_temp(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request"}, status=405)

    try:
        with transaction.atomic():  # 🔑 ensures atomic DB operation

            # Generate new transaction ID
            last_tran = TransactionMainsTemps.objects.order_by('-id').first()
            last_number = int(last_tran.tran_id[3:]) if last_tran else 0
            new_number = last_number + 1
            tran_id = f"TRA{new_number:09d}"  # total 12 digits

            # Get POST data
            bill_amount = float(request.POST.get("bill_amount") or 0)
            discount = float(request.POST.get("discount") or 0)
            net_amount = float(request.POST.get("net_amount") or 0)
            payment = float(request.POST.get("payment") or 0)
            due = float(request.POST.get("due") or 0)
            store_id = request.POST.get("store_id")
            supplier = request.POST.get("supplier")
            tran_method = request.POST.get("tran_method")
            location_name = request.POST.get("location")

            # Validate store
            if not store_id:
                return JsonResponse({"success": False, "message": "Store required"}, status=400)
            store = Stores.objects.get(id=store_id)

            # Location
            location = LocationInfos.objects.filter(division__iexact=location_name).first()
            loc_id = location.id if location else None

            # Transaction type
            tran_type_obj = TransactionMainHeads.objects.filter(type_name__iexact="Pharmacy").first()
            if not tran_type_obj:
                return JsonResponse({"success": False, "message": "Invalid transaction type"}, status=400)
            tran_type = tran_type_obj.id

            # 🔹 TABLE 1: transaction_mains_temps
            main_tran = TransactionMainsTemps.objects.create(
                tran_id=tran_id,
                tran_type=tran_type,
                tran_method=tran_method,
                tran_user=supplier,
                store=store,
                loc_id=loc_id,
                tran_date=timezone.now(),
                status=1,
                invoice=bill_amount,
                bill_amount=bill_amount,
                discount=discount,
                net_amount=net_amount,
                payment=payment,
                due=due
            )

            # 🔹 TABLE 2: transaction_details_temp (empty product row)
            TransactionDetailsTemps.objects.create(
                tran_id=tran_id,
                tran_type=tran_type,
                tran_method=tran_method,
                invoice=bill_amount,
                tran_user=supplier,
                amount=bill_amount,
                discount=discount,
                receive=payment,
                payment=payment,
                due=due,
                store=store,
                status=1,
                tran_date=timezone.now(),
                # product fields set to null/defaults
                tran_head_id=None,
                quantity_actual=0,
                quantity=0,
                quantity_issue=0,
                quantity_return=0,
                tot_amount=net_amount,
                cp=None,
                mrp=None
            )

            # Prepare response safely
            response_data = {
                "id": main_tran.id,
                "tran_id": main_tran.tran_id,
                "user_name": getattr(main_tran, 'user_name', supplier),
                "bill_amount": main_tran.bill_amount,
                "discount": main_tran.discount,
                "net_amount": main_tran.net_amount,
                "payment": main_tran.payment,
                "due": main_tran.due,
                "due_col": getattr(main_tran, 'due_col', 0),
                "due_disc": getattr(main_tran, 'due_disc', 0),
                "status": main_tran.status
            }

            return JsonResponse({"success": True, "tran_id": tran_id, "data": response_data})

    # except Stores.DoesNotExist:
    #     return JsonResponse({"success": False, "message": "Invalid store"}, status=400)
    except Exception as e:
        print("🔥 TRANSACTION ERROR:", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
# def test_tran_id_generation(request):
#         store = Stores.objects.first()  # any store for testing

#         tran_id = generate_tran_id("TRA")

#         TransactionMainsTemps.objects.create(
#             tran_id=tran_id,
#             tran_type = 1,
#             store=store,
#             loc_id=store.location_id,
#             tran_date=timezone.now(),
#             status=1,
#             discount=0
#         )

#         return JsonResponse({
#             "message": "Tran ID generated & saved successfully",
#             "tran_id": tran_id
#         })


def get_transaction(request, tran_id):
    try:
        # 🔹 Fetch main transaction
        main = get_object_or_404(TransactionMainsTemps, tran_id=tran_id)

        # 🔹 Supplier name from tran_user
        supplier_name = ""
        if main.tran_user:
            supplier = ItemManufacturers.objects.filter(id=main.tran_user).first()
            if supplier:
                supplier_name = supplier.manufacturer_name

        # 🔹 Store info
        store_name = main.store.store_name if main.store else ""
        store_id = main.store.id if main.store else None

        # 🔹 Location
        location_name = ""
        if main.loc_id:
            loc = LocationInfos.objects.filter(id=main.loc_id).first()
            if loc:
                location_name = loc.division

        # 🔹 Transaction details
        details_qs = TransactionDetailsTemps.objects.filter(tran_id=tran_id)
        details = []
        for d in details_qs:
            # Get product name
            product_name = ""
            if d.tran_head_id:
                product = TransactionHeads.objects.filter(id=d.tran_head_id).first()
                if product:
                    product_name = product.tran_head_name
            details.append({
                "id": d.id,
                "name": product_name or "Unknown Product",
                "qty": d.quantity or 0,
                "cp": d.cp or 0,
                "mrp": d.mrp or 0,
                "total": d.tot_amount or 0,
                "unit": "PCS"  # optional, or fetch from d.unit_id if needed
            })

        # 🔹 Response
        response = {
            "success": True,
            "data": {
                "tran_id": main.tran_id,
                "supplier": supplier_name,
                "store_id": store_id,
                "store_name": store_name,
                "location": location_name,
                "tran_method": main.tran_method,
                "tran_date": main.tran_date.date().strftime("%Y-%m-%d"),
                "bill_amount": main.bill_amount or 0,
                "discount": main.discount or 0,
                "net_amount": main.net_amount or 0,
                "payment": main.payment or 0,
                "due": main.due or 0,
                "details": details
            }
        }

        return JsonResponse(response)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})



# def get_temp_transaction(request, tran_id):
#     tran = TransactionMainsTemps.objects.get(id=tran_id)
#     medicines = tran.medicines.all().values("name","quantity","unit_price","total")

#     # fetch products from transaction__heads table
#     cursor = connection.cursor()
#     cursor.execute("SELECT tran_head_name AS name, '' AS generic_name, '' AS manufacture, '' AS form, quantity AS qty, cp, mrp FROM transaction__heads")
#     products = dictfetchall(cursor)

#     return JsonResponse({
#         "success": True,
#         "data": {
#             "location": tran.location,
#             "store_id": tran.store_id,
#             "date": tran.date,
#             "supplier_name": tran.supplier_name,
#             "payment_method": tran.tran_method,
#             "bill_amount": tran.bill_amount,
#             "discount": tran.discount,
#             "net_amount": tran.net_amount,
#             "payment": tran.payment,
#             "due": tran.due,
#             "medicines": list(medicines),
#             "products": products
#         }
#     })
    

    



# def get_temp_details(request, tran_id):
#     main = TransactionMainsTemps.objects.get(tran_id=tran_id)

#     items = TransactionDetailsTemps.objects.filter(tran_id=tran_id)

#     med_list = []
#     for i in items:
#         med_list.append({
#             "name": i.product_name,
#             "qty": i.qty,
#             "price": i.unit_price,
#             "total": i.total
#         })

#     return JsonResponse({
#         "tran_id": main.tran_id,
#         "store_id": main.store_id,
#         "location": main.loc_id,
#         "method": main.tran_method,
#         "bill_amount": main.bill_amount,
#         "discount": main.discount,
#         "net_amount": main.net_amount,
#         "payment": main.payment,
#         "due": main.due,
#         "medicines": med_list
#     })


@csrf_exempt  # AJAX POST

@transaction.atomic
def save_purchase(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request"}, status=405)

    try:
        data = json.loads(request.body)

        # ---- Form-level info ----
        store_id = data.get("store")
        location_id = data.get("location")
        tran_type_with = data.get("supplier")
        invoice = data.get("purchaseinvoice") or data.get("invoice")
        payment_method = data.get("payment_method")
        bill_amount = data.get("bill_amount") or 0
        discount = data.get("discount") or 0
        net_amount = data.get("net_amount") or 0
        receive = data.get("receive") or 0
        due = data.get("due") or 0
        # tran_date = data.get("tran_date") or timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        tran_date = data.get("tran_date")
        # Date & Time Both
        if tran_date:
            tran_date = datetime.combine(
                datetime.strptime(tran_date, "%Y-%m-%d").date(),
                timezone.localtime().time()
            )
        else:
            tran_date = timezone.localtime()
        
        # Only Date
        # if tran_date:
        #     tran_date = datetime.strptime(tran_date, "%Y-%m-%d")
        #     tran_date = timezone.make_aware(tran_date)
        # else:
        #     tran_date = timezone.now()

        print("tran_date from form:", tran_date)

        products = data.get("products", [])
        if not products:
            return JsonResponse({"success": False, "message": "No products selected"}, status=400)

        bill_amount = sum(float(row[5] or 0) for row in products)
        discount = float(discount or 0)
        net_amount = max(bill_amount - discount, 0)

        # ---- Generate transaction ID ----
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tran_id 
                FROM transaction__mains
                WHERE tran_id LIKE 'PHR%'
                ORDER BY tran_id DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()

            if row:
                last_number = int(row[0][3:])  # remove PHR
            else:
                last_number = 0

            phr_code = "PHR" + str(last_number + 1).zfill(9)
        # ---- END of Generate transaction ID ----

        tran_type = int(data.get("tran_type") or 6)
        page_id = data.get("page_id")
        page_init_user_method = ""
        page_init_method = ""
        if page_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT tran_main_head_id, user_tran_method, tran_method
                    FROM page_init
                    WHERE page_id = %s
                    LIMIT 1
                    """,
                    [page_id],
                )
                page_init_row = cursor.fetchone()
            if page_init_row and page_init_row[0]:
                tran_type = int(page_init_row[0])
            if page_init_row:
                page_init_user_method = str(page_init_row[1] or "").strip().lower()
                page_init_method = str(page_init_row[2] or "").strip().lower()

        # Page-init stores Receive/Payment in user_tran_method for Pharmacy
        # pages. Fall back to tran_method for pages configured that way.
        payment_mode = page_init_user_method
        if payment_mode not in {"receive", "payment"}:
            payment_mode = page_init_method
        if payment_mode not in {"receive", "payment"}:
            payment_mode = "payment"

        receive_amount = receive if payment_mode == "receive" else 0
        payment_amount = float(data.get("payment") or receive or 0) if payment_mode == "payment" else 0
        due = max(net_amount - (receive_amount or payment_amount), 0)
        status = 1

        # ---- Insert into transaction__mains ----
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO transaction__mains
                (tran_id, tran_type, tran_method, tran_type_with, store_id, 
                 loc_id, tran_date, status, invoice_ref, bill_amount, discount, net_amount,
                 receive, payment, due)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                phr_code, tran_type, payment_method, tran_type_with, store_id,
                location_id, tran_date, status, invoice, bill_amount, 
                discount, net_amount, receive_amount, payment_amount, due
            ])

        line_weights = [row[5] for row in products]
        receive_by_line = _allocate_amount(receive_amount, line_weights)
        payment_by_line = _allocate_amount(payment_amount, line_weights)
        due_by_line = _allocate_amount(due, line_weights)
        discount_by_line = _allocate_amount(discount, line_weights)

        # ---- Prepare details data using index-style access ----
        details_data = []

        update_query = """
        UPDATE transaction__heads
        SET cp = %s, mrp = %s
        WHERE id = %s
        """
        update_data = []
        
        for index, row in enumerate(products):
            details_data.append([
                # phr_code,         # tran_id
                # tran_type,        # tran_type_with
                # location_id,      # loc_id
                # store_id,         # store_id
                # tran_type_with,   # tran_user
                # row[0],           # tran_head_id
                # row[1],           # quantity_actual
                # row[1],           # quantity
                # 0,                # quantity_issue
                # 0,                # quantity_return   
                # row[4],           # cp
                # row[5],           # mrp
                # row[6],           # expiry_date
                # row[7],           # tot_amount                
                # tran_date,        # tran_date
                # status,           # status
                # discount,         # discount
                # receive,          # receive
                # receive,          # payment
                # due               # due

                phr_code,          # tran_id
                tran_type,        # tran_type_with
                payment_method,   # tran_method
                invoice,          # invoice
                location_id,      # loc_id
                tran_type_with,      # tran_user
                row[0],           # tran_head_id
                row[1],           # quantity_actual
                row[1],           # quantity
                0,                # quantity_issue
                0,                # quantity_return
                0,                # unit_id
                float(row[5] or 0), # amount (line bill)
                max(float(row[5] or 0) - float(discount_by_line[index]), 0), # tot_amount (line net)
                row[2],           # cp
                row[3],           # mrp
                row[4],           # expiry_date
                store_id,         # store_id
                tran_date,        # tran_date
                status,           # status
                discount_by_line[index],  # discount
                receive_by_line[index],   # receive
                payment_by_line[index],   # payment
                due_by_line[index]        # due

            ])

            # update product price
            # cursor.execute(update_query, [row[2], row[3], row[0]])

            update_data.append((row[2], row[3], row[0]))

        # ✅ new cursor
        with connection.cursor() as cursor:
            cursor.executemany(update_query, update_data)

        # ---- Insert into transaction__details ----
        # query = """
        #     INSERT INTO transaction__details
        #     (tran_id, tran_type, loc_id, store_id, tran_type_with, 
        #     tran_head_id, quantity_actual, quantity, quantity_issue, quantity_return,
        #     cp, mrp, expiry_date, tot_amount,
        #     tran_date, status, discount, receive, payment, due)
        #     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        # """        
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

        set_payment_mode(phr_code, payment_mode)
        return JsonResponse({"success": True, "tran_id": phr_code})

    except Exception as e:
        print("🔥 SAVE PURCHASE ERROR:", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
@transaction.atomic
def save_issue(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request"}, status=405)

    try:
        data = json.loads(request.body)

        # ---- Form-level info ----
        store_id = data.get("store")
        location_id = data.get("location")
        tran_type_with = data.get("supplier")
        invoice = data.get("purchaseinvoice")
        payment_method = data.get("payment_method")
        bill_amount = data.get("bill_amount") or 0
        discount = data.get("discount") or 0
        net_amount = data.get("net_amount") or 0
        receive = data.get("receive") or 0
        due = data.get("due") or 0
        tran_date = data.get("tran_date") or timezone.now().strftime("%Y-%m-%d %H:%M:%S")

        products = data.get("products", [])
        if not products:
            return JsonResponse({"success": False, "message": "No products selected"}, status=400)

        # ---- Generate transaction ID ----
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tran_id 
                FROM transaction__mains
                WHERE tran_id LIKE 'PHI%'
                ORDER BY tran_id DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()

            if row:
                last_number = int(row[0][3:])  # remove PHR
            else:
                last_number = 0

            phr_code = "PHI" + str(last_number + 1).zfill(9)
        # ---- END of Generate transaction ID ----

        tran_type = 6
        status = 1

        # ---- Insert into transaction__mains ----
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO transaction__mains
                (tran_id, tran_type, tran_method, tran_type_with, store_id, loc_id,
                 tran_date, status, invoice_ref, bill_amount, discount, net_amount,
                 payment, due)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                phr_code, tran_type, payment_method, tran_type_with, store_id,
                location_id, tran_date, status, bill_amount, bill_amount,
                discount, net_amount, receive, due
            ])

        # ---- Prepare details data using index-style access ----
        details_data = []
        for row in products:
            details_data.append([
                phr_code,         # tran_id
                tran_type,        # tran_type_with
                payment_method,   # tran_method
                invoice,          # invoice
                location_id,      # loc_id
                tran_type_with,   # tran_user
                row[0],           # tran_head_id
                row[1],           # quantity_actual
                0,                # quantity
                row[1],           # quantity_issue
                0,                # quantity_return
                row[5],           # unit_id
                row[2],           # amount (cp)
                row[3],           # tot_amount
                row[2],           # cp
                0,                # mrp (ignored)
                row[6],           # expiry_date
                store_id,         # store_id
                tran_date,        # tran_date
                status,           # status
                discount,         # discount
                receive,          # receive
                receive,          # payment
                due               # due
            ])

        # ---- Insert into transaction__details ----
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

        set_payment_mode(phr_code, "payment")
        return JsonResponse({"success": True, "tran_id": phr_code})

    except Exception as e:
        print("🔥 SAVE PURCHASE ERROR:", e)
        return JsonResponse({"success": False, "error": str(e)}, status=500)    


def pharmacy_party_payment_list(request):
    return render(request, "pharmacy/party_payment_list.html")


def pharmacy_party_payment_list_load(request):
    q = (request.GET.get("q") or "").strip()
    start_date = (request.GET.get("start_date") or "").strip()
    end_date = (request.GET.get("end_date") or "").strip()
    with_group = (request.GET.get("tran_with") or "").strip()
    supplier = (request.GET.get("supplier") or "").strip()
    try:
        limit = min(max(int(request.GET.get("limit", 50)), 1), 200)
        offset = max(int(request.GET.get("offset", 0)), 0)
    except (TypeError, ValueError):
        limit, offset = 50, 0

    base_sql = """
        FROM transaction__mains m
        LEFT JOIN transaction__withs tw ON tw.id = m.tran_type_with
        LEFT JOIN user__infos ui ON ui.user_id = m.tran_user
                                  OR CAST(ui.id AS CHAR) = m.tran_user
        WHERE m.tran_type = 6
          AND m.tran_id LIKE 'PHR%%'
          AND COALESCE(m.due, 0) > 0
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
    if with_group:
        filters.append(" AND m.tran_type_with = %s")
        params.append(with_group)
    if supplier:
        filters.append(" AND (m.tran_user = %s OR ui.user_id = %s OR CAST(ui.id AS CHAR) = %s)")
        params.extend([supplier, supplier, supplier])
    if start_date:
        filters.append(" AND DATE(m.tran_date) >= %s")
        params.append(start_date)
    if end_date:
        filters.append(" AND DATE(m.tran_date) <= %s")
        params.append(end_date)

    filter_sql = "".join(filters)
    select_sql = """
        SELECT m.id, m.tran_id, COALESCE(m.invoice_ref, '') AS invoice_ref,
               DATE_FORMAT(m.tran_date, '%%Y-%%m-%%d %%H:%%i:%%s') AS tran_date,
               COALESCE(tw.tran_with_name, CAST(m.tran_type_with AS CHAR), '') AS supplier_name,
               COALESCE(m.user_name, ui.user_name, m.tran_user, '') AS user_name,
               COALESCE(m.bill_amount, 0) AS bill_total, COALESCE(m.discount, 0) AS discount,
               COALESCE(m.net_amount, 0) AS net_total, COALESCE(m.payment, 0) AS payment,
               COALESCE(m.receive, 0) AS receive, COALESCE(m.due, 0) AS due
    """ + base_sql + filter_sql + " ORDER BY m.tran_date ASC, m.id ASC LIMIT %s OFFSET %s"
    total_sql = "SELECT COALESCE(SUM(m.due), 0) " + base_sql + filter_sql

    with connection.cursor() as cursor:
        cursor.execute(select_sql, params + [limit, offset])
        rows = dictfetchall(cursor)
        cursor.execute(total_sql, params)
        total_due = cursor.fetchone()[0] or 0
    return JsonResponse({"results": rows, "total_due": float(total_due)})


def pharmacy_party_payment_form(request, id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, tran_id, invoice_ref, tran_date, tran_type_with, tran_user,
                   bill_amount, discount, net_amount, payment, receive, due_col, due_disc, due
            FROM transaction__mains
            WHERE id = %s AND tran_type = 6 AND tran_id LIKE 'PHR%%'
            LIMIT 1
        """, [id])
        rows = dictfetchall(cursor)
    return render(request, "general_transaction/party_payment/payment_form.html", {
        "transaction": rows[0] if rows else None,
        "party_payment_process_url": f"/pharmacy/party-payment/process/{id}/",
        "party_payment_redirect_url": "/pharmacy/party-payment/",
    })


@csrf_exempt
@transaction.atomic
def pharmacy_party_payment_process(request, id):
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
            WHERE id = %s AND tran_type = 6 AND tran_id LIKE 'PHR%%'
            LIMIT 1
        """, [id])
        row = cursor.fetchone()
        if not row:
            return JsonResponse({"success": False, "error": "Pharmacy transaction not found"}, status=404)

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
            WHERE tran_id LIKE 'PPR%%' ORDER BY id DESC LIMIT 1
        """)
        last = cursor.fetchone()
        last_no = int(last[0][3:]) if last and last[0] else 0
        payment_tran_id = "PPR" + str(last_no + 1).zfill(9)

        cursor.execute("""
            UPDATE transaction__mains
            SET due = %s, due_col = %s, due_disc = %s
            WHERE id = %s AND tran_type = 6
        """, [new_due, new_due_col, new_due_disc, id])
        cursor.execute("""
            SELECT id, COALESCE(tot_amount, amount, 0)
            FROM transaction__details
            WHERE tran_id = %s AND tran_type = 6
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

    return JsonResponse({"success": True, "paid": pay_amount, "due_discount": due_discount,
                         "new_due": new_due, "redirect_url": "/pharmacy/party-payment/"})


@csrf_exempt
@transaction.atomic
def pharmacy_party_payment_fifo(request):
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
            SELECT id, tran_id, due
            FROM transaction__mains
            WHERE id IN ({placeholders}) AND tran_type = 6 AND tran_id LIKE 'PHR%%'
            ORDER BY tran_date ASC, id ASC
        """, ids)
        for row_id, tran_id, due in cursor.fetchall():
            if remaining <= 0:
                break
            due = float(due or 0)
            if due <= 0:
                continue
            paid = min(remaining, due)
            cursor.execute("""
                UPDATE transaction__mains
                SET payment = COALESCE(payment, 0) + %s, due = %s,
                    due_col = COALESCE(due_col, 0) + %s
                WHERE id = %s AND tran_type = 6
            """, [paid, due - paid, paid, row_id])
            cursor.execute("""
                UPDATE transaction__details
                SET payment = COALESCE(payment, 0) + %s, due = GREATEST(COALESCE(due, 0) - %s, 0),
                    due_col = COALESCE(due_col, 0) + %s
                WHERE tran_id = %s AND tran_type = 6
            """, [paid, paid, paid, tran_id])
            remaining -= paid
    return JsonResponse({"success": True, "paid": payment_amount - remaining})
