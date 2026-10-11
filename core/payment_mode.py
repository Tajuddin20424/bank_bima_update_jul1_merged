from django.db import connection


def set_payment_mode(tran_id, mode):
    """Keep the payment/receive mode synchronized in both transaction tables."""
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE transaction__mains SET payment_mode = %s WHERE tran_id = %s",
            [mode, tran_id],
        )
        cursor.execute(
            "UPDATE transaction__details SET payment_mode = %s WHERE tran_id = %s",
            [mode, tran_id],
        )
