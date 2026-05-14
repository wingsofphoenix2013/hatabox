from rest_framework import serializers

from sales.models import SalesOrder, SalesOrderComponent, SalesOrderIssue
from sales.services.orders import check_sales_order_can_confirm
from organizations.models import Organization, Person, OrganizationPersonAssignment
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

    open_confirmation_issues_count = serializers.IntegerField(
        read_only=True,
    )

    open_critical_confirmation_issues_count = serializers.IntegerField(
        read_only=True,
    )

    has_open_confirmation_issues = serializers.SerializerMethodField()

    can_confirm_now = serializers.SerializerMethodField()

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
            "open_confirmation_issues_count",
            "open_critical_confirmation_issues_count",
            "has_open_confirmation_issues",
            "can_confirm_now",
        ]

    def get_has_open_confirmation_issues(self, obj):
        return obj.open_confirmation_issues_count > 0

    def get_can_confirm_now(self, obj):
        return obj.open_critical_confirmation_issues_count == 0


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
        return not obj.issues.filter(
            stage=SalesOrderIssue.Stage.CONFIRMATION,
            status=SalesOrderIssue.Status.OPEN,
            severity=SalesOrderIssue.Severity.CRITICAL,
        ).exists()
        
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


class SalesOrderProductionReadinessIssueSerializer(serializers.Serializer):
    issue = serializers.IntegerField(read_only=True)
    severity = serializers.CharField(read_only=True)

    inv_item = serializers.IntegerField(read_only=True)
    inv_item_code = serializers.CharField(read_only=True)
    inv_item_name = serializers.CharField(read_only=True)

    missing_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    unit_symbol = serializers.CharField(read_only=True)

    is_required_for_step_start = serializers.BooleanField(read_only=True)

    message = serializers.CharField(read_only=True)
    last_checked_at = serializers.DateTimeField(read_only=True)


class SalesOrderProductionReadinessStepSerializer(serializers.Serializer):
    production_order_step = serializers.IntegerField(read_only=True)
    sequence_number = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)

    can_be_confirmed = serializers.BooleanField(read_only=True)

    open_critical_issues_count = serializers.IntegerField(read_only=True)
    open_non_critical_issues_count = serializers.IntegerField(read_only=True)

    issues = SalesOrderProductionReadinessIssueSerializer(
        many=True,
        read_only=True,
    )


class SalesOrderProductionReadinessSummarySerializer(serializers.Serializer):
    next_step = serializers.IntegerField(read_only=True, allow_null=True)
    next_step_name = serializers.CharField(read_only=True, allow_null=True)
    can_confirm_next_step = serializers.BooleanField(read_only=True)

    open_critical_issues_count = serializers.IntegerField(read_only=True)
    open_non_critical_issues_count = serializers.IntegerField(read_only=True)


class SalesOrderProductionReadinessSerializer(serializers.Serializer):
    sales_order = serializers.IntegerField(read_only=True)
    production_order = serializers.IntegerField(read_only=True, allow_null=True)

    summary = SalesOrderProductionReadinessSummarySerializer(read_only=True)

    steps = SalesOrderProductionReadinessStepSerializer(
        many=True,
        read_only=True,
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
    
