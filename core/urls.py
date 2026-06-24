from django.contrib import admin
from django.urls import path
from app.views import (
    index, compare_page, options_page,
    api_stock, api_compare, api_options, api_news, api_sparkline,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('compare/', compare_page, name='compare'),
    path('options/', options_page, name='options'),
    # JSON API
    path('api/stock/<str:ticker_sym>/', api_stock, name='api_stock'),
    path('api/compare/', api_compare, name='api_compare'),
    path('api/options/<str:ticker_sym>/', api_options, name='api_options'),
    path('api/news/<str:ticker_sym>/', api_news, name='api_news'),
    path('api/sparkline/<str:ticker_sym>/', api_sparkline, name='api_sparkline'),
]