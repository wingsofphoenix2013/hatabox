from django.utils import timezone

from rest_framework import serializers

from .models import (
    InvUnit,
    InvItemCategory,
    InvItem,
    ProductFamily,
    Product,
    ProductStep,
    ProductWork,
    ProductWorkItem,
    ProductStepItem,
    ProductAttachment,
)


class InvUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvUnit
        fields = "__all__"


class InvItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvItemCategory
        fields = "__all__"


class InvItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    unit_symbol = serializers.CharField(source="unit.symbol", read_only=True)

    class Meta:
        model = InvItem
        fields = [
            "id",
            "internal_code",
            "name",
            "description",
            "category",
            "category_name",
            "unit",
            "unit_name",
            "unit_symbol",
            "image",
            "qr_item",
            "requires_storage_place",
            "is_splittable",
            "is_required_for_step_start",
            "is_active",
            "created_at",
            "updated_at",
        ]


class InvItemOptionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    unit_symbol = serializers.CharField(source="unit.symbol", read_only=True)

    class Meta:
        model = InvItem
        fields = [
            "id",
            "name",
            "internal_code",
            "category_name",
            "unit_symbol",
            "description",
        ]

class ProductFamilySerializer(serializers.ModelSerializer):
    developer_display = serializers.CharField(
        source="get_developer_display",
        read_only=True,
    )

    class Meta:
        model = ProductFamily
        fields = [
            "id",
            "code",
            "name",
            "description",
            "developer",
            "developer_display",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ProductOptionSerializer(serializers.ModelSerializer):
    product_family_name = serializers.CharField(
        source="product_family.name",
        read_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "code",
            "product_family_name",
        ]


class ProductSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)
    development_started_at = serializers.DateField(required=False)
    development_finished_at = serializers.DateField(required=False, allow_null=True)

    development_status_display = serializers.CharField(
        source="get_development_status_display",
        read_only=True,
    )

    product_family_code = serializers.CharField(
        source="product_family.code",
        read_only=True,
    )
    product_family_name = serializers.CharField(
        source="product_family.name",
        read_only=True,
    )
    steps = serializers.SerializerMethodField()

    def get_steps(self, obj):
        return [
            {
                "id": step.id,
                "name": step.name,
                "sort_order": step.sort_order,
                "description": step.description,
                "works": [
                    {
                        "id": work.id,
                        "name": work.name,
                        "sort_order": work.sort_order,
                        "description": work.description,
                    }
                    for work in step.works.all()
                ],
            }
            for step in obj.steps.all()
        ]

    def validate(self, attrs):
        product_family = attrs.get("product_family") or getattr(self.instance, "product_family", None)
        version = attrs.get("version") or getattr(self.instance, "version", None)

        if product_family and version:
            queryset = Product.objects.filter(
                product_family=product_family,
                version=version,
            )

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({
                    "version": "Product with this version already exists in this product family."
                })

        return attrs

    def create(self, validated_data):
        product_family = validated_data["product_family"]
        version = validated_data["version"]

        validated_data["code"] = f"{product_family.code}-{version}"
        validated_data["development_status"] = Product.DevelopmentStatus.IN_DEVELOPMENT
        validated_data["development_started_at"] = timezone.localdate()
        validated_data["development_finished_at"] = None
        validated_data["hr_tracking"] = False

        return super().create(validated_data)

    class Meta:
        model = Product
        fields = [
            "id",
            "product_family",
            "product_family_code",
            "product_family_name",
            "version",
            "code",
            "description",
            "is_base_modification",
            "work_tracking",
            "hr_tracking",
            "development_status",
            "development_status_display",
            "development_started_at",
            "development_finished_at",
            "is_active",
            "created_at",
            "updated_at",
            "steps",
        ]
        

