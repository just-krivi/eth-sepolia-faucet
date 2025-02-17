from django.urls import path
from .views import FaucetFundView, FaucetStatsView

urlpatterns = [
    path("fund/", FaucetFundView.as_view(), name="faucet-fund"),
    path("stats/", FaucetStatsView.as_view(), name="faucet-stats"),
]
