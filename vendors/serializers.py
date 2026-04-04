from rest_framework import serializers
from .models import Vendor, VendorItem


class VendorSerializer(serializers.ModelSerializer):
    tax_type_name = serializers.CharField(source="tax_type.name", read_only=True)
    is_vat_payer = serializers.BooleanField(source="tax_type.is_vat_payer", read_only=True)
    is_profit_tax_payer = serializers.BooleanField(source="tax_type.is_profit_tax_payer", read_only=True)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "code",
            "name",
            "legal_name",
            "tax_type",
            "tax_type_name",
            "is_vat_payer",
            "is_profit_tax_payer",
            "edrpou",
            "ipn",
            "phone",
            "email",
            "logo",
            "is_active",
        ]


class VendorItemSerializer(serializers.ModelSerializer):
    vendor_code = serializers.CharField(source="vendor.code", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    item_internal_code = serializers.CharField(source="item.internal_code", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_description = serializers.CharField(source="item.description", read_only=True)
    item_category_id = serializers.IntegerField(source="item.category.id", read_only=True)
    item_category_name = serializers.CharField(source="item.category.name", read_only=True)
    item_unit_id = serializers.IntegerField(source="item.unit.id", read_only=True)
    item_unit_name = serializers.CharField(source="item.unit.name", read_only=True)
    item_unit_symbol = serializers.CharField(source="item.unit.symbol", read_only=True)

    brand_name = serializers.CharField(source="brand.name", read_only=True)
    country_of_origin_name = serializers.CharField(source="country_of_origin.name", read_only=True)
    country_of_origin_code = serializers.CharField(source="country_of_origin.code", read_only=True)

    class Meta:
        model = VendorItem
        fields = [
            "id",
            "vendor",
            "vendor_code",
            "vendor_name",
            "item",
            "item_internal_code",
            "item_name",
            "item_description",
            "item_category_id",
            "item_category_name",
            "item_unit_id",
            "item_unit_name",
            "item_unit_symbol",
            "vendor_sku",
            "name",
            "brand",
            "brand_name",
            "country_of_origin",
            "country_of_origin_name",
            "country_of_origin_code",
            "is_active",
        ]