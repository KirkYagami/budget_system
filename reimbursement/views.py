from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ApprovalLog, ExpenseClaim, PolicyRule, Reimbursement
from .serializers import (
    ApprovalActionSerializer, ApprovalLogSerializer,
    ClaimAttachmentSerializer, ExpenseClaimListSerializer,
    ExpenseClaimSerializer, PolicyRuleSerializer,
    ProcessReimbursementSerializer, ReimbursementSerializer,
)
from .services import (
    finance_action, manager_action,
    process_reimbursement, submit_claim,
)


# ─── EXPENSE CLAIMS ───────────────────────────────────────────────────────────

class ExpenseClaimListCreateView(generics.ListCreateAPIView):
    """
    GET  — list claims (filtered by role automatically)
    POST — create a new draft claim
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return ExpenseClaimSerializer if self.request.method == 'POST' else ExpenseClaimListSerializer

    def get_queryset(self):
        user = self.request.user
        qs   = ExpenseClaim.objects.select_related('submitted_by', 'manager', 'budget')

        # Role-based filtering
        if user.role == 'employee':
            qs = qs.filter(submitted_by=user)
        elif user.role == 'manager':
            qs = qs.filter(manager=user)
        elif user.role in ('finance', 'admin'):
            pass  # see all

        # Query param filters
        p = self.request.query_params
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('claim_type'):
            qs = qs.filter(claim_type=p['claim_type'])
        if p.get('expense_category'):
            qs = qs.filter(expense_category=p['expense_category'])
        if p.get('submitted_by'):
            qs = qs.filter(submitted_by_id=p['submitted_by'])
        return qs.order_by('-created_at')

    @swagger_auto_schema(
        operation_summary="List Expense Claims",
        operation_description=(
            "**Role-based access:**\n"
            "- `employee` → sees only their own claims\n"
            "- `manager` → sees claims assigned to them for review\n"
            "- `finance` / `admin` → sees all claims\n"
        ),
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=[s[0] for s in ExpenseClaim.Status.choices]),
            openapi.Parameter('claim_type', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=[c[0] for c in ExpenseClaim.ClaimType.choices]),
            openapi.Parameter('expense_category', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=[c[0] for c in ExpenseClaim.ExpenseCategory.choices]),
            openapi.Parameter('submitted_by', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        tags=['Expense Claims'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Expense Claim (Draft)",
        operation_description=(
            "Creates a claim in **draft** status.\n\n"
            "After creation, upload attachments then call `/submit/` to start the workflow.\n\n"
            "**claim_type options:** `expense` | `purchase`\n\n"
            "**expense_category options:** `project` | `equipment` | `vendor` | "
            "`marketing` | `travel` | `training` | `misc`"
        ),
        tags=['Expense Claims'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ExpenseClaimDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Full claim detail with attachments and approval log."""
    queryset = ExpenseClaim.objects.prefetch_related(
        'attachments', 'approval_logs__acted_by'
    ).select_related('submitted_by', 'manager', 'budget')
    serializer_class   = ExpenseClaimSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(operation_summary="Get Claim Detail", tags=['Expense Claims'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Claim (Draft only)",
        operation_description="Only allowed while claim is in `draft` status.",
        tags=['Expense Claims'],
    )
    def patch(self, request, *args, **kwargs):
        claim = self.get_object()
        if claim.status != ExpenseClaim.Status.DRAFT:
            return Response(
                {"detail": "Only draft claims can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Delete Claim (Draft only)", tags=['Expense Claims'])
    def delete(self, request, *args, **kwargs):
        claim = self.get_object()
        if claim.status != ExpenseClaim.Status.DRAFT:
            return Response(
                {"detail": "Only draft claims can be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().delete(request, *args, **kwargs)


# ─── WORKFLOW ACTIONS ─────────────────────────────────────────────────────────

class SubmitClaimView(APIView):
    """Employee submits a draft claim — triggers policy validation."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Submit Claim for Approval",
        operation_description=(
            "Transitions claim from `draft` → `submitted`.\n\n"
            "**Automatically runs policy validation engine:**\n"
            "- Amount limit checks\n"
            "- Receipt requirement checks\n"
            "- Category limit checks\n\n"
            "Policy result is stored in `policy_validated` and `policy_notes`."
        ),
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}),
        responses={200: ExpenseClaimSerializer, 400: "Invalid state"},
        tags=['Expense Claim Workflow'],
    )
    def post(self, request, pk):
        claim = generics.get_object_or_404(ExpenseClaim, pk=pk)
        if claim.submitted_by != request.user and request.user.role not in ('admin',):
            return Response({"detail": "You can only submit your own claims."},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            claim = submit_claim(claim, request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpenseClaimSerializer(claim, context={'request': request}).data)


class ManagerApprovalView(APIView):
    """Manager approves or rejects a submitted claim."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Manager Approve / Reject",
        operation_description=(
            "**Allowed roles:** `manager`, `admin`\n\n"
            "- `approve` → transitions to `manager_approved`\n"
            "- `reject`  → transitions to `manager_rejected` (rejection_reason required)"
        ),
        request_body=ApprovalActionSerializer,
        responses={200: ExpenseClaimSerializer, 400: "Validation error", 403: "Forbidden"},
        tags=['Expense Claim Workflow'],
    )
    def post(self, request, pk):
        if request.user.role not in ('manager', 'admin'):
            return Response({"detail": "Only managers can perform this action."},
                            status=status.HTTP_403_FORBIDDEN)
        claim      = generics.get_object_or_404(ExpenseClaim, pk=pk)
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            claim = manager_action(
                claim, request.user, d['action'],
                notes=d.get('notes', ''),
                rejection_reason=d.get('rejection_reason', ''),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpenseClaimSerializer(claim, context={'request': request}).data)


class FinanceApprovalView(APIView):
    """Finance approves or rejects a manager-approved claim."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Finance Approve / Reject",
        operation_description=(
            "**Allowed roles:** `finance`, `admin`\n\n"
            "- `approve` → transitions to `finance_approved`\n"
            "- `reject`  → transitions to `finance_rejected` (rejection_reason required)"
        ),
        request_body=ApprovalActionSerializer,
        responses={200: ExpenseClaimSerializer, 400: "Validation error", 403: "Forbidden"},
        tags=['Expense Claim Workflow'],
    )
    def post(self, request, pk):
        if request.user.role not in ('finance', 'admin'):
            return Response({"detail": "Only finance team can perform this action."},
                            status=status.HTTP_403_FORBIDDEN)
        claim      = generics.get_object_or_404(ExpenseClaim, pk=pk)
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            claim = finance_action(
                claim, request.user, d['action'],
                notes=d.get('notes', ''),
                rejection_reason=d.get('rejection_reason', ''),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpenseClaimSerializer(claim, context={'request': request}).data)


class ProcessReimbursementView(APIView):
    """Finance marks a finance-approved claim as paid."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Process Reimbursement (Mark as Paid)",
        operation_description=(
            "**Allowed roles:** `finance`, `admin`\n\n"
            "Creates a `Reimbursement` record and transitions claim to `paid`.\n"
            "Also updates the linked budget's `actual_amount` automatically."
        ),
        request_body=ProcessReimbursementSerializer,
        responses={200: ExpenseClaimSerializer, 400: "Error", 403: "Forbidden"},
        tags=['Expense Claim Workflow'],
    )
    def post(self, request, pk):
        if request.user.role not in ('finance', 'admin'):
            return Response({"detail": "Only finance team can process reimbursements."},
                            status=status.HTTP_403_FORBIDDEN)
        claim      = generics.get_object_or_404(ExpenseClaim, pk=pk)
        serializer = ProcessReimbursementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            process_reimbursement(
                claim, request.user,
                payment_method=d['payment_method'],
                payment_ref=d.get('payment_ref', ''),
                notes=d.get('notes', ''),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpenseClaimSerializer(
            ExpenseClaim.objects.get(pk=pk), context={'request': request}
        ).data)


class CancelClaimView(APIView):
    """Employee cancels their own claim (only if not yet finance-approved)."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Cancel Claim",
        operation_description="Employee can cancel a claim that has not yet been finance-approved.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'reason': openapi.Schema(type=openapi.TYPE_STRING)}
        ),
        responses={200: ExpenseClaimSerializer},
        tags=['Expense Claim Workflow'],
    )
    def post(self, request, pk):
        claim = generics.get_object_or_404(ExpenseClaim, pk=pk)
        if claim.submitted_by != request.user and request.user.role != 'admin':
            return Response({"detail": "You can only cancel your own claims."},
                            status=status.HTTP_403_FORBIDDEN)
        non_cancellable = [ExpenseClaim.Status.FINANCE_APPROVED,
                           ExpenseClaim.Status.PAID, ExpenseClaim.Status.CANCELLED]
        if claim.status in non_cancellable:
            return Response({"detail": f"Cannot cancel a claim with status: {claim.status}"},
                            status=status.HTTP_400_BAD_REQUEST)
        claim.status = ExpenseClaim.Status.CANCELLED
        claim.save()
        ApprovalLog.objects.create(
            claim=claim, action=ApprovalLog.Action.CANCELLED,
            acted_by=request.user,
            notes=request.data.get('reason', 'Cancelled by submitter.'),
        )
        return Response(ExpenseClaimSerializer(claim, context={'request': request}).data)


# ─── ATTACHMENTS ─────────────────────────────────────────────────────────────

class ClaimAttachmentView(generics.ListCreateAPIView):
    """Upload bills/receipts to a claim."""
    serializer_class   = ClaimAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExpenseClaim.objects.get(pk=self.kwargs['pk']).attachments.all()

    @swagger_auto_schema(
        operation_summary="List Attachments",
        tags=['Claim Attachments'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Upload Attachment (Bill/Invoice/Receipt)",
        operation_description=(
            "Upload a file attachment to a claim.\n\n"
            "Use `multipart/form-data`. Fields: `file`, `file_type`, `claim`.\n\n"
            "**file_type:** `invoice` | `receipt` | `quote` | `contract` | `other`"
        ),
        tags=['Claim Attachments'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# ─── APPROVAL LOG ─────────────────────────────────────────────────────────────

class ClaimApprovalLogView(generics.ListAPIView):
    """Full audit trail for a specific claim."""
    serializer_class   = ApprovalLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Claim Approval Audit Trail",
        tags=['Expense Claims'],
    )
    def get(self, request, pk, *args, **kwargs):
        claim = generics.get_object_or_404(ExpenseClaim, pk=pk)
        return Response(ApprovalLogSerializer(claim.approval_logs.all(), many=True).data)


# ─── POLICY RULES ─────────────────────────────────────────────────────────────

class PolicyRuleListCreateView(generics.ListCreateAPIView):
    """Manage policy rules used by the validation engine."""
    queryset           = PolicyRule.objects.all()
    serializer_class   = PolicyRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Policy Rules",
        tags=['Policy Rules'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Policy Rule",
        operation_description=(
            "Define a policy rule for the validation engine.\n\n"
            "**rule_type options:**\n"
            "- `amount_limit` — rejects if claim amount exceeds threshold\n"
            "- `category_limit` — per-category spending cap\n"
            "- `requires_receipt` — receipt mandatory above threshold\n"
            "- `approval_tier` — adds an extra approval step\n\n"
            "Leave `expense_category` blank to apply rule to ALL categories."
        ),
        tags=['Policy Rules'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PolicyRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = PolicyRule.objects.all()
    serializer_class   = PolicyRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(operation_summary="Get Policy Rule", tags=['Policy Rules'])
    def get(self, request, *args, **kwargs): return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Update Policy Rule", tags=['Policy Rules'])
    def patch(self, request, *args, **kwargs): return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Delete Policy Rule", tags=['Policy Rules'])
    def delete(self, request, *args, **kwargs): return super().delete(request, *args, **kwargs)


# ─── REIMBURSEMENT RECORDS ────────────────────────────────────────────────────

class ReimbursementListView(generics.ListAPIView):
    """Finance view — all processed reimbursements."""
    serializer_class   = ReimbursementSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List All Reimbursements",
        tags=['Reimbursements'],
    )
    def get(self, request, *args, **kwargs):
        qs = Reimbursement.objects.select_related('claim', 'paid_by').order_by('-paid_at')
        if request.user.role == 'employee':
            qs = qs.filter(claim__submitted_by=request.user)
        return Response(ReimbursementSerializer(qs, many=True).data)


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

class ReimbursementDashboardView(APIView):
    """Summary stats for the reimbursement module."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Reimbursement Dashboard",
        operation_description="Aggregated claim stats by status, category, and pending queues.",
        tags=['Expense Claims'],
    )
    def get(self, request):
        from django.db.models import Count, Sum

        all_claims = ExpenseClaim.objects.all()
        if request.user.role == 'employee':
            all_claims = all_claims.filter(submitted_by=request.user)
        elif request.user.role == 'manager':
            all_claims = all_claims.filter(manager=request.user)

        by_status = all_claims.values('status').annotate(
            count=Count('id'), total_amount=Sum('amount')
        )

        by_category = all_claims.values('expense_category').annotate(
            count=Count('id'), total_amount=Sum('amount')
        )

        pending_manager  = all_claims.filter(status='submitted').count()
        pending_finance  = all_claims.filter(status='manager_approved').count()
        total_paid       = Reimbursement.objects.filter(
            claim__in=all_claims
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        return Response({
            'total_claims':      all_claims.count(),
            'total_paid':        total_paid,
            'pending_manager_review': pending_manager,
            'pending_finance_review': pending_finance,
            'by_status':         list(by_status),
            'by_category':       list(by_category),
        })
