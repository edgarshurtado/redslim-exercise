from decimal import Decimal, ROUND_HALF_UP

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from rest_framework import serializers, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from market_data.models import Data

_ORDERING_MAP = {
    'market': 'market__description',
    'product': 'product__description',
    'brand': 'product__sub_brand__brand__description',
    'sub_brand': 'product__sub_brand__description',
    'value': 'value',
    'date': 'date',
    'period_weeks': 'period_weeks',
    'weighted_distribution': 'weighted_distribution',
}


class _TableOrderingFilter(OrderingFilter):
    def get_ordering(self, request, queryset, view):
        param = request.query_params.get(self.ordering_param)
        if param:
            fields = []
            for term in param.split(','):
                term = term.strip()
                desc = term.startswith('-')
                orm_field = _ORDERING_MAP.get(term.lstrip('-'))
                if orm_field:
                    fields.append(f'-{orm_field}' if desc else orm_field)
            if fields:
                return fields
        return self.get_default_ordering(view)


class _TablePagination(PageNumberPagination):
    page_size = 50  # fixed per spec; not overridable via query param


class _DataTableSerializer(serializers.ModelSerializer):
    market = serializers.CharField(source='market.description')
    product = serializers.CharField(source='product.description')
    brand = serializers.CharField(source='product.sub_brand.brand.description')
    sub_brand = serializers.CharField(source='product.sub_brand.description')

    class Meta:
        model = Data
        fields = [
            'id', 'market', 'product', 'brand', 'sub_brand',
            'value', 'date', 'period_weeks', 'weighted_distribution',
        ]


class DataTableFormatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Data.objects.select_related(
        'market',
        'product__sub_brand',
        'product__sub_brand__brand',
    ).order_by('-date')
    serializer_class = _DataTableSerializer
    pagination_class = _TablePagination
    filter_backends = [_TableOrderingFilter]


class BrandDominanceView(APIView):
    def get(self, request):
        qs = Data.objects.values(
            brand=F('product__sub_brand__brand__description')
        ).annotate(
            total_value=Sum('value'),
            wtd_numerator=Sum(
                ExpressionWrapper(
                    F('value') * F('weighted_distribution'),
                    output_field=DecimalField(max_digits=20, decimal_places=4),
                ),
                filter=Q(weighted_distribution__isnull=False),
            ),
            wtd_denominator=Sum(
                'value',
                filter=Q(weighted_distribution__isnull=False),
            ),
        ).order_by('-total_value')

        results = []
        for row in qs:
            wtd = None
            if row['wtd_numerator'] is not None and row['wtd_denominator']:
                wtd = (row['wtd_numerator'] / row['wtd_denominator']).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            results.append({
                'brand': row['brand'],
                'total_value': str(row['total_value']),
                'weighted_avg_wtd': str(wtd) if wtd is not None else None,
            })

        return Response(results)
