from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (AdminUserUpdateView, CustomTokenObtainPairView,
                    MeView, RegisterView, UserListView)

urlpatterns = [
    path('register/',         RegisterView.as_view(),              name='register'),
    path('login/',            CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/',    TokenRefreshView.as_view(),          name='token_refresh'),
    path('me/',               MeView.as_view(),                    name='me'),
    path('users/',            UserListView.as_view(),              name='user_list'),
    path('users/<int:pk>/',   AdminUserUpdateView.as_view(),       name='user_update'),
]
