from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('hostelapp', '0003_delete_professional'),  # Changed to match your actual file
    ]

    operations = [

        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='Professional',
                ),
            ],
            database_operations=[],
        ),
    ]