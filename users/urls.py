from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import CustomTokenObtainPairView
from .views import RegisterView, LoginView, LogoutView, ProtectedAPIView

app_name = 'users'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('protected/', ProtectedAPIView.as_view(), name='protected'),
]
