from django.db import models
from django.db.models import Sum
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

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
from .serializers import (
    InvUnitSerializer,
    InvItemCategorySerializer,
    InvItemSerializer,
    InvItemOptionSerializer,
    ProductFamilySerializer,
    ProductSerializer,
    ProductOptionSerializer,
    ProductStepSerializer,
    ProductWorkSerializer,
    ProductWorkItemSerializer,
    ProductStepItemSerializer,
    ProductAttachmentSerializer,
    ProductMaterialPlanSerializer,
    ProductWorkMaterialPlanSerializer,
    ProductStepMaterialPlanSerializer,
    ProductAttachmentOverviewSerializer,
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
        queryset = self.queryset

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


class ProductOptionsView(ListAPIView):
    serializer_class = ProductOptionSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Product.objects.select_related("product_family").filter(is_active=True)

        product_family = self.request.query_params.getlist("product_family")
        if product_family:
            queryset = queryset.filter(product_family_id__in=product_family)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search)
                | models.Q(product_family__name__icontains=search)
            )

        return queryset.order_by("product_family__name", "code", "id")


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related("product_family")
    serializer_class = ProductSerializer
    permission_classes = [DjangoModelPermissions]

    def perform_update(self, serializer):
        product = self.get_object()

        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished products cannot be modified.")

        if (
            "work_tracking" in serializer.validated_data
            and serializer.validated_data["work_tracking"] != product.work_tracking
            and product.steps.exists()
        ):
            raise ValidationError("Work tracking cannot be changed after product steps are created.")

        serializer.save()

    def perform_destroy(self, instance):
        if instance.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished products cannot be deleted.")

        instance.delete()

    def get_queryset(self):
        queryset = self.queryset.prefetch_related("steps__works")

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

    @action(detail=False, methods=["get"], url_path="create-info")
    def create_info(self, request):
        product_family_id = request.query_params.get("product_family")
        version = request.query_params.get("version")

        if not product_family_id:
            raise ValidationError({"product_family": "This query parameter is required."})

        product_family = ProductFamily.objects.get(pk=product_family_id)

        base_product = Product.objects.filter(
            product_family=product_family,
            is_base_modification=True,
        ).first()

        generated_code = None
        version_available = None

        if version:
            generated_code = f"{product_family.code}-{version}"
            version_available = not Product.objects.filter(
                product_family=product_family,
                version=version,
            ).exists()

        return Response({
            "product_family_id": product_family.id,
            "product_family_code": product_family.code,
            "product_family_name": product_family.name,
            "base_version": base_product.version if base_product else None,
            "generated_code": generated_code,
            "version_available": version_available,
        })

    @action(detail=True, methods=["post"], url_path="finish-development")
    def finish_development(self, request, pk=None):
        product = self.get_object()

        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Product development is already finished.")

        product.development_status = Product.DevelopmentStatus.FINISHED
        product.development_finished_at = timezone.localdate()
        product.save(
            update_fields=[
                "development_status",
                "development_finished_at",
                "updated_at",
            ]
        )

        serializer = self.get_serializer(product)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="step-material-plan")
    def step_material_plan(self, request, pk=None):
        product = self.get_object()

        if product.work_tracking:
            raise ValidationError(
                "Step material plan is available only when work tracking is disabled."
            )

        step_items_queryset = (
            ProductStepItem.objects.filter(product_step__product=product)
            .select_related(
                "product_step",
                "inv_item",
                "inv_item__category",
                "inv_item__unit",
            )
            .order_by(
                "inv_item__internal_code",
                "inv_item_id",
                "product_step__sort_order",
                "product_step_id",
            )
        )

        items_map = {}

        for step_item in step_items_queryset:
            inv_item = step_item.inv_item
            product_step = step_item.product_step

            item_key = inv_item.id

            if item_key not in items_map:
                items_map[item_key] = {
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
                items_map[item_key]["total_quantity"] += step_item.quantity

            items_map[item_key]["steps"].append(
                {
                    "product_step_id": product_step.id,
                    "product_step_name": product_step.name,
                    "product_step_sort_order": product_step.sort_order,
                    "quantity": step_item.quantity,
                }
            )

        items = list(items_map.values())

        items.sort(
            key=lambda x: (
                x["inv_item_internal_code"],
                x["inv_item_id"],
            )
        )

        payload = {
            "product": {
                "id": product.id,
                "code": product.code,
                "version": product.version,
                "description": product.description,
                "work_tracking": product.work_tracking,
                "hr_tracking": product.hr_tracking,
                "development_status": product.development_status,
                "development_status_display": product.get_development_status_display(),
                "development_started_at": product.development_started_at,
                "development_finished_at": product.development_finished_at,
                "is_base_modification": product.is_base_modification,
                "product_family_id": product.product_family_id,
                "product_family_code": product.product_family.code,
                "product_family_name": product.product_family.name,
            },
            "items": items,
        }

        serializer = ProductStepMaterialPlanSerializer(payload)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="work-material-plan")
    def work_material_plan(self, request, pk=None):
        product = self.get_object()

        if not product.work_tracking:
            raise ValidationError("Work material plan is available only when work tracking is enabled.")

        work_items_queryset = (
            ProductWorkItem.objects.filter(product_work__product_step__product=product)
            .select_related(
                "product_work",
                "product_work__product_step",
                "inv_item",
                "inv_item__category",
                "inv_item__unit",
            )
            .order_by(
                "inv_item__name",
                "inv_item_id",
                "product_work__product_step__sort_order",
                "product_work__product_step_id",
                "product_work__sort_order",
                "product_work_id",
            )
        )

        items_map = {}

        for work_item in work_items_queryset:
            inv_item = work_item.inv_item
            product_work = work_item.product_work
            product_step = product_work.product_step

            item_key = inv_item.id
            if item_key not in items_map:
                items_map[item_key] = {
                    "inv_item_id": inv_item.id,
                    "inv_item_internal_code": inv_item.internal_code,
                    "inv_item_name": inv_item.name,
                    "inv_item_category_id": inv_item.category_id,
                    "inv_item_category_name": inv_item.category.name,
                    "unit_id": inv_item.unit_id,
                    "unit_name": inv_item.unit.name,
                    "unit_symbol": inv_item.unit.symbol,
                    "total_quantity": work_item.quantity,
                    "steps_map": {},
                }
            else:
                items_map[item_key]["total_quantity"] += work_item.quantity

            step_key = product_step.id
            if step_key not in items_map[item_key]["steps_map"]:
                items_map[item_key]["steps_map"][step_key] = {
                    "product_step_id": product_step.id,
                    "product_step_name": product_step.name,
                    "product_step_sort_order": product_step.sort_order,
                    "total_quantity": work_item.quantity,
                    "works": [],
                }
            else:
                items_map[item_key]["steps_map"][step_key]["total_quantity"] += work_item.quantity

            items_map[item_key]["steps_map"][step_key]["works"].append(
                {
                    "product_work_id": product_work.id,
                    "product_work_name": product_work.name,
                    "product_work_sort_order": product_work.sort_order,
                    "quantity": work_item.quantity,
                }
            )

        items = []
        for item in items_map.values():
            steps = list(item["steps_map"].values())
            steps.sort(key=lambda x: (x["product_step_sort_order"], x["product_step_id"]))

            item.pop("steps_map")
            item["steps"] = steps
            items.append(item)

        items.sort(
            key=lambda x: (
                x["inv_item_internal_code"],
                x["inv_item_id"],
            )
        )

        payload = {
            "product": {
                "id": product.id,
                "code": product.code,
                "version": product.version,
                "description": product.description,
                "work_tracking": product.work_tracking,
                "hr_tracking": product.hr_tracking,
                "development_status": product.development_status,
                "development_status_display": product.get_development_status_display(),
                "development_started_at": product.development_started_at,
                "development_finished_at": product.development_finished_at,
                "is_base_modification": product.is_base_modification,
                "product_family_id": product.product_family_id,
                "product_family_code": product.product_family.code,
                "product_family_name": product.product_family.name,
            },
            "items": items,
        }

        serializer = ProductWorkMaterialPlanSerializer(payload)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="material-plan")
    def material_plan(self, request, pk=None):
        product = self.get_object()

        if product.work_tracking:
            work_items_queryset = (
                ProductWorkItem.objects.filter(product_work__product_step__product=product)
                .select_related(
                    "product_work",
                    "product_work__product_step",
                    "inv_item",
                    "inv_item__category",
                    "inv_item__unit",
                )
                .order_by(
                    "inv_item__name",
                    "inv_item_id",
                    "product_work__product_step__sort_order",
                    "product_work__product_step_id",
                )
            )

            summary_map = {}
            for work_item in work_items_queryset:
                inv_item = work_item.inv_item
                product_step = work_item.product_work.product_step

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
                        "total_quantity": work_item.quantity,
                        "steps": [],
                    }
                else:
                    summary_map[key]["total_quantity"] += work_item.quantity

                summary_map[key]["steps"].append(
                    {
                        "product_step_id": product_step.id,
                        "product_step_name": product_step.name,
                        "sort_order": product_step.sort_order,
                        "quantity": work_item.quantity,
                    }
                )

            summary_items = list(summary_map.values())
            summary_items.sort(key=lambda x: (x["inv_item_name"], x["inv_item_id"]))

            steps_queryset = (
                ProductStep.objects.filter(product=product)
                .prefetch_related(
                    "works__work_items__inv_item__category",
                    "works__work_items__inv_item__unit",
                )
                .order_by("sort_order", "id")
            )

            steps = []
            for step in steps_queryset:
                step_items_map = {}

                for work in step.works.all():
                    for work_item in work.work_items.all():
                        inv_item = work_item.inv_item
                        key = inv_item.id

                        if key not in step_items_map:
                            step_items_map[key] = {
                                "inv_item_id": inv_item.id,
                                "inv_item_internal_code": inv_item.internal_code,
                                "inv_item_name": inv_item.name,
                                "inv_item_category_id": inv_item.category_id,
                                "inv_item_category_name": inv_item.category.name,
                                "unit_id": inv_item.unit_id,
                                "unit_name": inv_item.unit.name,
                                "unit_symbol": inv_item.unit.symbol,
                                "quantity": work_item.quantity,
                            }
                        else:
                            step_items_map[key]["quantity"] += work_item.quantity

                steps.append(
                    {
                        "id": step.id,
                        "name": step.name,
                        "sort_order": step.sort_order,
                        "items": list(step_items_map.values()),
                    }
                )
        else:
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
                .prefetch_related(
                    "step_items__inv_item__category",
                    "step_items__inv_item__unit",
                )
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
                "work_tracking": product.work_tracking,
                "development_status": product.development_status,
                "development_status_display": product.get_development_status_display(),
                "product_family_id": product.product_family_id,
                "product_family_code": product.product_family.code,
                "product_family_name": product.product_family.name,
            },
            "summary_items": summary_items,
            "steps": steps,
        }

        serializer = ProductMaterialPlanSerializer(payload)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="attachments-overview")
    def attachments_overview(self, request, pk=None):
        product = self.get_object()

        attachments = (
            ProductAttachment.objects.filter(
                models.Q(product=product)
                | models.Q(product_step__product=product)
                | models.Q(product_work__product_step__product=product)
            )
            .select_related(
                "product_step",
                "product_work",
                "product_work__product_step",
            )
            .order_by("-created_at", "-id")
        )

        steps = (
            ProductStep.objects.filter(product=product)
            .prefetch_related("works")
            .order_by("sort_order", "id")
        )

        groups_map = {
            attachment_type: {
                "attachment_type": attachment_type,
                "attachment_type_display": label,
                "product_attachments": [],
                "steps": [],
            }
            for attachment_type, label in ProductAttachment.AttachmentTypeChoices.choices
        }

        for step in steps:
            works = [
                {
                    "id": work.id,
                    "name": work.name,
                    "sort_order": work.sort_order,
                    "attachments": [],
                }
                for work in step.works.all()
            ]

            for group in groups_map.values():
                group["steps"].append({
                    "id": step.id,
                    "name": step.name,
                    "sort_order": step.sort_order,
                    "attachments": [],
                    "works": [
                        {
                            "id": work["id"],
                            "name": work["name"],
                            "sort_order": work["sort_order"],
                            "attachments": [],
                        }
                        for work in works
                    ],
                })

        for attachment in attachments:
            attachment_data = {
                "id": attachment.id,
                "file": attachment.file,
                "attachment_type": attachment.attachment_type,
                "attachment_type_display": attachment.get_attachment_type_display(),
                "name": attachment.name,
                "description": attachment.description,
                "created_at": attachment.created_at,
            }

            group = groups_map[attachment.attachment_type]

            if attachment.product_id:
                group["product_attachments"].append(attachment_data)
                continue

            if attachment.product_step_id:
                for step in group["steps"]:
                    if step["id"] == attachment.product_step_id:
                        step["attachments"].append(attachment_data)
                        break

                continue

            if attachment.product_work_id:
                product_work = attachment.product_work

                for step in group["steps"]:
                    if step["id"] != product_work.product_step_id:
                        continue

                    for work in step["works"]:
                        if work["id"] == product_work.id:
                            work["attachments"].append(attachment_data)
                            break

                    break

        attachment_groups = []

        for group in groups_map.values():
            steps = []

            for step in group["steps"]:
                works = [
                    work
                    for work in step["works"]
                    if work["attachments"]
                ]

                if step["attachments"] or works:
                    steps.append({
                        "id": step["id"],
                        "name": step["name"],
                        "sort_order": step["sort_order"],
                        "attachments": step["attachments"],
                        "works": works,
                    })

            if group["product_attachments"] or steps:
                attachment_groups.append({
                    "attachment_type": group["attachment_type"],
                    "attachment_type_display": group["attachment_type_display"],
                    "product_attachments": group["product_attachments"],
                    "steps": steps,
                })

        payload = {
            "product": {
                "id": product.id,
                "code": product.code,
                "version": product.version,
                "work_tracking": product.work_tracking,
                "development_status": product.development_status,
                "development_status_display": product.get_development_status_display(),
                "product_family_id": product.product_family_id,
                "product_family_code": product.product_family.code,
                "product_family_name": product.product_family.name,
            },
            "attachment_groups": attachment_groups,
        }

        serializer = ProductAttachmentOverviewSerializer(payload)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="attachment-targets")
    def attachment_targets(self, request, pk=None):
        product = self.get_object()

        steps = (
            ProductStep.objects.filter(product=product)
            .prefetch_related("works")
            .order_by("sort_order", "id")
        )

        payload = {
            "product": {
                "id": product.id,
                "target_type": "product",
                "code": product.code,
                "version": product.version,
                "label": product.code,
            },
            "steps": [
                {
                    "id": step.id,
                    "target_type": "step",
                    "name": step.name,
                    "sort_order": step.sort_order,
                    "label": f"{step.sort_order}. {step.name}",
                    "works": [
                        {
                            "id": work.id,
                            "target_type": "work",
                            "name": work.name,
                            "sort_order": work.sort_order,
                            "label": f"{step.sort_order}.{work.sort_order}. {work.name}",
                        }
                        for work in step.works.all()
                    ],
                }
                for step in steps
            ],
        }

        return Response(payload)

        
