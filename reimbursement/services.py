"""
Business logic layer — keeps views thin.
All workflow transitions live here.
"""
from django.utils import timezone
from .models import ApprovalLog, ExpenseClaim, PolicyRule, Reimbursement


def validate_policy(claim: ExpenseClaim) -> tuple[bool, str]:
    """
    Run all active policy rules against the claim.
    Returns (passed: bool, notes: str)
    """
    rules  = PolicyRule.objects.filter(is_active=True)
    issues = []

    for rule in rules:
        # Skip if rule is category-specific and doesn't match
        if rule.expense_category and rule.expense_category != claim.expense_category:
            continue

        if rule.rule_type == PolicyRule.RuleType.AMOUNT_LIMIT:
            if rule.threshold_amount and claim.amount > rule.threshold_amount:
                issues.append(
                    f"[{rule.name}] Amount {claim.amount} exceeds limit {rule.threshold_amount}."
                )

        elif rule.rule_type == PolicyRule.RuleType.REQUIRES_RECEIPT:
            if rule.threshold_amount and claim.amount > rule.threshold_amount:
                has_receipt = claim.attachments.filter(
                    file_type__in=['invoice', 'receipt']
                ).exists()
                if not has_receipt:
                    issues.append(
                        f"[{rule.name}] Receipt/invoice required for amounts over {rule.threshold_amount}."
                    )

        elif rule.rule_type == PolicyRule.RuleType.CATEGORY_LIMIT:
            if rule.threshold_amount and claim.amount > rule.threshold_amount:
                issues.append(
                    f"[{rule.name}] {claim.get_expense_category_display()} "
                    f"expense exceeds category limit of {rule.threshold_amount}."
                )

    passed = len(issues) == 0
    notes  = " | ".join(issues) if issues else "All policy checks passed."
    return passed, notes


def submit_claim(claim: ExpenseClaim, user) -> ExpenseClaim:
    """Employee submits a draft claim for review."""
    if claim.status != ExpenseClaim.Status.DRAFT:
        raise ValueError("Only draft claims can be submitted.")

    passed, notes = validate_policy(claim)
    claim.policy_validated = passed
    claim.policy_notes     = notes
    claim.status           = ExpenseClaim.Status.SUBMITTED
    claim.submitted_at     = timezone.now()
    claim.save()

    action = (ApprovalLog.Action.POLICY_VALIDATED if passed
              else ApprovalLog.Action.POLICY_FAILED)
    ApprovalLog.objects.create(claim=claim, action=ApprovalLog.Action.SUBMITTED,
                                acted_by=user, notes="Claim submitted for approval.")
    ApprovalLog.objects.create(claim=claim, action=action,
                                acted_by=user, notes=notes)
    return claim


def manager_action(claim: ExpenseClaim, user, action: str, notes: str = '',
                   rejection_reason: str = '') -> ExpenseClaim:
    """Manager approves or rejects a submitted claim."""
    allowed_statuses = [ExpenseClaim.Status.SUBMITTED, ExpenseClaim.Status.UNDER_REVIEW]
    if claim.status not in allowed_statuses:
        raise ValueError(f"Claim is not in a reviewable state (current: {claim.status}).")

    if action == 'approve':
        claim.status = ExpenseClaim.Status.MANAGER_APPROVED
        log_action   = ApprovalLog.Action.MANAGER_APPROVED
    else:
        claim.status           = ExpenseClaim.Status.MANAGER_REJECTED
        claim.rejection_reason = rejection_reason
        log_action             = ApprovalLog.Action.MANAGER_REJECTED

    claim.save()
    ApprovalLog.objects.create(claim=claim, action=log_action,
                                acted_by=user, notes=notes or rejection_reason)
    return claim


def finance_action(claim: ExpenseClaim, user, action: str, notes: str = '',
                   rejection_reason: str = '') -> ExpenseClaim:
    """Finance approves or rejects a manager-approved claim."""
    if claim.status != ExpenseClaim.Status.MANAGER_APPROVED:
        raise ValueError("Claim must be manager-approved before finance review.")

    if action == 'approve':
        claim.status = ExpenseClaim.Status.FINANCE_APPROVED
        log_action   = ApprovalLog.Action.FINANCE_APPROVED
    else:
        claim.status           = ExpenseClaim.Status.FINANCE_REJECTED
        claim.rejection_reason = rejection_reason
        log_action             = ApprovalLog.Action.FINANCE_REJECTED

    claim.save()
    ApprovalLog.objects.create(claim=claim, action=log_action,
                                acted_by=user, notes=notes or rejection_reason)
    return claim


def process_reimbursement(claim: ExpenseClaim, user,
                           payment_method: str, payment_ref: str = '',
                           notes: str = '') -> Reimbursement:
    """Finance marks a claim as paid and creates the Reimbursement record."""
    if claim.status != ExpenseClaim.Status.FINANCE_APPROVED:
        raise ValueError("Only finance-approved claims can be reimbursed.")

    reimbursement = Reimbursement.objects.create(
        claim          = claim,
        amount_paid    = claim.amount,
        payment_method = payment_method,
        payment_ref    = payment_ref,
        paid_by        = user,
        notes          = notes,
    )

    claim.status = ExpenseClaim.Status.PAID
    claim.save()

    ApprovalLog.objects.create(claim=claim, action=ApprovalLog.Action.PAID,
                                acted_by=user,
                                notes=f"Paid via {payment_method}. Ref: {payment_ref or 'N/A'}")

    # Update budget actual amount if claim is linked to a budget
    if claim.budget:
        budget = claim.budget
        budget.actual_amount += claim.amount
        budget.save()

    return reimbursement
