
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection


# ============================================================
# DICT FETCH ALL
# ============================================================

def dictfetchall(cursor):
    """Return all rows from a cursor as a list of dictionaries."""

    columns = [col[0] for col in cursor.description]

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


# ============================================================
# BED CATEGORY LIST PAGE
# ============================================================

def bed_category_list(request):

    return render(
        request,
        'bed_category/bed_category_list.html'
    )


# ============================================================
# BED CATEGORY ADD PAGE
# ============================================================

def bed_category_add(request):

    return render(
        request,
        'bed_category/add.html'
    )


# ============================================================
# GET ALL BED CATEGORIES
# ============================================================

@csrf_exempt
def get_bed_categories(request):

    if request.method == "GET":

        try:

            cursor = connection.cursor()

            sql = """
                SELECT
                    id,
                    name,
                    status
                FROM bed_categories
                ORDER BY id DESC
            """

            cursor.execute(sql)

            bed_categories = dictfetchall(cursor)

            return JsonResponse({
                "status": "success",
                "bed_categories": bed_categories
            })


        except Exception as e:

            print(
                f"DEBUG ERROR: {str(e)}"
            )

            return JsonResponse({
                "status": "error",
                "message": f"Database error: {str(e)}"
            })


    return JsonResponse({
        "status": "failed",
        "message": "Invalid request"
    })


# ============================================================
# GET SINGLE BED CATEGORY / EDIT PAGE
# ============================================================

def bed_category_edit(request, id):

    try:

        cursor = connection.cursor()

        sql = """
            SELECT
                id,
                name,
                status
            FROM bed_categories
            WHERE id = %s
        """

        cursor.execute(
            sql,
            [id]
        )

        category_list = dictfetchall(cursor)


        if not category_list:

            return JsonResponse({
                "status": "error",
                "message": "Bed Category not found."
            })


        category = category_list[0]


        return render(
            request,
            "bed_category/edit.html",
            {
                "category": category
            }
        )


    except Exception as e:

        return JsonResponse({
            "status": "error",
            "message": str(e)
        })


# ============================================================
# SAVE NEW BED CATEGORY
# ============================================================

@csrf_exempt
def save_bed_category(request):

    if request.method == "POST":

        # ----------------------------------------------------
        # GET FORM DATA
        # ----------------------------------------------------

        category_name = request.POST.get('name')

        category_status = request.POST.get('status')


        # ----------------------------------------------------
        # DEFAULT STATUS
        # ----------------------------------------------------

        if category_status in [None, ""]:

            category_status = 1


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not category_name:

            return JsonResponse({
                "status": "error",
                "message": "Bed Category name is required."
            })


        try:

            cursor = connection.cursor()


            # ------------------------------------------------
            # INSERT
            # ------------------------------------------------

            sql = """
                INSERT INTO bed_categories
                (
                    name,
                    status
                )
                VALUES (%s, %s)
            """


            params = [
                category_name,
                category_status
            ]


            cursor.execute(
                sql,
                params
            )


            return JsonResponse({
                "status": "success",
                "message": "Bed Category saved successfully!"
            })


        except Exception as e:

            return JsonResponse({
                "status": "error",
                "message": str(e)
            })


    return JsonResponse({
        "status": "failed",
        "message": "Invalid request"
    })


# ============================================================
# UPDATE BED CATEGORY
# ============================================================

@csrf_exempt
def update_bed_category(request):

    if request.method == "POST":

        # ----------------------------------------------------
        # GET FORM DATA
        # ----------------------------------------------------

        category_id = request.POST.get('id')

        category_name = request.POST.get('name')

        category_status = request.POST.get('status')


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not category_id:

            return JsonResponse({
                "status": "error",
                "message": "Bed Category ID is required."
            })


        if not category_name:

            return JsonResponse({
                "status": "error",
                "message": "Bed Category name is required."
            })


        # ----------------------------------------------------
        # DEFAULT STATUS
        # ----------------------------------------------------

        if category_status in [None, ""]:

            category_status = 1


        try:

            cursor = connection.cursor()


            # ------------------------------------------------
            # UPDATE
            # ------------------------------------------------

            sql = """
                UPDATE bed_categories
                SET
                    name = %s,
                    status = %s
                WHERE id = %s
            """


            params = [
                category_name,
                category_status,
                category_id
            ]


            cursor.execute(
                sql,
                params
            )


            # ------------------------------------------------
            # CHECK UPDATE
            # ------------------------------------------------

            if cursor.rowcount == 0:

                return JsonResponse({
                    "status": "error",
                    "message": "Bed Category not found."
                })


            return JsonResponse({
                "status": "success",
                "message": "Bed Category updated successfully!"
            })


        except Exception as e:

            return JsonResponse({
                "status": "error",
                "message": str(e)
            })


    return JsonResponse({
        "status": "failed",
        "message": "Invalid request"
    })


# ============================================================
# DELETE BED CATEGORY
# ============================================================

@csrf_exempt
def remove_bed_category(request):

    if request.method == "POST":

        # ----------------------------------------------------
        # GET ID
        # ----------------------------------------------------

        category_id = request.POST.get('id')


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not category_id:

            return JsonResponse({
                "status": "error",
                "message": "Bed Category ID is required."
            })


        try:

            cursor = connection.cursor()


            # ------------------------------------------------
            # DELETE
            # ------------------------------------------------

            sql = """
                DELETE FROM bed_categories
                WHERE id = %s
            """


            cursor.execute(
                sql,
                [category_id]
            )


            # ------------------------------------------------
            # CHECK DELETE
            # ------------------------------------------------

            if cursor.rowcount == 0:

                return JsonResponse({
                    "status": "error",
                    "message": "Bed Category not found."
                })


            return JsonResponse({
                "status": "success",
                "message": "Bed Category removed successfully!"
            })


        except Exception as e:

            return JsonResponse({
                "status": "error",
                "message": str(e)
            })


    return JsonResponse({
        "status": "failed",
        "message": "Invalid request"
    })