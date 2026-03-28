import os
from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import User
from budget_planning.models import Budget, BudgetCategory


def claim_attachment_path(instance, filename):
    return f"claims/{instance.claim.id}/{filename}"


class ExpenseClaim(models.Model):
    """
    Core model — an employee submits a reimbursement claim.
    Flows through: draft → submitted → under_review → approved / rejected → paid
    """

    class ClaimType(models.TextChoices):
        EXPENSE  = 'expense',  'Expense Claim'
        PURCHASE = 'purchase', 'Purchase Claim'

    class PaymentType(models.TextChoices):
        PREPAID  = 'prepaid',  'Prepaid (Employee paid first)'
        POSTPAID = 'postpaid', 'Postpaid (Company pays vendor)'

    class Status(models.TextChoices):
        DRAFT         = 'draft',         'Draft'
        SUBMITTED     = 'submitted',     'Submitted'
        UNDER_REVIEW  = 'under_review',  'Under Review'
        MANAGER_APPROVED  = 'manager_approved',  'Manager Approved'
        MANAGER_REJECTED  = 'manager_rejected',  'Manager Rejected'
        FINANCE_APPROVED  = 'finance_approved',  'Finance Approved'
        FINANCE_REJECTED  = 'finance_rejected',  'Finance Rejected'
        PAID          = 'paid',          'Paid / Reimbursed'
        CANCELLED     = 'cancelled',     'Cancelled'

    class ExpenseCategory(models.TextChoices):
        PROJECT   = 'project',   'Project Expense'
        EQUIPMENT = 'equipment', 'Equipment Purchase'
        VENDOR    = 'vendor',    'Vendor Expense'
        MARKETING = 'marketing', 'Marketing Expense'
        TRAVEL    = 'travel',    'Travel Expense'
        TRAINING  = 'training',  'Training & Development'
        MISC      = 'misc',      'Miscellaneous'

    # Core fields
    claim_number     = models.CharField(max_length=20, unique=True, editable=False)
    claim_type       = models.CharField(max_length=10, choices=ClaimType.choices)
    expense_category = models.CharField(max_length=15, choices=ExpenseCategory.choices)
    payment_type     = models.CharField(max_length=10, choices=PaymentType.choices,
                                        default=PaymentType.PREPAID)
    title            = models.CharField(max_length=200)
    description      = models.TextField()
    amount           = models.DecimalField(max_digits=12, decimal_places=2,
                                           validators=[MinValueValidator(0.01)])
    currency         = models.CharField(max_length=5, default='IDR')
    expense_date     = models.DateField()

    # Relations
    submitted_by  = models.ForeignKey(User, on_delete=models.PROTECT, related_name='claims_submitted')
    budget        = models.ForeignKey(Budget, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='claims')
    budget_category = models.ForeignKey(BudgetCategory, null=True, blank=True,
                                        on_delete=models.SET_NULL)

    # Workflow
    status           = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    manager          = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='claims_to_review')
    rejection_reason = models.TextField(blank=True)
    policy_validated = models.BooleanField(default=False)
    policy_notes     = models.TextField(blank=True)

    # Purchase-specific
    is_reusable      = models.BooleanField(default=False, help_text="For purchase claims — is item reusable/asset?")
    added_to_inventory = models.BooleanField(default=False)
    po_number        = models.CharField(max_length=50, blank=True)

    # Timestamps
    submitted_at  = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.claim_number:
            self.claim_number = self._generate_claim_number()
        super().save(*args, **kwargs)

    def _generate_claim_number(self):
        import datetime
        prefix = 'CLM'
        date   = datetime.date.today().strftime('%Y%m')
        last   = ExpenseClaim.objects.filter(
            claim_number__startswith=f'{prefix}{date}'
        ).count()
        return f"{prefix}{date}{str(last + 1).zfill(4)}"

    def __str__(self):
        return f"{self.claim_number} — {self.title} ({self.get_status_display()})"


class ClaimAttachment(models.Model):
    """Bill / invoice / receipt uploads for a claim."""

    class FileType(models.TextChoices):
        INVOICE  = 'invoice',  'Invoice'
        RECEIPT  = 'receipt',  'Receipt'
        QUOTE    = 'quote',    'Quotation'
        CONTRACT = 'contract', 'Contract'
        OTHER    = 'other',    'Other'

    claim     = models.ForeignKey(ExpenseClaim, on_delete=models.CASCADE, related_name='attachments')
    file      = models.FileField(upload_to=claim_attachment_path)
    file_type = models.CharField(max_length=10, choices=FileType.choices, default=FileType.RECEIPT)
    filename  = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.claim.claim_number} / {self.filename}"


class ApprovalLog(models.Model):
    """Immutable audit log of every approval action taken on a claim."""

    class Action(models.TextChoices):
        SUBMITTED         = 'submitted',         'Submitted'
        MANAGER_APPROVED  = 'manager_approved',  'Manager Approved'
        MANAGER_REJECTED  = 'manager_rejected',  'Manager Rejected'
        FINANCE_APPROVED  = 'finance_approved',  'Finance Approved'
        FINANCE_REJECTED  = 'finance_rejected',  'Finance Rejected'
        POLICY_VALIDATED  = 'policy_validated',  'Policy Validated'
        POLICY_FAILED     = 'policy_failed',     'Policy Check Failed'
        PAID              = 'paid',              'Payment Processed'
        CANCELLED         = 'cancelled',         'Cancelled'
        REVISED           = 'revised',           'Claim Revised'

    claim      = models.ForeignKey(ExpenseClaim, on_delete=models.CASCADE, related_name='approval_logs')
    action     = models.CharField(max_length=20, choices=Action.choices)
    acted_by   = models.ForeignKey(User, on_delete=models.PROTECT)
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.claim.claim_number} | {self.action} by {self.acted_by}"


class PolicyRule(models.Model):
    """
    Configurable policy rules the validation engine checks against.
    e.g. Travel claims > 5,000,000 IDR require Finance approval.
    """

    class RuleType(models.TextChoices):
        AMOUNT_LIMIT    = 'amount_limit',    'Amount Limit'
        CATEGORY_LIMIT  = 'category_limit',  'Category Limit'
        REQUIRES_RECEIPT = 'requires_receipt', 'Receipt Required Above Amount'
        APPROVAL_TIER   = 'approval_tier',   'Extra Approval Tier'

    name             = models.CharField(max_length=100)
    rule_type        = models.CharField(max_length=20, choices=RuleType.choices)
    expense_category = models.CharField(max_length=15,
                                        choices=ExpenseClaim.ExpenseCategory.choices,
                                        blank=True, help_text="Blank = applies to all categories")
    threshold_amount = models.DecimalField(max_digits=12, decimal_places=2,
                                           null=True, blank=True)
    description      = models.TextField(blank=True)
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class Reimbursement(models.Model):
    """Final payment record once Finance approves a claim."""

    class Method(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CASH          = 'cash',          'Cash'
        WALLET        = 'wallet',        'Digital Wallet'

    claim           = models.OneToOneField(ExpenseClaim, on_delete=models.PROTECT,
                                           related_name='reimbursement')
    amount_paid     = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method  = models.CharField(max_length=15, choices=Method.choices)
    payment_ref     = models.CharField(max_length=100, blank=True, help_text="Bank ref / transaction ID")
    paid_by         = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reimbursements_processed')
    paid_at         = models.DateTimeField(auto_now_add=True)
    notes           = models.TextField(blank=True)

    def __str__(self):
        return f"Reimbursement for {self.claim.claim_number} — {self.amount_paid}"
