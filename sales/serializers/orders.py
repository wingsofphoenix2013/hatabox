from rest_framework import serializers

from sales.models import SalesOrder, SalesOrderComponent
from organizations.models import Organization
from inventory.models import Product


class SalesOrderComponentSerializer(serializers.ModelSerializer):
    inv_item_code = serializers.CharField(
        source="inv_item.internal_code",
        read_only=True,
    )
    inv_item_name = serializers.CharField(
        source="inv_item.name",
        read_only=True,
    )

    class Meta:
        model = SalesOrderComponent
        fields = [
            "id",
            "inv_item",
            "inv_item_code",
            "inv_item_name",
            "quantity",
            "source_type",
            "source_organization",
        ]


class SalesOrderSerializer(serializers.ModelSerializer):
    components = SalesOrderComponentSerializer(many=True, read_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            "id",
            "organization",
            "product",
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "comment",
            "components",
        ]
        read_only_fields = [
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "components",
        ]


class CreateSalesOrderSerializer(serializers.Serializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all()
    )
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )