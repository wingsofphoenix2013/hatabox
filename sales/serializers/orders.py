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

class UpdateSalesOrderComponentSourceSerializer(serializers.Serializer):
    component_id = serializers.IntegerField(min_value=1)
    source_type = serializers.ChoiceField(
        choices=SalesOrderComponent.SourceType.choices,
    )
    source_organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        source_type = attrs["source_type"]
        source_organization = attrs.get("source_organization")

        if source_type == SalesOrderComponent.SourceType.STOCK:
            if source_organization is not None:
                raise serializers.ValidationError({
                    "source_organization": "Для джерела stock організація не вказується."
                })

        if source_type == SalesOrderComponent.SourceType.DONATED:
            if source_organization is None:
                raise serializers.ValidationError({
                    "source_organization": "Для цього типу джерела потрібно вказати організацію."
                })

        return attrs