from rest_framework.routers import DefaultRouter
from .views import DataTableFormatViewSet

router = DefaultRouter(trailing_slash=True)
router.register('table', DataTableFormatViewSet, basename='data-table')

urlpatterns = router.urls
