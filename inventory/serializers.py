from rest_framework import serializers

from .models import (
    InvUnit,
    InvItemCategory,
    InvItem,
    ProductFamily,
    ProductFamilyLibrary,
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
            "is_active",
            "created_at",
            "updated_at",
        ]


class ProductFamilyLibrarySerializer(serializers.ModelSerializer):
    attachment_type_display = serializers.CharField(
        source="get_attachment_type_display",
        read_only=True,
    )
    file_url = serializers.SerializerMethodField()
    product_family_code = serializers.CharField(
        source="product_family.code",
        read_only=True,
    )
    product_family_name = serializers.CharField(
        source="product_family.name",
        read_only=True,
    )

    class Meta:
        model = ProductFamilyLibrary
        fields = [
            "id",
            "product_family",
            "product_family_code",
            "product_family_name",
            "name",
            "description",
            "attachment_type",
            "attachment_type_display",
            "file",
            "file_url",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class ProductFamilySerializer(serializers.ModelSerializer):
    developer_display = serializers.CharField(
        source="get_developer_display",
        read_only=True,
    )
    library_items = ProductFamilyLibrarySerializer(many=True, read_only=True)

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
            "library_items",
        ]