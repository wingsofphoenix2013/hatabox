from rest_framework import serializers
from .models import Vendor


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