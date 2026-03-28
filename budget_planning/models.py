from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import User


class BudgetCycle(models.Model):
    """Management defines budget cycles (e.g. FY-2025, Q1-2025)."""

    class CycleType(models.TextChoices):
        ANNUAL    = 'annual',    'Annual'
        QUARTERLY = 'quarterly', 'Quarterly'
        MONTHLY   = 'monthly',   'Monthly'
        CUSTOM    = 'custom',    'Custom'

    class Status(models.TextChoices):
        DRAFT   = 'draft',   'Draft'
        ACTIVE  = 'active',  'Active'
        CLOSED  = 'closed',  'Closed'
        FROZEN  = 'frozen',  'Frozen'

    name        = models.CharField(max_length=100, unique=True)
    cycle_type  = models.CharField(max_length=15, choices=CycleType.choices)
    start_date  = models.DateField()
    end_date    = models.DateField()
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    description = models.TextField(blank=True)
    created_by  = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cycles_created')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class BudgetCategory(models.Model):
    """Predefined categories like Travel, Marketing, Equipment etc."""

    name        = models.CharField(max_length=100, unique=True)
    code        = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Budget Categories'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} – {self.name}"


class Budget(models.Model):
    """Multi-level budget: Organization / Department / Project."""

    class BudgetLevel(models.TextChoices):
        ORGANIZATION = 'organization', 'Organization'
        DEPARTMENT   = 'department',   'Department'
        PROJECT      = 'project',      'Project / Activity'

    class Status(models.TextChoices):
        DRAFT    = 'draft',    'Draft'
        PENDING  = 'pending',  'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        ACTIVE   = 'active',   'Active'
        CLOSED   = 'closed',   'Closed'

    cycle           = models.ForeignKey(BudgetCycle, on_delete=models.PROTECT, related_name='budgets')
    level           = models.CharField(max_length=15, choices=BudgetLevel.choices)
    name            = models.CharField(max_length=150)
    department      = models.CharField(max_length=100, blank=True)
    project_code    = models.CharField(max_length=50, blank=True)
    owner           = models.ForeignKey(User, on_delete=models.PROTECT, related_name='owned_budgets')
    planned_amount  = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    actual_amount   = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                          validators=[MinValueValidator(0)])
    reserved_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                          validators=[MinValueValidator(0)])
    status          = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    notes           = models.TextField(blank=True)
    parent          = models.ForeignKey('self', null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='children')
    created_by      = models.ForeignKey(User, on_delete=models.PROTECT, related_name='budgets_created')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['cycle', 'level', 'department', 'project_code']]

    def __str__(self):
        return f"{self.name} | {self.get_level_display()} | {self.cycle}"

    @property
    def available_amount(self):
        return self.planned_amount - self.actual_amount - self.reserved_amount

    @property
    def utilization_pct(self):
        if self.planned_amount == 0:
            return 0
        return round((self.actual_amount / self.planned_amount) * 100, 2)


class BudgetLineItem(models.Model):
    """Breakdown of a budget by category."""

    budget          = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='line_items')
    category        = models.ForeignKey(BudgetCategory, on_delete=models.PROTECT)
    planned_amount  = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    actual_amount   = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description     = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['budget', 'category']]

    def __str__(self):
        return f"{self.budget.name} / {self.category.name}"


class BudgetRevision(models.Model):
    """Audit log of every budget change."""

    budget      = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='revisions')
    revised_by  = models.ForeignKey(User, on_delete=models.PROTECT)
    old_amount  = models.DecimalField(max_digits=15, decimal_places=2)
    new_amount  = models.DecimalField(max_digits=15, decimal_places=2)
    reason      = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
