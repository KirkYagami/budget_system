from rest_framework import serializers
from .models import ApprovalLog, ClaimAttachment, ExpenseClaim, PolicyRule, Reimbursement


class ClaimAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.StringRelatedField(source='uploaded_by', read_only=True)

    class Meta:
        model  = ClaimAttachment
        fields = ['id', 'claim', 'file', 'file_type', 'filename',
                  'file_size', 'uploaded_by_name', 'uploaded_at']
        read_only_fields = ['id', 'claim', 'filename', 'file_size', 'uploaded_by_name', 'uploaded_at']

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        f = validated_data.get('file')
        if f:
            validated_data['filename']  = f.name
            validated_data['file_size'] = f.size
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
    """
    Full claim serializer.
    On CREATE: accepts optional `attachments` as a list of uploaded files.
    On READ:   returns full nested attachments + approval log.
    """
    submitted_by_name    = serializers.StringRelatedField(source='submitted_by', read_only=True)
    manager_name         = serializers.StringRelatedField(source='manager', read_only=True)
    budget_name          = serializers.StringRelatedField(source='budget', read_only=True)
    attachments          = ClaimAttachmentSerializer(many=True, read_only=True)
    approval_logs        = ApprovalLogSerializer(many=True, read_only=True)
    reimbursement_detail = ReimbursementSerializer(source='reimbursement', read_only=True)

    # Write-only field: list of files sent with the create request
    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="Attach one or more files (receipts/invoices) with the claim. Use multipart/form-data.",
    )
    file_types = serializers.ListField(
        child=serializers.ChoiceField(choices=ClaimAttachment.FileType.choices),
        write_only=True,
        required=False,
        help_text=(
            "File type for each uploaded file, in the same order as `uploaded_files`. "
            "Options: invoice | receipt | quote | contract | other. "
            "Defaults to 'receipt' if omitted."
        ),
    )

    class Meta:
        model  = ExpenseClaim
        fields = [
            'id', 'claim_number', 'claim_type', 'expense_category', 'payment_type',
            'title', 'description', 'amount', 'currency', 'expense_date',
            'submitted_by', 'submitted_by_name', 'budget', 'budget_name',
            'budget_category', 'manager', 'manager_name',
            'status', 'rejection_reason', 'policy_validated', 'policy_notes',
            'is_reusable', 'added_to_inventory', 'po_number',
            # write-only attachment helpers
            'uploaded_files', 'file_types',
            # read-only nested
            'attachments', 'approval_logs', 'reimbursement_detail',
            'submitted_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'claim_number', 'submitted_by', 'status',
            'policy_validated', 'policy_notes', 'submitted_at',
            'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        # Pop attachment data before saving claim
        uploaded_files = validated_data.pop('uploaded_files', [])
        file_types     = validated_data.pop('file_types', [])

        validated_data['submitted_by'] = self.context['request'].user
        if not validated_data.get('manager'):
            validated_data['manager'] = self.context['request'].user.manager

        claim = super().create(validated_data)

        # Save each attached file
        user = self.context['request'].user
        for i, f in enumerate(uploaded_files):
            ftype = file_types[i] if i < len(file_types) else ClaimAttachment.FileType.RECEIPT
            ClaimAttachment.objects.create(
                claim       = claim,
                file        = f,
                file_type   = ftype,
                filename    = f.name,
                file_size   = f.size,
                uploaded_by = user,
            )

        return claim


class ExpenseClaimListSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.StringRelatedField(source='submitted_by', read_only=True)
    attachment_count  = serializers.SerializerMethodField()

    class Meta:
        model  = ExpenseClaim
        fields = ['id', 'claim_number', 'claim_type', 'expense_category',
                  'title', 'amount', 'currency', 'status',
                  'submitted_by_name', 'expense_date', 'attachment_count', 'created_at']

    def get_attachment_count(self, obj):
        return obj.attachments.count()


# ─── Action Serializers ───────────────────────────────────────────────────────

class ApprovalActionSerializer(serializers.Serializer):
    action           = serializers.ChoiceField(choices=['approve', 'reject'])
    notes            = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['action'] == 'reject' and not data.get('rejection_reason'):
            raise serializers.ValidationError(
                {"rejection_reason": "Rejection reason is required when rejecting."})
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