class ProductStepViewSet(ModelViewSet):
    queryset = ProductStep.objects.select_related(
        "product",
        "product__product_family",
    )
    serializer_class = ProductStepSerializer
    permission_classes = [DjangoModelPermissions]

    @action(detail=False, methods=["get"], url_path="used-sort-orders")
    def used_sort_orders(self, request):
        product_id = request.query_params.get("product")

        if not product_id:
            raise ValidationError({"product": "This query parameter is required."})

        sort_orders = list(
            ProductStep.objects.filter(product_id=product_id)
            .order_by("sort_order")
            .values_list("sort_order", flat=True)
        )

        return Response({
            "product": int(product_id),
            "used_sort_orders": sort_orders,
        })

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        steps = request.data.get("steps", [])

        if not steps:
            raise ValidationError({"steps": "This field is required."})

        for index, step_id in enumerate(steps, start=1):
            ProductStep.objects.filter(pk=step_id).update(
                sort_order=1000000 + index
            )

        for index, step_id in enumerate(steps, start=1):
            ProductStep.objects.filter(pk=step_id).update(
                sort_order=index
            )

        return Response({"success": True})

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]

        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished product steps cannot be modified.")

        serializer.save()

    def perform_update(self, serializer):
        if self.get_object().product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished product steps cannot be modified.")

        serializer.save()

    def perform_destroy(self, instance):
        if instance.product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished product steps cannot be modified.")

        instance.delete()

    def get_queryset(self):
        queryset = self.queryset.prefetch_related("step_items__inv_item__unit")

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


