from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Enterprise Budget Management API",
        default_version='v1',
        description=(
            "## Enterprise Budget Management System\n\n"
            "### Modules\n"
            "- ✅ **Auth** — JWT login, registration, roles\n"
            "- ✅ **Budget Planning** — cycles, categories, multi-level budgets\n"
            "- ✅ **Expense Reimbursement** — claims, approvals, policy engine, payments\n"
            "- 🔜 Cost Control & Budget Validation\n"
            "- 🔜 Monitoring & Analytics\n\n"
            "### Authentication\n"
            "1. `POST /api/auth/register/` → create account\n"
            "2. `POST /api/auth/login/` → get Bearer token\n"
            "3. Click **Authorize** → enter `Bearer <token>`\n\n"
            "### Reimbursement Workflow\n"
            "```\n"
            "Create (draft) → Submit → Manager Action → Finance Action → Process Payment\n"
            "```"
        ),
        contact=openapi.Contact(email="admin@budgetsystem.com"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/',               include('accounts.urls')),
    path('api/budget-planning/',    include('budget_planning.urls')),
    path('api/reimbursement/',      include('reimbursement.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/',   schema_view.with_ui('redoc',   cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0),     name='schema-json'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
