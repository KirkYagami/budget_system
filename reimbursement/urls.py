from django.urls import path
from .views import (
    CancelClaimView, ClaimApprovalLogView, ClaimAttachmentView,
    ExpenseClaimDetailView, ExpenseClaimListCreateView,
    FinanceApprovalView, ManagerApprovalView,
    PolicyRuleDetailView, PolicyRuleListCreateView,
    ProcessReimbursementView, ReimbursementDashboardView,
    ReimbursementListView, SubmitClaimView,
)

urlpatterns = [
    # Claims CRUD
    path('',           ExpenseClaimListCreateView.as_view(), name='claim-list'),
    path('<int:pk>/',  ExpenseClaimDetailView.as_view(),     name='claim-detail'),

    # Workflow actions
    path('<int:pk>/submit/',            SubmitClaimView.as_view(),         name='claim-submit'),
    path('<int:pk>/manager-action/',    ManagerApprovalView.as_view(),     name='claim-manager'),
    path('<int:pk>/finance-action/',    FinanceApprovalView.as_view(),     name='claim-finance'),
    path('<int:pk>/process-payment/',   ProcessReimbursementView.as_view(),name='claim-pay'),
    path('<int:pk>/cancel/',            CancelClaimView.as_view(),         name='claim-cancel'),

    # Attachments & audit
    path('<int:pk>/attachments/',       ClaimAttachmentView.as_view(),     name='claim-attachments'),
    path('<int:pk>/audit-log/',         ClaimApprovalLogView.as_view(),    name='claim-audit'),

    # Policy rules
    path('policies/',          PolicyRuleListCreateView.as_view(), name='policy-list'),
    path('policies/<int:pk>/', PolicyRuleDetailView.as_view(),     name='policy-detail'),

    # Finance views
    path('reimbursements/',    ReimbursementListView.as_view(),    name='reimbursement-list'),
    path('dashboard/',         ReimbursementDashboardView.as_view(), name='reimbursement-dashboard'),
]
