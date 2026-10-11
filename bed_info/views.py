from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


# ============================================================
# BED INFO LIST
# ============================================================

def bed_info_list(request):

    return render(
        request,
        'bed_info/bed_info_list.html'
    )


# ============================================================
# BED INFO ADD
# ============================================================

def bed_info_add(request):

    return render(
        request,
        'bed_info/add.html'
    )


# ============================================================
# BED INFO EDIT PAGE
# ============================================================

def bed_info_edit(request, id):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT
                id,
                category_id,
                bed_no,
                occupancy,
                entry_at,
                entry_by,
                status

            FROM bed_info

            WHERE id = %s
        """, [id])

        row = cursor.fetchone()


    if not row:

        return JsonResponse({

            'status': 'error',

            'message': 'Bed Info not found.'

        })


    bed = {

        'id': row[0],

        'category_id': row[1],

        'bed_no': row[2],

        'occupancy': row[3],

        'entry_at': row[4],

        'entry_by': row[5],

        'status': row[6]

    }


    return render(

        request,

        'bed_info/edit.html',

        {
            'bed': bed
        }

    )


# ============================================================
# GET BED INFO
# ============================================================

@csrf_exempt
def get_bed_info(request):

    category_id = request.GET.get(
        'category_id',
        ''
    )

    with connection.cursor() as cursor:

        # ====================================================
        # BED INFO LIST
        # ====================================================

        if category_id:

            cursor.execute("""
                SELECT
                    bi.id,
                    bi.category_id,
                    bc.name,
                    bi.bed_no,
                    bi.occupancy,
                    bi.entry_at,
                    bi.entry_by,
                    bi.status

                FROM bed_info bi

                LEFT JOIN bed_categories bc
                    ON bi.category_id = bc.id

                WHERE bi.category_id = %s

                ORDER BY bi.id DESC
            """, [category_id])

        else:

            cursor.execute("""
                SELECT
                    bi.id,
                    bi.category_id,
                    bc.name,
                    bi.bed_no,
                    bi.occupancy,
                    bi.entry_at,
                    bi.entry_by,
                    bi.status

                FROM bed_info bi

                LEFT JOIN bed_categories bc
                    ON bi.category_id = bc.id

                ORDER BY bi.id DESC
            """)


        rows = cursor.fetchall()

        bed_info = []


        for row in rows:

            bed_info.append({

                'id': row[0],

                'category_id': row[1],

                'category_name': row[2],

                'bed_no': row[3],

                'occupancy': row[4],

                'entry_at': row[5],

                'entry_by': row[6],

                'status': row[7]

            })


        # ====================================================
        # NORMAL CATEGORY SUMMARY
        # TEMP CATEGORY EXCLUDED
        # ====================================================

        cursor.execute("""
            SELECT
                bc.id,
                bc.name,

                SUM(
                    CASE
                        WHEN bi.occupancy = 'vacant'
                        THEN 1
                        ELSE 0
                    END
                ) AS total_vacant,

                SUM(
                    CASE
                        WHEN bi.occupancy = 'occupied'
                        THEN 1
                        ELSE 0
                    END
                ) AS total_occupied

            FROM bed_categories bc

            LEFT JOIN bed_info bi
                ON bc.id = bi.category_id
                AND bi.status = 1

            WHERE bc.status = 1

            AND UPPER(TRIM(bc.name)) != 'TEMP'

            GROUP BY
                bc.id,
                bc.name

            ORDER BY bc.id ASC
        """)


        category_rows = cursor.fetchall()


        category_summary = []

        total_vacant = 0

        total_occupied = 0


        for row in category_rows:

            category_vacant = int(
                row[2] or 0
            )

            category_occupied = int(
                row[3] or 0
            )

            category_total = (
                category_vacant
                +
                category_occupied
            )


            category_summary.append({

                'category_id':
                    row[0],

                'category_name':
                    row[1],

                'total_vacant':
                    category_vacant,

                'total_occupied':
                    category_occupied,

                'total_bed':
                    category_total

            })


            total_vacant += category_vacant

            total_occupied += category_occupied


        # ====================================================
        # NORMAL TOTAL
        # ====================================================

        normal_total_bed = (
            total_vacant
            +
            total_occupied
        )


        # ====================================================
        # TEMP CATEGORY
        # VACANT + OCCUPIED
        # ====================================================

        cursor.execute("""
            SELECT

                SUM(
                    CASE
                        WHEN bi.occupancy = 'vacant'
                        THEN 1
                        ELSE 0
                    END
                ) AS temp_vacant,

                SUM(
                    CASE
                        WHEN bi.occupancy = 'occupied'
                        THEN 1
                        ELSE 0
                    END
                ) AS temp_occupied

            FROM bed_info bi

            INNER JOIN bed_categories bc
                ON bi.category_id = bc.id

            WHERE bi.status = 1

            AND bc.status = 1

            AND UPPER(TRIM(bc.name)) = 'TEMP'
        """)


        temp_row = cursor.fetchone()


        temp_vacant = int(
            temp_row[0] or 0
        )

        temp_occupied = int(
            temp_row[1] or 0
        )


        temp_total = (
            temp_vacant
            +
            temp_occupied
        )


        # ====================================================
        # ALL BED TOTAL
        # ====================================================

        all_vacant = (
            total_vacant
            +
            temp_vacant
        )


        all_occupied = (
            total_occupied
            +
            temp_occupied
        )


        total_bed = (
            normal_total_bed
            +
            temp_total
        )


    # ========================================================
    # JSON RESPONSE
    # ========================================================

    return JsonResponse({

        'bed_info':
            bed_info,

        'category_summary':
            category_summary,

        # NORMAL
        'total_vacant':
            total_vacant,

        'total_occupied':
            total_occupied,

        'normal_total_bed':
            normal_total_bed,

        # TEMP
        'temp_vacant':
            temp_vacant,

        'temp_occupied':
            temp_occupied,

        'temp_total':
            temp_total,

        # ALL
        'all_vacant':
            all_vacant,

        'all_occupied':
            all_occupied,

        'total_bed':
            total_bed

    })

    
# ============================================================
# SAVE BED INFO
# ============================================================

@csrf_exempt
def save_bed_info(request):

    if request.method == 'POST':


        category_id = request.POST.get(
            'category_id'
        )


        bed_no = request.POST.get(
            'bed_no'
        )


        occupancy = request.POST.get(
            'occupancy',
            'vacant'
        )


        status = request.POST.get(
            'status',
            1
        )


        # ====================================================
        # VALIDATION
        # ====================================================

        if not category_id or not bed_no:

            return JsonResponse({

                'status':
                    'error',

                'message':
                    'Category and Bed No are required.'

            })


        try:

            with connection.cursor() as cursor:


                # =============================================
                # INSERT BED
                # =============================================

                cursor.execute("""
                    INSERT INTO bed_info
                    (
                        category_id,
                        bed_no,
                        occupancy,
                        entry_at,
                        entry_by,
                        status
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        NOW(),
                        NOW(),
                        %s
                    )
                """, [

                    category_id,

                    bed_no,

                    occupancy,

                    status

                ])


            return JsonResponse({

                'status':
                    'success',

                'message':
                    'Bed Info saved successfully!'

            })


        except Exception as e:

            return JsonResponse({

                'status':
                    'error',

                'message':
                    str(e)

            })


    return JsonResponse({

        'status':
            'error',

        'message':
            'Invalid request.'

    })


# ============================================================
# UPDATE BED INFO
# ============================================================

@csrf_exempt
def update_bed_info(request):

    if request.method == 'POST':


        bed_id = request.POST.get(
            'id'
        )


        category_id = request.POST.get(
            'category_id'
        )


        bed_no = request.POST.get(
            'bed_no'
        )


        occupancy = request.POST.get(
            'occupancy',
            'vacant'
        )


        status = request.POST.get(
            'status',
            1
        )


        # ====================================================
        # VALIDATION
        # ====================================================

        if not bed_id:

            return JsonResponse({

                'status':
                    'error',

                'message':
                    'Bed Info ID is required.'

            })


        if not category_id or not bed_no:

            return JsonResponse({

                'status':
                    'error',

                'message':
                    'Category and Bed No are required.'

            })


        try:

            with connection.cursor() as cursor:


                # =============================================
                # UPDATE BED
                # =============================================

                cursor.execute("""
                    UPDATE bed_info

                    SET

                        category_id = %s,

                        bed_no = %s,

                        occupancy = %s,

                        entry_by = NOW(),

                        status = %s

                    WHERE id = %s
                """, [

                    category_id,

                    bed_no,

                    occupancy,

                    status,

                    bed_id

                ])


                rowcount = cursor.rowcount


            if rowcount == 0:

                return JsonResponse({

                    'status':
                        'error',

                    'message':
                        'Bed Info not found.'

                })


            return JsonResponse({

                'status':
                    'success',

                'message':
                    'Bed Info updated successfully!'

            })


        except Exception as e:

            return JsonResponse({

                'status':
                    'error',

                'message':
                    str(e)

            })


    return JsonResponse({

        'status':
            'error',

        'message':
            'Invalid request.'

    })


# ============================================================
# REMOVE BED INFO
# ============================================================

@csrf_exempt
def remove_bed_info(request):

    if request.method == 'POST':


        bed_id = request.POST.get(
            'id'
        )


        if not bed_id:

            return JsonResponse({

                'status':
                    'error',

                'message':
                    'Bed Info ID is required.'

            })


        try:

            with connection.cursor() as cursor:


                cursor.execute("""
                    DELETE FROM bed_info

                    WHERE id = %s
                """, [
                    bed_id
                ])


                rowcount = cursor.rowcount


            if rowcount == 0:

                return JsonResponse({

                    'status':
                        'error',

                    'message':
                        'Bed Info not found.'

                })


            return JsonResponse({

                'status':
                    'success',

                'message':
                    'Bed Info removed successfully!'

            })


        except Exception as e:

            return JsonResponse({

                'status':
                    'error',

                'message':
                    str(e)

            })


    return JsonResponse({

        'status':
            'error',

        'message':
            'Invalid request.'

    })