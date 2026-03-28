from decimal import Decimal
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Budget, BudgetCategory, BudgetCycle, BudgetLineItem, BudgetRevision
from .serializers import (
    BudgetCategorySerializer, BudgetCycleSerializer, BudgetLineItemSerializer,
    BudgetReviseAmountSerializer, BudgetRevisionSerializer,
    BudgetSerializer, BudgetStatusUpdateSerializer, BudgetSummarySerializer,
)


# ─── BUDGET CYCLE ─────────────────────────────────────────────────────────────

class BudgetCycleListCreateView(generics.ListCreateAPIView):
    """List all budget cycles or create a new one."""
    queryset           = BudgetCycle.objects.all()
    serializer_class   = BudgetCycleSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Budget Cycles",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=[c[0] for c in BudgetCycle.Status.choices]),
        ],
        tags=['Budget Cycles'],
    )
    def get(self, request, *args, **kwargs):
        qs = self.queryset
        s  = request.query_params.get('status')
        if s:
            qs = qs.filter(status=s)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create Budget Cycle",
        tags=['Budget Cycles'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BudgetCycleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific budget cycle."""
    queryset           = BudgetCycle.objects.all()
    serializer_class   = BudgetCycleSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(operation_summary="Get Budget Cycle", tags=['Budget Cycles'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Update Budget Cycle", tags=['Budget Cycles'])
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Delete Budget Cycle", tags=['Budget Cycles'])
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ─── BUDGET CATEGORY ──────────────────────────────────────────────────────────

class BudgetCategoryListCreateView(generics.ListCreateAPIView):
    """List or create budget categories."""
    queryset           = BudgetCategory.objects.filter(is_active=True)
    serializer_class   = BudgetCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(operation_summary="List Budget Categories", tags=['Budget Categories'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Create Budget Category", tags=['Budget Categories'])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BudgetCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = BudgetCategory.objects.all()
    serializer_class   = BudgetCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(operation_summary="Get Category", tags=['Budget Categories'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Update Category", tags=['Budget Categories'])
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Delete Category", tags=['Budget Categories'])
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ─── BUDGET ───────────────────────────────────────────────────────────────────

class BudgetListCreateView(generics.ListCreateAPIView):
    """List budgets with filters, or create a new budget."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return BudgetSummarySerializer
        return BudgetSerializer

    def get_queryset(self):
        qs = Budget.objects.select_related('cycle', 'owner', 'created_by').all()
        p  = self.request.query_params
        if p.get('cycle'):
            qs = qs.filter(cycle_id=p['cycle'])
        if p.get('level'):
            qs = qs.filter(level=p['level'])
        if p.get('department'):
            qs = qs.filter(department__icontains=p['department'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('owner'):
            qs = qs.filter(owner_id=p['owner'])
        return qs

    @swagger_auto_schema(
        operation_summary="List Budgets",
        manual_parameters=[
            openapi.Parameter('cycle',      openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('level',      openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=[l[0] for l in Budget.BudgetLevel.choices]),
            openapi.Parameter('department', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('status',     openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              enum=[s[0] for s in Budget.Status.choices]),
            openapi.Parameter('owner',      openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        tags=['Budgets'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Budget",
        operation_description=(
            "Create a new budget at org / department / project level.\n\n"
            "**Status flow:** draft → pending → approved → active → closed"
        ),
        tags=['Budgets'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BudgetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Full detail of a budget including line items."""
    queryset           = Budget.objects.prefetch_related('line_items__category', 'revisions').all()
    serializer_class   = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(operation_summary="Get Budget Detail", tags=['Budgets'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Update Budget", tags=['Budgets'])
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Delete Budget", tags=['Budgets'])
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class BudgetStatusUpdateView(APIView):
    """Change budget status with optional notes."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Update Budget Status",
        operation_description=(
            "Transition a budget through its lifecycle:\n"
            "- `draft` → `pending` (submit for approval)\n"
            "- `pending` → `approved` / `rejected` (manager/finance action)\n"
            "- `approved` → `active` (activate)\n"
            "- `active` → `closed`\n"
        ),
        request_body=BudgetStatusUpdateSerializer,
        responses={200: BudgetSerializer, 400: "Invalid status"},
        tags=['Budgets'],
    )
    def patch(self, request, pk):
        budget     = generics.get_object_or_404(Budget, pk=pk)
        serializer = BudgetStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        budget.status = serializer.validated_data['status']
        if serializer.validated_data.get('notes'):
            budget.notes = serializer.validated_data['notes']
        budget.save()

        return Response(BudgetSerializer(budget, context={'request': request}).data)


class BudgetReviseAmountView(APIView):
    """Revise a budget's planned amount (creates audit log)."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Revise Budget Amount",
        operation_description="Updates planned_amount and logs the change in BudgetRevision for audit.",
        request_body=BudgetReviseAmountSerializer,
        responses={200: BudgetSerializer, 400: "Validation error"},
        tags=['Budgets'],
    )
    def post(self, request, pk):
        budget     = generics.get_object_or_404(Budget, pk=pk)
        serializer = BudgetReviseAmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_amount = budget.planned_amount
        new_amount = serializer.validated_data['new_amount']

        BudgetRevision.objects.create(
            budget     = budget,
            revised_by = request.user,
            old_amount = old_amount,
            new_amount = new_amount,
            reason     = serializer.validated_data['reason'],
        )

        budget.planned_amount = new_amount
        budget.save()

        return Response(BudgetSerializer(budget, context={'request': request}).data)


class BudgetRevisionListView(generics.ListAPIView):
    """Audit trail – all revisions for a budget."""
    serializer_class   = BudgetRevisionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Budget Revisions (Audit Trail)",
        tags=['Budgets'],
    )
    def get(self, request, pk, *args, **kwargs):
        budget = generics.get_object_or_404(Budget, pk=pk)
        qs     = budget.revisions.all()
        return Response(BudgetRevisionSerializer(qs, many=True).data)


# ─── BUDGET LINE ITEMS ────────────────────────────────────────────────────────

class BudgetLineItemListCreateView(generics.ListCreateAPIView):
    """Line items for a specific budget."""
    serializer_class   = BudgetLineItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BudgetLineItem.objects.filter(budget_id=self.kwargs['pk'])

    @swagger_auto_schema(operation_summary="List Line Items", tags=['Budget Line Items'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Add Line Item",
        operation_description="Add a category-level breakdown to a budget.",
        tags=['Budget Line Items'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# ─── BUDGET OVERVIEW / DASHBOARD ─────────────────────────────────────────────

class BudgetOverviewView(APIView):
    """High-level budget health summary across all active budgets."""
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Budget Overview Dashboard",
        operation_description="Returns aggregated stats: total budgets, utilization, overrun count.",
        responses={200: openapi.Response(
            description="Overview stats",
            examples={"application/json": {
                "total_budgets": 12,
                "total_planned": "5000000.00",
                "total_actual": "2100000.00",
                "total_available": "2900000.00",
                "overall_utilization_pct": 42.0,
                "overrun_count": 1,
                "by_level": [],
            }}
        )},
        tags=['Budgets'],
    )
    def get(self, request):
        from django.db.models import Sum, Count, Q

        budgets = Budget.objects.filter(status__in=['active', 'approved'])
        agg     = budgets.aggregate(
            total_planned  = Sum('planned_amount'),
            total_actual   = Sum('actual_amount'),
            total_reserved = Sum('reserved_amount'),
        )

        total_planned  = agg['total_planned']  or Decimal('0')
        total_actual   = agg['total_actual']   or Decimal('0')
        total_reserved = agg['total_reserved'] or Decimal('0')
        total_available = total_planned - total_actual - total_reserved
        overrun_count  = budgets.filter(actual_amount__gt=models.F('planned_amount')).count()

        utilization = round(float(total_actual / total_planned) * 100, 2) if total_planned else 0

        # Per-level breakdown
        from .models import Budget as B
        by_level = []
        for level_code, label in B.BudgetLevel.choices:
            sub = budgets.filter(level=level_code).aggregate(
                planned=Sum('planned_amount'), actual=Sum('actual_amount'))
            by_level.append({
                'level':   label,
                'planned': sub['planned'] or 0,
                'actual':  sub['actual'] or 0,
            })

        return Response({
            'total_budgets':        budgets.count(),
            'total_planned':        total_planned,
            'total_actual':         total_actual,
            'total_available':      total_available,
            'overall_utilization_pct': utilization,
            'overrun_count':        overrun_count,
            'by_level':             by_level,
        })
