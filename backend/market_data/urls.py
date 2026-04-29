from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BrandDominanceView, DataTableFormatViewSet, EvolutionOptionsView, EvolutionChartView

router = DefaultRouter(trailing_slash=True)
router.register('table', DataTableFormatViewSet, basename='data-table')

urlpatterns = router.urls + [
    path('dominance/', BrandDominanceView.as_view(), name='brand-dominance'),
    path('evolution/options/', EvolutionOptionsView.as_view(), name='evolution-options'),
    path('evolution/chart/', EvolutionChartView.as_view(), name='evolution-chart'),
]
