from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection


# =========================================================
# DICT FETCH ALL
# =========================================================

def dictfetchall(cursor):

    columns = [
        col[0]
        for col in cursor.description
    ]

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


# =========================================================
# CHECK IN DETAILS LIST
# =========================================================

def check_in_details_list(request):

    return render(
        request,
        'check_in_details/check_in_details.html'
    )

def check_in_details_add(request):

    return render(
        request,
        'check_in_details/add.html'
    )


# =========================================================
# GET CHECK IN DETAILS
# =========================================================

@csrf_exempt
def get_check_in_details(request):

    if request.method == "GET":

        try:

            with connection.cursor() as cursor:

                sql = """
                    SELECT
                        cid.id,
                        cid.hotel_guest_id,
                        hgi.guest_name,

                        cid.bed_category_id,
                        bc.name AS bed_category,

                        cid.bed_info_id,
                        bi.bed_no,

                        cid.check_in,
                        cid.check_out,
                        cid.remarks,
                        cid.status

                    FROM check_in_details cid

                    LEFT JOIN hotel_guests_info hgi
                        ON cid.hotel_guest_id = hgi.id

                    LEFT JOIN bed_categories bc
                        ON cid.bed_category_id = bc.id

                    LEFT JOIN bed_info bi
                        ON cid.bed_info_id = bi.id

                    ORDER BY cid.id DESC
                """

                cursor.execute(sql)

                check_in_details = dictfetchall(
                    cursor
                )

            return JsonResponse({

                "status": "success",

                "check_in_details":
                    check_in_details

            })

        except Exception as e:

            return JsonResponse({

                "status": "error",

                "message": str(e)

            }, status=500)


    return JsonResponse({

        "status": "failed",

        "message": "Invalid request"

    }, status=400)


# =========================================================
# GET HOTEL GUEST LIST
# =========================================================

@csrf_exempt
def get_hotel_guests(request):

    if request.method == "GET":

        try:

            with connection.cursor() as cursor:

                sql = """
                    SELECT
                        id,
                        guest_name,
                        mobile,
                        status

                    FROM hotel_guests_info

                    WHERE status = 1

                    ORDER BY id DESC
                """

                cursor.execute(sql)

                guests = dictfetchall(
                    cursor
                )

            return JsonResponse({

                "status": "success",

                "guests": guests

            })

        except Exception as e:

            return JsonResponse({

                "status": "error",

                "message": str(e)

            }, status=500)


    return JsonResponse({

        "status": "failed",

        "message": "Invalid request"

    }, status=400)


# =========================================================
# GET GUEST CHECK IN INFO
# =========================================================
# Guest select korle:
#
# Bed Category
# Bed Info / Bed No
# Check In
#
# automatically return korbe.
#
# hotel_guests_info actual columns:
#
# Bed_Category
# bed_info
# check_in
# =========================================================

@csrf_exempt
def get_guest_check_in_info(request):

    if request.method == "GET":

        guest_id = request.GET.get(
            'guest_id'
        )

        if not guest_id:

            return JsonResponse({

                "status": "error",

                "message":
                    "Guest ID is required"

            }, status=400)

        try:

            with connection.cursor() as cursor:

                sql = """
                    SELECT
                        h.id,
                        h.guest_name,

                        h.Bed_Category,

                        h.bed_info,

                        bi.bed_no,

                        h.check_in

                    FROM hotel_guests_info h

                    LEFT JOIN bed_info bi
                        ON h.bed_info = bi.id

                    WHERE h.id = %s

                    LIMIT 1
                """

                cursor.execute(
                    sql,
                    [guest_id]
                )

                row = cursor.fetchone()


            if not row:

                return JsonResponse({

                    "status": "error",

                    "message":
                        "Guest information not found"

                }, status=404)


            guest_info = {

                "id":
                    row[0],

                "guest_name":
                    row[1],

                # ---------------------------------------------
                # DB COLUMN:
                # Bed_Category
                #
                # JS KEY:
                # bed_category_id
                # ---------------------------------------------

                "bed_category_id":
                    row[2] or '',


                # ---------------------------------------------
                # DB COLUMN:
                # bed_info
                #
                # JS KEY:
                # bed_info_id
                # ---------------------------------------------

                "bed_info_id":
                    row[3] or '',


                "bed_no":
                    row[4] or '',


                "check_in": (
                    row[5].strftime(
                        '%Y-%m-%d'
                    )
                    if row[5]
                    else ''
                )
            }


            return JsonResponse({

                "status": "success",

                "guest_info":
                    guest_info

            })


        except Exception as e:

            return JsonResponse({

                "status": "error",

                "message": str(e)

            }, status=500)


    return JsonResponse({

        "status": "failed",

        "message":
            "Invalid request method"

    }, status=400)


# =========================================================
# SAVE CHECK IN DETAILS
# =========================================================

