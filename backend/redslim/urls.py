from django.urls import path, include

urlpatterns = [
    path('', include('hello.urls')),
    path('market-data/', include('market_data.urls')),
]
