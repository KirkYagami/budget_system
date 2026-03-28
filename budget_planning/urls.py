from django.urls import path
from .views import (
    BudgetCategoryDetailView, BudgetCategoryListCreateView,
    BudgetCycleDetailView, BudgetCycleListCreateView,
    BudgetDetailView, BudgetLineItemListCreateView,
    BudgetListCreateView, BudgetOverviewView,
    BudgetReviseAmountView, BudgetRevisionListView,
    BudgetStatusUpdateView,
)

urlpatterns = [
    # Cycles
    path('cycles/',          BudgetCycleListCreateView.as_view(), name='cycle-list'),
    path('cycles/<int:pk>/', BudgetCycleDetailView.as_view(),     name='cycle-detail'),

    # Categories
    path('categories/',          BudgetCategoryListCreateView.as_view(), name='category-list'),
    path('categories/<int:pk>/', BudgetCategoryDetailView.as_view(),     name='category-detail'),

    # Budgets
    path('',             BudgetListCreateView.as_view(), name='budget-list'),
    path('<int:pk>/',    BudgetDetailView.as_view(),     name='budget-detail'),
    path('<int:pk>/status/',  BudgetStatusUpdateView.as_view(),   name='budget-status'),
    path('<int:pk>/revise/',  BudgetReviseAmountView.as_view(),   name='budget-revise'),
    path('<int:pk>/revisions/', BudgetRevisionListView.as_view(), name='budget-revisions'),
    path('<int:pk>/line-items/', BudgetLineItemListCreateView.as_view(), name='budget-lineitems'),

    # Dashboard
    path('overview/', BudgetOverviewView.as_view(), name='budget-overview'),
]
