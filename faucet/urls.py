from django.urls import path
from .views import FaucetFundView, FaucetStatsView
from . import views

urlpatterns = [
    path("fund", FaucetFundView.as_view(), name="faucet-fund"),
    path("stats", FaucetStatsView.as_view(), name="faucet-stats"),
    path("transactions", views.transaction_list, name="transaction-list"),
]
