from django.core.exceptions import ValidationError
from django.db import models

from reference.models import TaxType


class Organization(models.Model):
    class Type(models.TextChoices):
        MILITARY = "military", "Military"
        COMMERCIAL = "commercial", "Commercial"
        CHARITY = "charity", "Charity"
        VENDOR = "vendor", "Vendor"

    name = models.CharField(max_length=255, verbose_name="Назва")
    legal_name = models.CharField(max_length=255, verbose_name="Юридична назва")
    type = models.CharField(
        max_length=32,
        choices=Type.choices,
        verbose_name="Тип організації",
    )
    edrpou = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="ЄДРПОУ",
    )
    is_active = models.BooleanField(default=True, verbose_name="Діюча")

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class CommercialOrganization(models.Model):
    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="commercial_profile",
        verbose_name="Організація",
    )
    tax_type = models.ForeignKey(
        TaxType,
        on_delete=models.PROTECT,
        verbose_name="Форма оподаткування",
    )
    ipn = models.CharField(max_length=20, verbose_name="ІПН")
    legal_address = models.TextField(verbose_name="Юридична адреса")

    class Meta:
        verbose_name = "Commercial organization profile"
        verbose_name_plural = "Commercial organization profiles"

    def __str__(self):
        return f"{self.organization} — commercial"

    def clean(self):
        super().clean()
        if self.organization_id and self.organization.type != Organization.Type.COMMERCIAL:
            raise ValidationError({
                "organization": "Commercial profile can be attached only to organization with type 'commercial'."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class MilitaryOrganization(models.Model):
    class MilitaryType(models.TextChoices):
        ZSU = "zsu", "ЗСУ"
        NGU = "ngu", "НГУ"
        DPSU = "dpsu", "ДПСУ"
        DSNS = "dsns", "ДСНС"
        MVS = "mvs", "МВС"
        SBU = "sbu", "СБУ"

    class MilitaryBranch(models.TextChoices):
        SV = "sv", "СВ"
        PS = "ps", "ПС"
        VMS = "vms", "ВМС"
        DSHV = "dshv", "ДШВ"
        SBS = "sbs", "СБС"
        SP = "sp", "СП"
        SL = "sl", "СЛ"
        GUR = "gur", "ГУР"
        SSO = "sso", "ССО"
        TRO = "tro", "ТРО"
        KMS = "kms", "КМС"

    class MilitaryCorps(models.TextChoices):
        AZOV_1_NGU = "1_nsu_azov", "1-й корпус НГУ «Азов»"
        KHARTIIA_2_NGU = "2_nsu_khartiia", "2-й корпус НГУ «Хартія»"
        ARMY_3 = "3_ak", "3-й армійський корпус"
        DSHV_7 = "7_dshv", "7-й корпус ДШВ"
        DSHV_8 = "8_dshv", "8-й корпус ДШВ"
        AK_9 = "9_ak", "9-й армійський корпус"
        AK_10 = "10_ak", "10-й армійський корпус"
        AK_11 = "11_ak", "11-й армійський корпус"
        AK_12 = "12_ak", "12-й армійський корпус"
        AK_14 = "14_ak", "14-й армійський корпус"
        AK_15 = "15_ak", "15-й армійський корпус"
        AK_16 = "16_ak", "16-й армійський корпус"
        AK_17 = "17_ak", "17-й армійський корпус"
        AK_18 = "18_ak", "18-й армійський корпус"
        AK_19 = "19_ak", "19-й армійський корпус"
        AK_20 = "20_ak", "20-й армійський корпус"
        AK_21 = "21_ak", "21-й армійський корпус"
        MARINES_30 = "30_marine_corps", "30-й корпус морської піхоти"

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="military_profile",
        verbose_name="Організація",
    )
    a_code = models.CharField(
        max_length=5,
        blank=True,
        verbose_name="A-код",
        help_text="Або одна літера і 4 цифри, або 4 цифри",
    )
    military_type = models.CharField(
        max_length=20,
        choices=MilitaryType.choices,
        verbose_name="Тип військової організації",
    )
    military_branch = models.CharField(
        max_length=20,
        choices=MilitaryBranch.choices,
        blank=True,
        verbose_name="Рід / вид військ",
    )
    military_corps = models.CharField(
        max_length=32,
        choices=MilitaryCorps.choices,
        blank=True,
        verbose_name="Корпус",
    )

    class Meta:
        verbose_name = "Military organization profile"
        verbose_name_plural = "Military organization profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["a_code"],
                condition=~models.Q(a_code=""),
                name="uq_military_organization_a_code",
            ),
        ]

    def __str__(self):
        return f"{self.organization} — military"

    def clean(self):
        super().clean()
        if self.organization_id and self.organization.type != Organization.Type.MILITARY:
            raise ValidationError({
                "organization": "Military profile can be attached only to organization with type 'military'."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class CharityOrganization(models.Model):
    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="charity_profile",
        verbose_name="Організація",
    )
    legal_address = models.TextField(verbose_name="Юридична адреса")

    class Meta:
        verbose_name = "Charity organization profile"
        verbose_name_plural = "Charity organization profiles"

    def __str__(self):
        return f"{self.organization} — charity"

    def clean(self):
        super().clean()
        if self.organization_id and self.organization.type != Organization.Type.CHARITY:
            raise ValidationError({
                "organization": "Charity profile can be attached only to organization with type 'charity'."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
        
class Person(models.Model):
    class CommunicationType(models.TextChoices):
        VOICE = "voice", "Voice"
        WHATSAPP = "whatsapp", "WhatsApp"
        SIGNAL = "signal", "Signal"
        TELEGRAM = "telegram", "Telegram"
        VIBER = "viber", "Viber"
        OTHER = "other", "Other"

    last_name = models.CharField(max_length=255, verbose_name="Прізвище")
    first_name = models.CharField(max_length=255, verbose_name="Ім'я")
    middle_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="По батькові",
    )

    birth_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="День народження",
    )
    birth_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Місяць народження",
    )
    birth_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Рік народження",
    )

    phone_1_type = models.CharField(
        max_length=20,
        choices=CommunicationType.choices,
        blank=True,
        verbose_name="Тип комунікації 1",
    )
    phone_1 = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Телефон 1",
    )
    phone_2_type = models.CharField(
        max_length=20,
        choices=CommunicationType.choices,
        blank=True,
        verbose_name="Тип комунікації 2",
    )
    phone_2 = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Телефон 2",
    )

    comment = models.TextField(blank=True, verbose_name="Коментар")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        ordering = ["last_name", "first_name", "middle_name", "id"]

    def __str__(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(part for part in parts if part)


class OrganizationPosition(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Назва посади",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class OrganizationPersonAssignment(models.Model):
    person = models.ForeignKey(
        "organizations.Person",
        on_delete=models.PROTECT,
        related_name="organization_assignments",
        verbose_name="Людина",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="person_assignments",
        verbose_name="Організація",
    )
    position = models.ForeignKey(
        "organizations.OrganizationPosition",
        on_delete=models.PROTECT,
        related_name="person_assignments",
        verbose_name="Посада",
    )
    is_current = models.BooleanField(default=True, verbose_name="Поточне призначення")

    class Meta:
        ordering = ["organization__name", "position__name", "person__last_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["person"],
                condition=models.Q(is_current=True),
                name="uq_person_single_current_assignment",
            ),
            models.UniqueConstraint(
                fields=["organization", "position"],
                condition=models.Q(is_current=True),
                name="uq_organization_position_single_current_person",
            ),
        ]

    def __str__(self):
        status = "current" if self.is_current else "inactive"
        return f"{self.person} — {self.organization} — {self.position} ({status})"