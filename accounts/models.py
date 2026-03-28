from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended User with department, role, and manager linkage."""

    class Role(models.TextChoices):
        EMPLOYEE      = 'employee',      'Employee'
        MANAGER       = 'manager',       'Manager'
        FINANCE       = 'finance',       'Finance'
        BUDGET_OWNER  = 'budget_owner',  'Budget Owner'
        ADMIN         = 'admin',         'Admin'

    role       = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    department = models.CharField(max_length=100, blank=True)
    manager    = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='subordinates'
    )
    phone      = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"
