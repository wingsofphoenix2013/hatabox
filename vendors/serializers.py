from rest_framework import serializers
from .models import Vendor, VendorItem, VendorPaymentDetails


class VendorSerializer(serializers.ModelSerializer):
    tax_type_name = serializers.CharField(source="tax_type.name", read_only=True)
    is_vat_payer = serializers.BooleanField(source="tax_type.is_vat_payer", read_only=True)
    is_profit_tax_payer = serializers.BooleanField(source="tax_type.is_profit_tax_payer", read_only=True)

    item_category_ids = serializers.SerializerMethodField()
    item_category_names = serializers.SerializerMethodField()

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
            "vat",
            "website",
            "logo",
            "is_active",
            "item_category_ids",
            "item_category_names",
        ]

    def _get_sorted_unique_categories(self, obj):
        vendor_items = getattr(obj, "active_vendor_items_for_categories", [])

        categories_map = {}
        for vendor_item in vendor_items:
            item = getattr(vendor_item, "item", None)
            if not item or not getattr(item, "is_active", False):
                continue

            category = getattr(item, "category", None)
            if not category:
                continue

            categories_map[category.id] = category.name

        return sorted(categories_map.items(), key=lambda x: (x[1], x[0]))

    def get_item_category_ids(self, obj):
        categories = self._get_sorted_unique_categories(obj)
        return [category_id for category_id, _ in categories]

    def get_item_category_names(self, obj):
        categories = self._get_sorted_unique_categories(obj)
        return [category_name for _, category_name in categories]

class VendorPaymentDetailsSerializer(serializers.ModelSerializer):
    vendor_code = serializers.CharField(source="vendor.code", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = VendorPaymentDetails
        fields = [
            "id",
            "vendor",
            "vendor_code",
            "vendor_name",
            "label",
            "iban",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
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