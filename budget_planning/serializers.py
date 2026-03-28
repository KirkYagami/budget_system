from rest_framework import serializers
from .models import Budget, BudgetCategory, BudgetCycle, BudgetLineItem, BudgetRevision


class BudgetCycleSerializer(serializers.ModelSerializer):
    created_by_name = serializers.StringRelatedField(source='created_by', read_only=True)

    class Meta:
        model  = BudgetCycle
        fields = ['id', 'name', 'cycle_type', 'start_date', 'end_date',
                  'status', 'description', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class BudgetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = BudgetCategory
        fields = ['id', 'name', 'code', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class BudgetLineItemSerializer(serializers.ModelSerializer):
    category_name     = serializers.StringRelatedField(source='category', read_only=True)
    available_amount  = serializers.SerializerMethodField()

    class Meta:
        model  = BudgetLineItem
        fields = ['id', 'budget', 'category', 'category_name',
                  'planned_amount', 'actual_amount', 'available_amount', 'description', 'created_at']
        read_only_fields = ['id', 'actual_amount', 'created_at']

    def get_available_amount(self, obj):
        return obj.planned_amount - obj.actual_amount


class BudgetRevisionSerializer(serializers.ModelSerializer):
    revised_by_name = serializers.StringRelatedField(source='revised_by', read_only=True)

    class Meta:
        model  = BudgetRevision
        fields = ['id', 'old_amount', 'new_amount', 'reason', 'revised_by_name', 'created_at']
        read_only_fields = ['id', 'revised_by_name', 'created_at']


class BudgetSerializer(serializers.ModelSerializer):
    owner_name       = serializers.StringRelatedField(source='owner', read_only=True)
    cycle_name       = serializers.StringRelatedField(source='cycle', read_only=True)
    available_amount = serializers.ReadOnlyField()
    utilization_pct  = serializers.ReadOnlyField()
    line_items       = BudgetLineItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Budget
        fields = [
            'id', 'cycle', 'cycle_name', 'level', 'name', 'department',
            'project_code', 'owner', 'owner_name', 'planned_amount',
            'actual_amount', 'reserved_amount', 'available_amount',
            'utilization_pct', 'status', 'notes', 'parent',
            'line_items', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'actual_amount', 'reserved_amount',
                            'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class BudgetSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    available_amount = serializers.ReadOnlyField()
    utilization_pct  = serializers.ReadOnlyField()
    cycle_name       = serializers.StringRelatedField(source='cycle', read_only=True)
    owner_name       = serializers.StringRelatedField(source='owner', read_only=True)

    class Meta:
        model  = Budget
        fields = ['id', 'name', 'level', 'department', 'project_code',
                  'cycle_name', 'owner_name', 'planned_amount', 'actual_amount',
                  'available_amount', 'utilization_pct', 'status']


class BudgetStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Budget.Status.choices)
    notes  = serializers.CharField(required=False, allow_blank=True)


class BudgetReviseAmountSerializer(serializers.Serializer):
    new_amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    reason     = serializers.CharField(min_length=10)