@csrf_exempt
def save_check_in_details(request):

    if request.method == "POST":

        # -------------------------------------------------
        # FORM DATA
        # -------------------------------------------------

        hotel_guest_id = request.POST.get(
            'hotel_guest_id'
        )

        bed_category_id = request.POST.get(
            'bed_category_id'
        )

        bed_info_id = request.POST.get(
            'bed_info_id'
        )

        check_in = request.POST.get(
            'check_in'
        )

        check_out = request.POST.get(
            'check_out'
        )

        remarks = request.POST.get(
            'remarks'
        )

        status = request.POST.get(
            'status'
        ) or '1'


        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if not hotel_guest_id:

            return JsonResponse({

                "status": "error",

                "message":
                    "Please select hotel guest"

            }, status=400)


        if not bed_category_id:

            return JsonResponse({

                "status": "error",

                "message":
                    "Bed Category is required"

            }, status=400)


        if not bed_info_id:

            return JsonResponse({

                "status": "error",

                "message":
                    "Bed Info is required"

            }, status=400)


        try:

            with connection.cursor() as cursor:

                sql = """
                    INSERT INTO check_in_details
                    (
                        hotel_guest_id,
                        bed_category_id,
                        bed_info_id,
                        check_in,
                        check_out,
                        remarks,
                        status
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """

                params = [

                    hotel_guest_id,

                    bed_category_id,

                    bed_info_id,

                    check_in
                    if check_in
                    else None,

                    check_out
                    if check_out
                    else None,

                    remarks,

                    status

                ]

                cursor.execute(
                    sql,
                    params
                )


            return JsonResponse({

                "status": "success",

                "message":
                    "Check In Details saved successfully!"

            })


        except Exception as e:

            return JsonResponse({

                "status": "error",

                "message": str(e)

            }, status=500)


    return JsonResponse({

        "status": "failed",

        "message":
            "Invalid request"

    }, status=400)


# =========================================================
# UPDATE CHECK IN DETAILS
# =========================================================

@csrf_exempt
def update_check_in_details(request):

    if request.method == "POST":

        # -------------------------------------------------
        # FORM DATA
        # -------------------------------------------------

        check_in_id = request.POST.get(
            'id'
        )

        hotel_guest_id = request.POST.get(
            'hotel_guest_id'
        )

        bed_category_id = request.POST.get(
            'bed_category_id'
        )

        bed_info_id = request.POST.get(
            'bed_info_id'
        )

        check_in = request.POST.get(
            'check_in'
        )

        check_out = request.POST.get(
            'check_out'
        )

        remarks = request.POST.get(
            'remarks'
        )

        status = request.POST.get(
            'status'
        ) or '1'


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not check_in_id:

            return JsonResponse({

                "status": "error",

                "message":
                    "Check In ID is required"

            }, status=400)


        if not hotel_guest_id:

            return JsonResponse({

                "status": "error",

                "message":
                    "Please select hotel guest"

            }, status=400)


        if not bed_category_id:

            return JsonResponse({

                "status": "error",

                "message":
                    "Bed Category is required"

            }, status=400)


        if not bed_info_id:

            return JsonResponse({

                "status": "error",

                "message":
                    "Bed Info is required"

            }, status=400)


        try:

            with connection.cursor() as cursor:

                sql = """
                    UPDATE check_in_details

                    SET
                        hotel_guest_id = %s,
                        bed_category_id = %s,
                        bed_info_id = %s,
                        check_in = %s,
                        check_out = %s,
                        remarks = %s,
                        status = %s

                    WHERE id = %s
                """

                params = [

                    hotel_guest_id,

                    bed_category_id,

                    bed_info_id,

                    check_in
                    if check_in
                    else None,

                    check_out
                    if check_out
                    else None,

                    remarks,

                    status,

                    check_in_id

                ]

                cursor.execute(
                    sql,
                    params
                )


            return JsonResponse({

                "status": "success",

                "message":
                    "Check In Details updated successfully!"

            })


        except Exception as e:

            return JsonResponse({

                "status": "error",

                "message": str(e)

            }, status=500)


    return JsonResponse({

        "status": "failed",

        "message":
            "Invalid request"

    }, status=400)


# =========================================================
# REMOVE CHECK IN DETAILS
# =========================================================

@csrf_exempt
def remove_check_in_details(request):

    if request.method == "POST":

        check_in_id = request.POST.get(
            'id'
        )


        if not check_in_id:

            return JsonResponse({

                "status": "error",

                "message":
                    "Check In ID is required"

            }, status=400)


        try:

            with connection.cursor() as cursor:

                sql = """
                    DELETE FROM check_in_details

                    WHERE id = %s
                """

                cursor.execute(
                    sql,
                    [check_in_id]
                )


            return JsonResponse({

                "status": "success",

                "message":
                    "Check In Details removed successfully!"

            })


        except Exception as e:

            return JsonResponse({

                "status": "error",

                "message": str(e)

            }, status=500)


    return JsonResponse({

        "status": "failed",

        "message":
            "Invalid request"

    }, status=400)