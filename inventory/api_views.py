from django.db import models
from django.db.models import Sum

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import (
    InvUnit,
    InvItemCategory,
    InvItem,
    ProductFamily,
    ProductFamilyLibrary,
    Product,
    ProductLibrary,
    ProductStep,
    ProductStepLibrary,
    ProductStepItem,
)
from .serializers import (
    InvUnitSerializer,
    InvItemCategorySerializer,
    InvItemSerializer,
    InvItemOptionSerializer,
    ProductFamilySerializer,
    ProductFamilyLibrarySerializer,
    ProductSerializer,
    ProductLibrarySerializer,
    ProductStepSerializer,
    ProductStepLibrarySerializer,
    ProductStepItemSerializer,
    ProductMaterialPlanSerializer,
)


class InvUnitViewSet(ReadOnlyModelViewSet):
    queryset = InvUnit.objects.filter(is_active=True)
    serializer_class = InvUnitSerializer


class InvItemCategoryViewSet(ReadOnlyModelViewSet):
    queryset = InvItemCategory.objects.filter(is_active=True)
    serializer_class = InvItemCategorySerializer


class InvItemViewSet(ModelViewSet):
    queryset = InvItem.objects.filter(is_active=True)
    serializer_class = InvItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.select_related("category", "unit")

        category = self.request.query_params.getlist("category")
        if category:
            queryset = queryset.filter(category_id__in=category)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(internal_code__icontains=search)
            )

        return queryset

class InvItemOptionsView(ListAPIView):
    serializer_class = InvItemOptionSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = InvItem.objects.select_related("category", "unit").filter(is_active=True)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(internal_code__icontains=search)
            )

        return queryset.order_by("name", "id")

class ProductFamilyViewSet(ModelViewSet):
    queryset = ProductFamily.objects.filter(is_active=True)
    serializer_class = ProductFamilySerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.prefetch_related("library_items")

        developer = self.request.query_params.getlist("developer")
        if developer:
            queryset = queryset.filter(developer__in=developer)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
            )

        return queryset


class ProductFamilyLibraryViewSet(ModelViewSet):
    queryset = ProductFamilyLibrary.objects.filter(is_active=True).select_related("product_family")
    serializer_class = ProductFamilyLibrarySerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        product_family = self.request.query_params.getlist("product_family")
        if product_family:
            queryset = queryset.filter(product_family_id__in=product_family)

        attachment_type = self.request.query_params.getlist("attachment_type")
        if attachment_type:
            queryset = queryset.filter(attachment_type__in=attachment_type)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
                | models.Q(product_family__code__icontains=search)
                | models.Q(product_family__name__icontains=search)
            )

        return queryset
        
class ProductViewSet(ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related("product_family")
    serializer_class = ProductSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.prefetch_related("library_items")

        product_family = self.request.query_params.getlist("product_family")
        if product_family:
            queryset = queryset.filter(product_family_id__in=product_family)

        product_family_code = self.request.query_params.get("product_family_code")
        if product_family_code:
            queryset = queryset.filter(
                product_family__code__icontains=product_family_code
            )

        is_base_modification = self.request.query_params.get("is_base_modification")
        if is_base_modification is not None:
            value = is_base_modification.strip().lower()
            if value in ("true", "1"):
                queryset = queryset.filter(is_base_modification=True)
            elif value in ("false", "0"):
                queryset = queryset.filter(is_base_modification=False)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(version__icontains=search)
                | models.Q(description__icontains=search)
                | models.Q(product_family__code__icontains=search)
                | models.Q(product_family__name__icontains=search)
            )

        return queryset

    @action(detail=True, methods=["get"], url_path="material-plan")
    def material_plan(self, request, pk=None):
        product = self.get_object()

        step_items_queryset = (
            ProductStepItem.objects.filter(product_step__product=product)
            .select_related(
                "product_step",
                "inv_item",
                "inv_item__category",
                "inv_item__unit",
            )
            .order_by(
                "inv_item__name",
                "inv_item_id",
                "product_step__sort_order",
                "product_step_id",
            )
        )

        summary_map = {}
        for step_item in step_items_queryset:
            inv_item = step_item.inv_item
            product_step = step_item.product_step

            key = inv_item.id
            if key not in summary_map:
                summary_map[key] = {
                    "inv_item_id": inv_item.id,
                    "inv_item_internal_code": inv_item.internal_code,
                    "inv_item_name": inv_item.name,
                    "inv_item_category_id": inv_item.category_id,
                    "inv_item_category_name": inv_item.category.name,
                    "unit_id": inv_item.unit_id,
                    "unit_name": inv_item.unit.name,
                    "unit_symbol": inv_item.unit.symbol,
                    "total_quantity": step_item.quantity,
                    "steps": [],
                }
            else:
                summary_map[key]["total_quantity"] += step_item.quantity

            summary_map[key]["steps"].append(
                {
                    "product_step_id": product_step.id,
                    "product_step_name": product_step.name,
                    "sort_order": product_step.sort_order,
                    "quantity": step_item.quantity,
                }
            )

        summary_items = list(summary_map.values())
        summary_items.sort(key=lambda x: (x["inv_item_name"], x["inv_item_id"]))

        steps_queryset = (
            ProductStep.objects.filter(product=product)
            .prefetch_related("step_items__inv_item__category", "step_items__inv_item__unit")
            .order_by("sort_order", "id")
        )

        steps = []
        for step in steps_queryset:
            step_items = []
            for step_item in step.step_items.all():
                step_items.append(
                    {
                        "inv_item_id": step_item.inv_item_id,
                        "inv_item_internal_code": step_item.inv_item.internal_code,
                        "inv_item_name": step_item.inv_item.name,
                        "inv_item_category_id": step_item.inv_item.category_id,
                        "inv_item_category_name": step_item.inv_item.category.name,
                        "unit_id": step_item.inv_item.unit_id,
                        "unit_name": step_item.inv_item.unit.name,
                        "unit_symbol": step_item.inv_item.unit.symbol,
                        "quantity": step_item.quantity,
                    }
                )

            steps.append(
                {
                    "id": step.id,
                    "name": step.name,
                    "sort_order": step.sort_order,
                    "items": step_items,
                }
            )

        payload = {
            "product": {
                "id": product.id,
                "code": product.code,
                "version": product.version,
                "product_family_id": product.product_family_id,
                "product_family_code": product.product_family.code,
                "product_family_name": product.product_family.name,
            },
            "summary_items": summary_items,
            "steps": steps,
        }

        serializer = ProductMaterialPlanSerializer(payload)
        return Response(serializer.data)