class ProductWorkViewSet(ModelViewSet):
    queryset = ProductWork.objects.select_related(
        "product_step",
        "product_step__product",
        "product_step__product__product_family",
    ).prefetch_related(
        "work_items__inv_item__unit",
    )
    serializer_class = ProductWorkSerializer
    permission_classes = [DjangoModelPermissions]

    @action(detail=False, methods=["get"], url_path="used-sort-orders")
    def used_sort_orders(self, request):
        product_step_id = request.query_params.get("product_step")

        if not product_step_id:
            raise ValidationError({"product_step": "This query parameter is required."})

        sort_orders = list(
            ProductWork.objects.filter(product_step_id=product_step_id)
            .order_by("sort_order")
            .values_list("sort_order", flat=True)
        )

        return Response({
            "product_step": int(product_step_id),
            "used_sort_orders": sort_orders,
        })

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        works = request.data.get("works", [])

        if not works:
            raise ValidationError({"works": "This field is required."})

        for index, work_id in enumerate(works, start=1):
            ProductWork.objects.filter(pk=work_id).update(
                sort_order=1000000 + index
            )

        for index, work_id in enumerate(works, start=1):
            ProductWork.objects.filter(pk=work_id).update(
                sort_order=index
            )

        return Response({"success": True})

    def perform_create(self, serializer):
        product_step = serializer.validated_data["product_step"]
        product = product_step.product

        if not product.work_tracking:
            raise ValidationError("Work tracking is disabled for this product.")

        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished products cannot be modified.")

        serializer.save()

    def perform_update(self, serializer):
        product = self.get_object().product_step.product

        if not product.work_tracking:
            raise ValidationError("Work tracking is disabled for this product.")

        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished products cannot be modified.")

        serializer.save()

    def perform_destroy(self, instance):
        product = instance.product_step.product

        if not product.work_tracking:
            raise ValidationError("Work tracking is disabled for this product.")

        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished products cannot be modified.")

        instance.delete()

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
            queryset = queryset.filter(
                product_step__product__product_family_id__in=product_family
            )

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(product_step__name__icontains=search)
                | models.Q(product_step__product__code__icontains=search)
            )

        return queryset


