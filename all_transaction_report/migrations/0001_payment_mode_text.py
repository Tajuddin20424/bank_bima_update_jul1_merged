from django.db import migrations


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE transaction__mains "
                "MODIFY payment_mode VARCHAR(20) NULL"
            ),
            reverse_sql=(
                "ALTER TABLE transaction__mains "
                "MODIFY payment_mode BIGINT NULL"
            ),
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE transaction__details "
                "MODIFY payment_mode VARCHAR(20) NULL"
            ),
            reverse_sql=(
                "ALTER TABLE transaction__details "
                "MODIFY payment_mode BIGINT NULL"
            ),
        ),
    ]