class ProductStepItemSerializer(serializers.ModelSerializer):
    inv_item_internal_code = serializers.CharField(
        source="inv_item.internal_code",
        read_only=True,
    )
    inv_item_name = serializers.CharField(
        source="inv_item.name",
        read_only=True,
    )
    inv_item_unit_id = serializers.IntegerField(
        source="inv_item.unit.id",
        read_only=True,
    )
    inv_item_unit_name = serializers.CharField(
        source="inv_item.unit.name",
        read_only=True,
    )
    inv_item_unit_symbol = serializers.CharField(
        source="inv_item.unit.symbol",
        read_only=True,
    )
    product_step_name = serializers.CharField(
        source="product_step.name",
        read_only=True,
    )
    product_step_sort_order = serializers.IntegerField(
        source="product_step.sort_order",
        read_only=True,
    )
    product_id = serializers.IntegerField(
        source="product_step.product.id",
        read_only=True,
    )
    product_code = serializers.CharField(
        source="product_step.product.code",
        read_only=True,
    )

    class Meta:
        model = ProductStepItem
        fields = [
            "id",
            "product_step",
            "product_step_name",
            "product_step_sort_order",
            "product_id",
            "product_code",
            "inv_item",
            "inv_item_internal_code",
            "inv_item_name",
            "inv_item_unit_id",
            "inv_item_unit_name",
            "inv_item_unit_symbol",
            "quantity",
            "created_at",
            "updated_at",
        ]


class ProductWorkItemSerializer(serializers.ModelSerializer):
    inv_item_internal_code = serializers.CharField(
        source="inv_item.internal_code",
        read_only=True,
    )
    inv_item_name = serializers.CharField(
        source="inv_item.name",
        read_only=True,
    )
    inv_item_unit_id = serializers.IntegerField(
        source="inv_item.unit.id",
        read_only=True,
    )
    inv_item_unit_name = serializers.CharField(
        source="inv_item.unit.name",
        read_only=True,
    )
    inv_item_unit_symbol = serializers.CharField(
        source="inv_item.unit.symbol",
        read_only=True,
    )

    class Meta:
        model = ProductWorkItem
        fields = [
            "id",
            "product_work",
            "inv_item",
            "inv_item_internal_code",
            "inv_item_name",
            "inv_item_unit_id",
            "inv_item_unit_name",
            "inv_item_unit_symbol",
            "quantity",
            "created_at",
            "updated_at",
        ]


class ProductAttachmentSerializer(serializers.ModelSerializer):
    attachment_type_display = serializers.CharField(
        source="get_attachment_type_display",
        read_only=True,
    )

    class Meta:
        model = ProductAttachment
        fields = [
            "id",
            "product",
            "product_step",
            "product_work",
            "file",
            "attachment_type",
            "attachment_type_display",
            "name",
            "description",
            "created_at",
        ]
        read_only_fields = [
            "created_at",
        ]


class ProductWorkSerializer(serializers.ModelSerializer):
    product_step_name = serializers.CharField(
        source="product_step.name",
        read_only=True,
    )
    product_step_sort_order = serializers.IntegerField(
        source="product_step.sort_order",
        read_only=True,
    )
    product_id = serializers.IntegerField(
        source="product_step.product.id",
        read_only=True,
    )
    product_code = serializers.CharField(
        source="product_step.product.code",
        read_only=True,
    )
    work_items = ProductWorkItemSerializer(many=True, read_only=True)

    class Meta:
        model = ProductWork
        fields = [
            "id",
            "product_step",
            "product_step_name",
            "product_step_sort_order",
            "product_id",
            "product_code",
            "name",
            "sort_order",
            "description",
            "created_at",
            "updated_at",
            "work_items",
        ]


class ProductStepSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(
        source="product.id",
        read_only=True,
    )
    product_code = serializers.CharField(
        source="product.code",
        read_only=True,
    )
    product_version = serializers.CharField(
        source="product.version",
        read_only=True,
    )
    product_family_id = serializers.IntegerField(
        source="product.product_family.id",
        read_only=True,
    )
    product_family_code = serializers.CharField(
        source="product.product_family.code",
        read_only=True,
    )
    product_family_name = serializers.CharField(
        source="product.product_family.name",
        read_only=True,
    )
    product_work_tracking = serializers.BooleanField(
        source="product.work_tracking",
        read_only=True,
    )
    product_development_status = serializers.CharField(
        source="product.development_status",
        read_only=True,
    )
    product_development_status_display = serializers.CharField(
        source="product.get_development_status_display",
        read_only=True,
    )
    step_items = ProductStepItemSerializer(many=True, read_only=True)
    works = ProductWorkSerializer(many=True, read_only=True)

    class Meta:
        model = ProductStep
        fields = [
            "id",
            "product",
            "product_id",
            "product_code",
            "product_version",
            "product_family_id",
            "product_family_code",
            "product_family_name",
            "product_work_tracking",
            "product_development_status",
            "product_development_status_display",
            "name",
            "sort_order",
            "description",
            "created_at",
            "updated_at",
            "step_items",
            "works",
        ]
        