class ProductWorkItemViewSet(ModelViewSet):
    queryset = ProductWorkItem.objects.select_related(
        "product_work",
        "product_work__product_step",
        "product_work__product_step__product",
        "product_work__product_step__product__product_family",
        "inv_item",
        "inv_item__unit",
    )
    serializer_class = ProductWorkItemSerializer
    permission_classes = [DjangoModelPermissions]

    def perform_create(self, serializer):
        product_work = serializer.validated_data["product_work"]
        product = product_work.product_step.product

        if not product.work_tracking:
            raise ValidationError("Work tracking is disabled for this product.")

        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished products cannot be modified.")

        serializer.save()

    def perform_update(self, serializer):
        product = self.get_object().product_work.product_step.product

        if not product.work_tracking:
            raise ValidationError("Work tracking is disabled for this product.")

        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished products cannot be modified.")

        serializer.save()

    def perform_destroy(self, instance):
        product = instance.product_work.product_step.product

        if not product.work_tracking:
            raise ValidationError("Work tracking is disabled for this product.")

        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished products cannot be modified.")

        instance.delete()

    def get_queryset(self):
        queryset = self.queryset

        product_work = self.request.query_params.getlist("product_work")
        if product_work:
            queryset = queryset.filter(product_work_id__in=product_work)

        product_step = self.request.query_params.getlist("product_step")
        if product_step:
            queryset = queryset.filter(product_work__product_step_id__in=product_step)

        product = self.request.query_params.getlist("product")
        if product:
            queryset = queryset.filter(product_work__product_step__product_id__in=product)

        inv_item = self.request.query_params.getlist("inv_item")
        if inv_item:
            queryset = queryset.filter(inv_item_id__in=inv_item)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(inv_item__internal_code__icontains=search)
                | models.Q(inv_item__name__icontains=search)
                | models.Q(product_work__name__icontains=search)
                | models.Q(product_work__product_step__name__icontains=search)
                | models.Q(product_work__product_step__product__code__icontains=search)
            )

        return queryset


