from rest_framework import serializers

from sales.models import SalesOrder, SalesOrderComponent
from sales.services.orders import check_sales_order_can_confirm
from organizations.models import Organization, Person, OrganizationPersonAssignment
from inventory.models import Product


class SalesOrderComponentSerializer(serializers.ModelSerializer):
    is_required_for_start = serializers.BooleanField(read_only=True)
    inv_item_code = serializers.CharField(
        source="inv_item.internal_code",
        read_only=True,
    )
    inv_item_name = serializers.CharField(
        source="inv_item.name",
        read_only=True,
    )
    inv_item_unit_symbol = serializers.CharField(
        source="inv_item.unit.symbol",
        read_only=True,
    )

    class Meta:
        model = SalesOrderComponent
        fields = [
            "id",
            "inv_item",
            "inv_item_code",
            "inv_item_name",
            "inv_item_unit_symbol",
            "quantity",
            "fulfillment_mode",
            "is_required_for_start",
        ]


class SalesOrderListSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )
    product_code = serializers.CharField(
        source="product.code",
        read_only=True,
    )
    product_family_name = serializers.CharField(
        source="product.product_family.name",
        read_only=True,
    )

    class Meta:
        model = SalesOrder
        fields = [
            "id",
            "organization",
            "organization_name",
            "product",
            "product_code",
            "product_family_name",
            "status",
            "created_by",
            "created_at",
            "completed_at",
            "customer_responsible_person",
            "comment",
        ]

class SalesOrderSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )
    product_code = serializers.CharField(
        source="product.code",
        read_only=True,
    )
    product_family_name = serializers.CharField(
        source="product.product_family.name",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )
    customer_responsible_person_name = serializers.SerializerMethodField()
    can_try_confirm = serializers.SerializerMethodField()
    has_warehouse_shortages = serializers.SerializerMethodField()
    warehouse_shortages_last_checked_at = serializers.SerializerMethodField()
    warehouse_shortages = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrder
        fields = [
            "id",
            "organization",
            "organization_name",
            "product",
            "product_code",
            "product_family_name",
            "status",
            "status_display",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "completed_at",
            "customer_responsible_person",
            "customer_responsible_person_name",
            "comment",
            "can_try_confirm",
            "has_warehouse_shortages",
            "warehouse_shortages_last_checked_at",
            "warehouse_shortages",
        ]
        read_only_fields = [
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_customer_responsible_person_name(self, obj):
        if obj.customer_responsible_person is None:
            return None
        return str(obj.customer_responsible_person)

    def get_can_try_confirm(self, obj):
        return not obj.warehouse_shortages.filter(
            is_required_for_start=True,
        ).exists()

    def get_has_warehouse_shortages(self, obj):
        return obj.warehouse_shortages.exists()

    def get_warehouse_shortages_last_checked_at(self, obj):
        shortage = obj.warehouse_shortages.order_by(
            "-last_checked_at",
            "-updated_at",
        ).first()

        if shortage is None:
            return None

        return shortage.last_checked_at or shortage.updated_at

    def get_warehouse_shortages(self, obj):
        return [
            {
                "id": shortage.id,
                "sales_order_component": shortage.sales_order_component_id,
                "inv_item": shortage.inv_item_id,
                "inv_item_code": shortage.inv_item.internal_code,
                "inv_item_name": shortage.inv_item.name,
                "fulfillment_mode": shortage.fulfillment_mode,
                "organization": shortage.organization_id,
                "missing_quantity": shortage.missing_quantity,
                "is_required_for_start": shortage.is_required_for_start,
                "last_checked_at": shortage.last_checked_at,
            }
            for shortage in obj.warehouse_shortages.select_related("inv_item").all()
        ]
        
class CreateSalesOrderSerializer(serializers.Serializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all()
    )
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )
    customer_responsible_person = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        required=False,
        allow_null=True,
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        organization = attrs["organization"]
        person = attrs.get("customer_responsible_person")

        if person is not None:
            exists = OrganizationPersonAssignment.objects.filter(
                organization=organization,
                person=person,
                is_current=True,
            ).exists()

            if not exists:
                raise serializers.ValidationError({
                    "customer_responsible_person": "Особа не належить до організації або не є актуальною."
                })

        return attrs

class UpdateSalesOrderComponentSourceSerializer(serializers.Serializer):
    component_id = serializers.IntegerField(min_value=1)
    fulfillment_mode = serializers.ChoiceField(
        choices=SalesOrderComponent.FulfillmentMode.choices,
    )


class SetCustomerComponentsSerializer(serializers.Serializer):
    component_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )


class UpdateSalesOrderDetailsSerializer(serializers.Serializer):
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    customer_responsible_person = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        sales_order = self.context["sales_order"]
        person = attrs.get("customer_responsible_person")

        if person is not None:
            exists = OrganizationPersonAssignment.objects.filter(
                organization=sales_order.organization,
                person=person,
                is_current=True,
            ).exists()

            if not exists:
                raise serializers.ValidationError({
                    "customer_responsible_person": "Особа не належить до організації або не є актуальною."
                })

        return attrs
    
