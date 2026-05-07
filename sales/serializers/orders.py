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

    class Meta:
        model = SalesOrderComponent
        fields = [
            "id",
            "inv_item",
            "inv_item_code",
            "inv_item_name",
            "quantity",
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
    components = SalesOrderComponentSerializer(many=True, read_only=True)
    can_confirm = serializers.SerializerMethodField()
    customer_responsible_person_name = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrder
        fields = [
            "id",
            "organization",
            "product",
            "status",
            "can_confirm",
            "created_by",
            "created_at",
            "updated_at",
            "completed_at",
            "customer_responsible_person",
            "customer_responsible_person_name",
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
        
    def get_can_confirm(self, obj):
        return check_sales_order_can_confirm(obj)["can_confirm"]

    def get_customer_responsible_person_name(self, obj):
        if obj.customer_responsible_person is None:
            return None
        return str(obj.customer_responsible_person)


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


class SetCustomerComponentsSerializer(serializers.Serializer):
    component_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )