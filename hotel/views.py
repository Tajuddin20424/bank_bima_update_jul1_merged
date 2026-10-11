from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection, transaction
from django.conf import settings
from django.utils import timezone

import os
import uuid
import traceback
import random
import string


def generate_10_digit_id():
    """Generate a random 10-digit ID."""
    return ''.join(random.choices(string.digits, k=10))


def dictfetchall(cursor):
    """Convert database cursor results to list of dictionaries."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ============================================================
# HOTEL PAGE
# ============================================================

def hotel_view(request):

    return render(
        request,
        'hotel/guest_info.html'
    )


# ============================================================
# IMAGE UPLOAD
# ============================================================

def save_guest_image(image_file):

    if not image_file:
        return None

    allowed_extensions = [
        '.jpg',
        '.jpeg',
        '.png',
        '.webp'
    ]

    extension = os.path.splitext(
        image_file.name
    )[1].lower()

    if extension not in allowed_extensions:

        raise ValueError(
            'Only JPG, JPEG, PNG and WEBP images are allowed.'
        )

    if image_file.size > 5 * 1024 * 1024:

        raise ValueError(
            'Image size must be less than 5 MB.'
        )

    upload_dir = os.path.join(
        settings.MEDIA_ROOT,
        'hotel_guests'
    )

    os.makedirs(
        upload_dir,
        exist_ok=True
    )

    filename = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    relative_path = os.path.join(
        'hotel_guests',
        filename
    )

    full_path = os.path.join(
        settings.MEDIA_ROOT,
        relative_path
    )

    with open(
        full_path,
        'wb+'
    ) as destination:

        for chunk in image_file.chunks():

            destination.write(
                chunk
            )

    return relative_path.replace(
        os.sep,
        '/'
    )


# ============================================================
# DELETE IMAGE
# ============================================================

def delete_guest_image(image_path):

    if not image_path:
        return

    try:

        full_path = os.path.join(
            settings.MEDIA_ROOT,
            image_path
        )

        if os.path.isfile(full_path):

            os.remove(full_path)

    except Exception:

        pass


# ============================================================
# LOAD HOTEL GUEST
# ============================================================

def load_hotel(request):

    if request.method == 'GET':

        try:

            with connection.cursor() as cursor:

                sql = """
                    SELECT
                        id,
                        title,
                        guest_name,
                        image,
                        mobile,
                        gender,
                        date_of_birth,
                        nationality,
                        address,
                        check_in,
                        check_out,
                        booking_source,
                        guest_category,
                        Bed_Category,
                        bed_info,
                        emergency_guest_contact,
                        status,
                        entry_by
                    FROM hotel_guests_info
                    ORDER BY id ASC
                """

                cursor.execute(sql)

                rows = cursor.fetchall()


            hotel_list = []

            for row in rows:

                hotel_list.append({

                    'id': row[0],

                    'title': row[1] or '',

                    'guest_name': row[2] or '',

                    'image': row[3] or '',

                    'mobile': row[4] or '',

                    'gender': row[5] or '',

                    'date_of_birth': (
                        row[6].strftime('%Y-%m-%d')
                        if row[6]
                        else ''
                    ),

                    'nationality': row[7] or '',

                    'address': row[8] or '',

                    'check_in': (
                        row[9].strftime('%Y-%m-%dT%H:%M')
                        if row[9]
                        else ''
                    ),

                    'check_out': (
                        row[10].strftime('%Y-%m-%dT%H:%M')
                        if row[10]
                        else ''
                    ),

                    'booking_source': row[11] or '',

                    'guest_category': row[12] or '',

                    'bed_category': row[13] or '',

                    'bed_info': row[14] or '',

                    'emergency_guest_contact':
                        row[15] or '',

                    'status': row[16],
                    'entry_by': row[17] or ''


                })


            return JsonResponse({
                'status': 'success',
                'hotels': hotel_list
            })


        except Exception as e:

            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request'
    })

#save_hotel function----------------------------

def save_hotel(request):

    if request.method == "POST":

        title = request.POST.get('title')
        guest_name = request.POST.get('guest_name')
        mobile = request.POST.get('mobile')
        gender = request.POST.get('gender')
        date_of_birth = request.POST.get('date_of_birth')
        nationality = request.POST.get('nationality')
        address = request.POST.get('address')
        booking_source = request.POST.get('booking_source')
        guest_category = request.POST.get('guest_category')
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')
        bed_category_id = request.POST.get('bed_category_id')
        bed_info_id = request.POST.get('bed_info_id')
        emergency_guest_contact = request.POST.get('emergency_guest_contact')
        entry_by = request.POST.get('entry_by')
        status = request.POST.get('status')

        # Transaction Head ID
        head_id = request.POST.get('head_id')

        image_file = request.FILES.get('image')

        try:

            # ==============================
            # IMAGE
            # ==============================

            image_path = None

            if image_file:
                image_path = save_guest_image(image_file)


            cursor = connection.cursor()


            # ==============================
            # GENERATE UNIQUE GUEST ID
            # ==============================

            cursor.execute("""
                SELECT COALESCE(MAX(id), 0) + 1
                FROM hotel_guests_info
            """)

            next_guest_id = cursor.fetchone()[0]

            guest_unique_id = f"GUEST{next_guest_id:09d}"


            # ==============================
            # SAVE HOTEL GUEST
            # ==============================

            hotel_sql = """
                INSERT INTO hotel_guests_info
                (
                    id,
                    guest_id,
                    title,
                    guest_name,
                    image,
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
                    status,
                    entry_by
                )
                VALUES
                (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
            """

            hotel_params = [
                next_guest_id,
                guest_unique_id,
                title,
                guest_name,
                image_path,
                mobile,
                gender,
                date_of_birth or None,
                nationality,
                address,
                booking_source,
                guest_category,
                check_in or None,
                check_out or None,
                bed_category_id,
                bed_info_id,
                emergency_guest_contact,
                status,
                entry_by
            ]

            cursor.execute(hotel_sql, hotel_params)


            # ==============================
            # SAVE GUEST INTO USER__INFOS
            # ==============================

            user_sql = """
                INSERT INTO user__infos
                (
                    user_id,
                    login_user_id,
                    title,
                    user_name,
                    user_phone,
                    gender,
                    dob,
                    nationality,
                    address,
                    tran_user_type,
                    tran_method,
                    tran_with_id,
                    image,
                    status,
                    added_at
                )
                VALUES
                (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
            """

            user_params = [
                guest_unique_id,
                guest_unique_id,
                title,
                guest_name,
                mobile,
                gender,
                date_of_birth or None,
                nationality,
                address,
                8,
                "Both",
                36,
                image_path,
                1 if status == 'A' else 0,
                timezone.now()
            ]

            cursor.execute(user_sql, user_params)


            # ==============================
            # SAVE GUEST INTO
            # TRANSACTION__WITHS
            # ==============================

            if head_id:

                with_id = generate_10_digit_id()

                with_sql = """
                    INSERT INTO transaction__withs
                    (
                        id,
                        tran_type,
                        tran_with_name
                    )
                    VALUES
                    (
                        %s, %s, %s
                    )
                """

                with_params = [
                    with_id,
                    head_id,
                    guest_name
                ]

                cursor.execute(
                    with_sql,
                    with_params
                )


            # ==============================
            # BED OCCUPIED
            # ==============================

            if bed_info_id:

                bed_sql = """
                    UPDATE bed_info
                    SET occupancy = 'occupied'
                    WHERE id = %s
                """

                cursor.execute(
                    bed_sql,
                    [bed_info_id]
                )


            # ==============================
            # SUCCESS
            # ==============================

            return JsonResponse({
                "status": "success",
                "message": "Guest saved successfully!!",
                "guest_id": guest_unique_id
            })


        except Exception as e:

            print("ERROR >>>", str(e))

            return JsonResponse({
                "status": "error",
                "message": str(e)
            })


    return JsonResponse({
        "status": "failed",
        "message": "Invalid request"
    })

# ============================================================
# UPDATE HOTEL GUEST
# ============================================================

def update_hotel(request):

    if request.method == "POST":

        guest_db_id = request.POST.get('id')
        title = request.POST.get('title')
        guest_name = request.POST.get('guest_name')
        mobile = request.POST.get('mobile')
        gender = request.POST.get('gender')
        date_of_birth = request.POST.get('date_of_birth')
        nationality = request.POST.get('nationality')
        address = request.POST.get('address')
        booking_source = request.POST.get('booking_source')
        guest_category = request.POST.get('guest_category')
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')
        bed_category_id = request.POST.get('bed_category_id')
        bed_info_id = request.POST.get('bed_info_id')
        emergency_guest_contact = request.POST.get('emergency_guest_contact')
        status = request.POST.get('status')
        entry_by = request.POST.get('entry_by')
        image_file = request.FILES.get('image')

        try:

            cursor = connection.cursor()


            # Get Guest ID and Old Image

            sql = """
                SELECT guest_id, image
                FROM hotel_guests_info
                WHERE id = %s
            """

            cursor.execute(sql, [guest_db_id])

            guest = cursor.fetchone()


            if not guest:
                return JsonResponse({
                    "status": "error",
                    "message": "Guest not found"
                })


            guest_unique_id = guest[0]
            old_image = guest[1]


            # New image selected

            if image_file:

                image_path = save_guest_image(image_file)

                sql = """
                    UPDATE hotel_guests_info
                    SET
                        title = %s,
                        guest_name = %s,
                        image = %s,
                        mobile = %s,
                        gender = %s,
                        date_of_birth = %s,
                        nationality = %s,
                        address = %s,
                        booking_source = %s,
                        guest_category = %s,
                        check_in = %s,
                        check_out = %s,
                        Bed_Category = %s,
                        bed_info = %s,
                        emergency_guest_contact = %s,
                        entry_by = %s,
                        status = %s
                    WHERE id = %s
                """

                params = [
                        title,
                        guest_name,
                        image_path,
                        mobile,
                        gender,
                        date_of_birth or None,
                        nationality,
                        address,
                        booking_source,
                        guest_category,
                        check_in or None,
                        check_out or None,
                        bed_category_id,
                        bed_info_id,
                        emergency_guest_contact,
                        entry_by,
                        status,
                        guest_db_id
                    ]

                cursor.execute(sql, params)


                if old_image:
                    delete_guest_image(old_image)


            # No new image selected

            else:

                image_path = old_image

                sql = """
                    UPDATE hotel_guests_info
                    SET
                        title = %s,
                        guest_name = %s,
                        mobile = %s,
                        gender = %s,
                        date_of_birth = %s,
                        nationality = %s,
                        address = %s,
                        booking_source = %s,
                        guest_category = %s,
                        check_in = %s,
                        check_out = %s,
                        Bed_Category = %s,
                        bed_info = %s,
                        emergency_guest_contact = %s,
                        status = %s,
                        entry_by = %s
                    WHERE id = %s
                """

                params = [
                    title,
                    guest_name,
                    mobile,
                    gender,
                    date_of_birth or None,
                    nationality,
                    address,
                    booking_source,
                    guest_category,
                    check_in or None,
                    check_out or None,
                    bed_category_id,
                    bed_info_id,
                    emergency_guest_contact,
                    status,
                    entry_by,
                    guest_db_id
                ]

                cursor.execute(sql, params)


            # Update Same Guest in user__infos

            user_sql = """
                UPDATE user__infos
                SET
                    title = %s,
                    user_name = %s,
                    user_phone = %s,
                    gender = %s,
                    dob = %s,
                    nationality = %s,
                    address = %s,
                    image = %s,
                    status = %s
                WHERE user_id = %s
            """

            user_params = [
                title,
                guest_name,
                mobile,
                gender,
                date_of_birth or None,
                nationality,
                address,
                image_path,
                1 if status == 'A' else 0,
                guest_unique_id
            ]

            cursor.execute(user_sql, user_params)


            # Selected Bed Occupied

            if bed_info_id:

                sql = """
                    UPDATE bed_info
                    SET occupancy = 'occupied'
                    WHERE id = %s
                """

                cursor.execute(sql, [bed_info_id])


            return JsonResponse({
                "status": "success",
                "message": "Guest information updated successfully"
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
# DELETE HOTEL GUEST
# ============================================================

def delete_hotel(request):

    if request.method == "POST":

        guest_db_id = request.POST.get('id')

        print("DELETE GUEST ID >>>", guest_db_id)

        try:

            cursor = connection.cursor()


            # Get Guest ID and Image

            sql = """
                SELECT guest_id, image
                FROM hotel_guests_info
                WHERE id = %s
            """

            cursor.execute(sql, [guest_db_id])

            guest = cursor.fetchone()


            if not guest:

                return JsonResponse({
                    "status": "error",
                    "message": "Guest not found"
                })


            guest_unique_id = guest[0]
            image_path = guest[1]


            # Delete From user__infos

            sql = """
                DELETE FROM user__infos
                WHERE user_id = %s
            """

            cursor.execute(sql, [guest_unique_id])


            # Delete Hotel Guest

            sql = """
                DELETE FROM hotel_guests_info
                WHERE id = %s
            """

            cursor.execute(sql, [guest_db_id])


            # Delete Image

            if image_path:
                delete_guest_image(image_path)


            return JsonResponse({
                "status": "success",
                "message": "Guest information deleted successfully"
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