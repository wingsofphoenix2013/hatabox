from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InvUnit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("symbol", models.CharField(max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
            ],
            options={
                "db_table": "inv_units",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="InvItemCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
            ],
            options={
                "db_table": "inv_item_categories",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="InvItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("internal_code", models.CharField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("image", models.ImageField(blank=True, db_column="image_path", null=True, upload_to="items/")),
                ("qr_item", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
                (
                    "category",
                    models.ForeignKey(
                        db_column="category_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="inventory.invitemcategory",
                    ),
                ),
                (
                    "unit",
                    models.ForeignKey(
                        db_column="unit_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="inventory.invunit",
                    ),
                ),
            ],
            options={
                "db_table": "inv_items",
                "ordering": ["name"],
            },
        ),
    ]