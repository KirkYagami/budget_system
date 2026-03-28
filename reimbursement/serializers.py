from rest_framework import serializers
from .models import ApprovalLog, ClaimAttachment, ExpenseClaim, PolicyRule, Reimbursement


class ClaimAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.StringRelatedField(source='uploaded_by', read_only=True)

    class Meta:
        model  = ClaimAttachment
        fields = ['id', 'claim', 'file', 'file_type', 'filename',
                  'file_size', 'uploaded_by_name', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_by_name', 'uploaded_at']

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        f = validated_data.get('file')
        if f:
            validated_data.setdefault('filename', f.name)
            validated_data.setdefault('file_size', f.size)
        return super().create(validated_data)


class ApprovalLogSerializer(serializers.ModelSerializer):
    acted_by_name = serializers.StringRelatedField(source='acted_by', read_only=True)

    class Meta:
        model  = ApprovalLog
        fields = ['id', 'action', 'acted_by_name', 'notes', 'created_at']
        read_only_fields = ['id', 'acted_by_name', 'created_at']


class ReimbursementSerializer(serializers.ModelSerializer):
    paid_by_name = serializers.StringRelatedField(source='paid_by', read_only=True)

    class Meta:
        model  = Reimbursement
        fields = ['id', 'claim', 'amount_paid', 'payment_method',
                  'payment_ref', 'paid_by_name', 'paid_at', 'notes']
        read_only_fields = ['id', 'paid_by_name', 'paid_at']


class ExpenseClaimSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.StringRelatedField(source='submitted_by', read_only=True)
    manager_name      = serializers.StringRelatedField(source='manager', read_only=True)
    budget_name       = serializers.StringRelatedField(source='budget', read_only=True)
    attachments       = ClaimAttachmentSerializer(many=True, read_only=True)
    approval_logs     = ApprovalLogSerializer(many=True, read_only=True)
    reimbursement_detail = ReimbursementSerializer(source='reimbursement', read_only=True)

    class Meta:
        model  = ExpenseClaim
        fields = [
            'id', 'claim_number', 'claim_type', 'expense_category', 'payment_type',
            'title', 'description', 'amount', 'currency', 'expense_date',
            'submitted_by', 'submitted_by_name', 'budget', 'budget_name',
            'budget_category', 'manager', 'manager_name',
            'status', 'rejection_reason', 'policy_validated', 'policy_notes',
            'is_reusable', 'added_to_inventory', 'po_number',
            'attachments', 'approval_logs', 'reimbursement_detail',
            'submitted_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'claim_number', 'submitted_by', 'status',
            'policy_validated', 'policy_notes', 'submitted_at',
            'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        validated_data['submitted_by'] = self.context['request'].user
        # Auto-assign manager from user profile if not specified
        if not validated_data.get('manager'):
            validated_data['manager'] = self.context['request'].user.manager
        return super().create(validated_data)


class ExpenseClaimListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    submitted_by_name = serializers.StringRelatedField(source='submitted_by', read_only=True)

    class Meta:
        model  = ExpenseClaim
        fields = ['id', 'claim_number', 'claim_type', 'expense_category',
                  'title', 'amount', 'currency', 'status',
                  'submitted_by_name', 'expense_date', 'created_at']


# ─── Action Serializers ───────────────────────────────────────────────────────

class SubmitClaimSerializer(serializers.Serializer):
    """No extra fields needed — just triggers submit action."""
    pass


class ApprovalActionSerializer(serializers.Serializer):
    action  = serializers.ChoiceField(choices=['approve', 'reject'])
    notes   = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['action'] == 'reject' and not data.get('rejection_reason'):
            raise serializers.ValidationError(
                {"rejection_reason": "Rejection reason is required when rejecting a claim."})
        return data


class ProcessReimbursementSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=Reimbursement.Method.choices)
    payment_ref    = serializers.CharField(required=False, allow_blank=True)
    notes          = serializers.CharField(required=False, allow_blank=True)


class PolicyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PolicyRule
        fields = ['id', 'name', 'rule_type', 'expense_category',
                  'threshold_amount', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