class ProductAttachmentViewSet(ModelViewSet):
    queryset = ProductAttachment.objects.select_related(
        "product",
        "product_step",
        "product_step__product",
        "product_work",
        "product_work__product_step",
        "product_work__product_step__product",
    )
    serializer_class = ProductAttachmentSerializer
    permission_classes = [DjangoModelPermissions]
    parser_classes = [MultiPartParser, FormParser]

    @action(detail=False, methods=["post"], url_path="bulk-upload")
    def bulk_upload(self, request):
        files = request.FILES.getlist("files")

        if not files:
            raise ValidationError({"files": "This field is required."})

        base_data = {
            "product": request.data.get("product"),
            "product_step": request.data.get("product_step"),
            "product_work": request.data.get("product_work"),
            "attachment_type": request.data.get("attachment_type"),
        }

        created_items = []

        for file in files:
            serializer = self.get_serializer(
                data={
                    **base_data,
                    "file": file,
                }
            )
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            created_items.append(serializer.data)

        return Response(created_items)

    def _get_attachment_product(self, attachment):
        if attachment.product_id:
            return attachment.product

        if attachment.product_step_id:
            return attachment.product_step.product

        if attachment.product_work_id:
            return attachment.product_work.product_step.product

        return None

    def _validate_product_not_finished(self, product):
        if product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished product attachments cannot be modified.")

    def perform_create(self, serializer):
        validated_data = serializer.validated_data

        product = validated_data.get("product")

        if product is None and validated_data.get("product_step"):
            product = validated_data["product_step"].product

        if product is None and validated_data.get("product_work"):
            product = validated_data["product_work"].product_step.product

        self._validate_product_not_finished(product)

        serializer.save()

    def perform_update(self, serializer):
        forbidden_fields = {
            "product",
            "product_step",
            "product_work",
            "file",
            "attachment_type",
        }

        if forbidden_fields.intersection(serializer.validated_data.keys()):
            raise ValidationError(
                "Only name and description can be changed after attachment creation."
            )

        product = self._get_attachment_product(self.get_object())
        self._validate_product_not_finished(product)

        serializer.save()

    def perform_destroy(self, instance):
        product = self._get_attachment_product(instance)
        self._validate_product_not_finished(product)

        instance.delete()

    def get_queryset(self):
        queryset = self.queryset

        product = self.request.query_params.getlist("product")
        if product:
            queryset = queryset.filter(
                models.Q(product_id__in=product)
                | models.Q(product_step__product_id__in=product)
                | models.Q(product_work__product_step__product_id__in=product)
            )

        product_step = self.request.query_params.getlist("product_step")
        if product_step:
            queryset = queryset.filter(
                models.Q(product_step_id__in=product_step)
                | models.Q(product_work__product_step_id__in=product_step)
            )

        product_work = self.request.query_params.getlist("product_work")
        if product_work:
            queryset = queryset.filter(product_work_id__in=product_work)

        attachment_type = self.request.query_params.getlist("attachment_type")
        if attachment_type:
            queryset = queryset.filter(attachment_type__in=attachment_type)

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

    def perform_create(self, serializer):
        product_step = serializer.validated_data["product_step"]

        if product_step.product.work_tracking:
            raise ValidationError("Step items are not available when work tracking is enabled.")

        if product_step.product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished product step items cannot be modified.")

        serializer.save()

    def perform_update(self, serializer):
        if self.get_object().product_step.product.work_tracking:
            raise ValidationError("Step items are not available when work tracking is enabled.")

        if self.get_object().product_step.product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished product step items cannot be modified.")

        serializer.save()

    def perform_destroy(self, instance):
        if instance.product_step.product.work_tracking:
            raise ValidationError("Step items are not available when work tracking is enabled.")

        if instance.product_step.product.development_status == Product.DevelopmentStatus.FINISHED:
            raise ValidationError("Finished product step items cannot be modified.")

        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("This step item is already used and cannot be deleted.")

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