class ProductMaterialPlanSummaryItemStepSerializer(serializers.Serializer):
    product_step_id = serializers.IntegerField()
    product_step_name = serializers.CharField()
    sort_order = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)


class ProductMaterialPlanSummaryItemSerializer(serializers.Serializer):
    inv_item_id = serializers.IntegerField()
    inv_item_internal_code = serializers.CharField()
    inv_item_name = serializers.CharField()
    inv_item_category_id = serializers.IntegerField()
    inv_item_category_name = serializers.CharField()
    unit_id = serializers.IntegerField()
    unit_name = serializers.CharField()
    unit_symbol = serializers.CharField()
    total_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    steps = ProductMaterialPlanSummaryItemStepSerializer(many=True)


class ProductMaterialPlanStepItemSerializer(serializers.Serializer):
    inv_item_id = serializers.IntegerField()
    inv_item_internal_code = serializers.CharField()
    inv_item_name = serializers.CharField()
    inv_item_category_id = serializers.IntegerField()
    inv_item_category_name = serializers.CharField()
    unit_id = serializers.IntegerField()
    unit_name = serializers.CharField()
    unit_symbol = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)


class ProductMaterialPlanStepSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    sort_order = serializers.IntegerField()
    items = ProductMaterialPlanStepItemSerializer(many=True)


class ProductMaterialPlanProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    version = serializers.CharField()
    work_tracking = serializers.BooleanField()
    development_status = serializers.CharField()
    development_status_display = serializers.CharField()
    product_family_id = serializers.IntegerField()
    product_family_code = serializers.CharField()
    product_family_name = serializers.CharField()


class ProductWorkMaterialPlanWorkSerializer(serializers.Serializer):
    product_work_id = serializers.IntegerField()
    product_work_name = serializers.CharField()
    product_work_sort_order = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)


class ProductWorkMaterialPlanStepSerializer(serializers.Serializer):
    product_step_id = serializers.IntegerField()
    product_step_name = serializers.CharField()
    product_step_sort_order = serializers.IntegerField()
    total_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    works = ProductWorkMaterialPlanWorkSerializer(many=True)


class ProductWorkMaterialPlanItemSerializer(serializers.Serializer):
    inv_item_id = serializers.IntegerField()
    inv_item_internal_code = serializers.CharField()
    inv_item_name = serializers.CharField()

    inv_item_category_id = serializers.IntegerField()
    inv_item_category_name = serializers.CharField()

    unit_id = serializers.IntegerField()
    unit_name = serializers.CharField()
    unit_symbol = serializers.CharField()

    total_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)

    steps = ProductWorkMaterialPlanStepSerializer(many=True)


class ProductWorkMaterialPlanSerializer(serializers.Serializer):
    product = ProductMaterialPlanProductSerializer()
    items = ProductWorkMaterialPlanItemSerializer(many=True)


class ProductStepMaterialPlanStepSerializer(serializers.Serializer):
    product_step_id = serializers.IntegerField()
    product_step_name = serializers.CharField()
    product_step_sort_order = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)


class ProductStepMaterialPlanItemSerializer(serializers.Serializer):
    inv_item_id = serializers.IntegerField()
    inv_item_internal_code = serializers.CharField()
    inv_item_name = serializers.CharField()

    inv_item_category_id = serializers.IntegerField()
    inv_item_category_name = serializers.CharField()

    unit_id = serializers.IntegerField()
    unit_name = serializers.CharField()
    unit_symbol = serializers.CharField()

    total_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)

    steps = ProductStepMaterialPlanStepSerializer(many=True)


class ProductStepMaterialPlanSerializer(serializers.Serializer):
    product = ProductMaterialPlanProductSerializer()
    items = ProductStepMaterialPlanItemSerializer(many=True)


class ProductMaterialPlanSerializer(serializers.Serializer):
    product = ProductMaterialPlanProductSerializer()
    summary_items = ProductMaterialPlanSummaryItemSerializer(many=True)
    steps = ProductMaterialPlanStepSerializer(many=True)