class ProductLibraryViewSet(ModelViewSet):
    queryset = ProductLibrary.objects.filter(is_active=True).select_related(
        "product",
        "product__product_family",
    )
    serializer_class = ProductLibrarySerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        product = self.request.query_params.getlist("product")
        if product:
            queryset = queryset.filter(product_id__in=product)

        product_family = self.request.query_params.getlist("product_family")
        if product_family:
            queryset = queryset.filter(product__product_family_id__in=product_family)

        attachment_type = self.request.query_params.getlist("attachment_type")
        if attachment_type:
            queryset = queryset.filter(attachment_type__in=attachment_type)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
                | models.Q(product__code__icontains=search)
                | models.Q(product__version__icontains=search)
                | models.Q(product__product_family__code__icontains=search)
                | models.Q(product__product_family__name__icontains=search)
            )

        return queryset
        
class ProductStepViewSet(ModelViewSet):
    queryset = ProductStep.objects.select_related(
        "product",
        "product__product_family",
    )
    serializer_class = ProductStepSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset.prefetch_related("library_items", "step_items__inv_item__unit")

        product = self.request.query_params.getlist("product")
        if product:
            queryset = queryset.filter(product_id__in=product)

        product_family = self.request.query_params.getlist("product_family")
        if product_family:
            queryset = queryset.filter(product__product_family_id__in=product_family)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(product__code__icontains=search)
                | models.Q(product__version__icontains=search)
                | models.Q(product__product_family__code__icontains=search)
                | models.Q(product__product_family__name__icontains=search)
            )

        return queryset


class ProductStepLibraryViewSet(ModelViewSet):
    queryset = ProductStepLibrary.objects.filter(is_active=True).select_related(
        "product_step",
        "product_step__product",
        "product_step__product__product_family",
    )
    serializer_class = ProductStepLibrarySerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        product_step = self.request.query_params.getlist("product_step")
        if product_step:
            queryset = queryset.filter(product_step_id__in=product_step)

        product = self.request.query_params.getlist("product")
        if product:
            queryset = queryset.filter(product_step__product_id__in=product)

        product_family = self.request.query_params.getlist("product_family")
        if product_family:
            queryset = queryset.filter(product_step__product__product_family_id__in=product_family)

        attachment_type = self.request.query_params.getlist("attachment_type")
        if attachment_type:
            queryset = queryset.filter(attachment_type__in=attachment_type)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(description__icontains=search)
                | models.Q(product_step__name__icontains=search)
                | models.Q(product_step__product__code__icontains=search)
                | models.Q(product_step__product__version__icontains=search)
                | models.Q(product_step__product__product_family__code__icontains=search)
                | models.Q(product_step__product__product_family__name__icontains=search)
            )

        return queryset


class ProductStepItemViewSet(ModelViewSet):
    queryset = ProductStepItem.objects.select_related(
        "product_step",
        "product_step__product",
        "product_step__product__product_family",
        "inv_item",
        "inv_item__unit",
    )
    serializer_class = ProductStepItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        product_step = self.request.query_params.getlist("product_step")
        if product_step:
            queryset = queryset.filter(product_step_id__in=product_step)

        product = self.request.query_params.getlist("product")
        if product:
            queryset = queryset.filter(product_step__product_id__in=product)

        product_family = self.request.query_params.getlist("product_family")
        if product_family:
            queryset = queryset.filter(product_step__product__product_family_id__in=product_family)

        inv_item = self.request.query_params.getlist("inv_item")
        if inv_item:
            queryset = queryset.filter(inv_item_id__in=inv_item)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(inv_item__internal_code__icontains=search)
                | models.Q(inv_item__name__icontains=search)
                | models.Q(product_step__name__icontains=search)
                | models.Q(product_step__product__code__icontains=search)
                | models.Q(product_step__product__version__icontains=search)
            )

        return queryset