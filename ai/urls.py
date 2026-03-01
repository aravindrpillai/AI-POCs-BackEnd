from django.urls import path
from django.contrib import admin
from cv.views.cv_upload_api import CVUploadAPIView
from cv.views.cv_search_api import CVSearchAPIView
from claims.views import ClaimsAPIView, ClaimsFileUploadView

urlpatterns = [
    path('admin/', admin.site.urls),

    #Resume AI
    path("cv/candidate/upload/", CVUploadAPIView.as_view(), name="cv-upload"),
    path("cv/candidate/search/", CVSearchAPIView.as_view(), name="cv-search-full"),
    path("cv/candidate/search/<str:id>/", CVSearchAPIView.as_view(), name="cv-search-single"),
    
     
    #Claims
    path("claims/conversation/", ClaimsAPIView.as_view()),
    path("claims/conversation/<uuid:conv_id>/", ClaimsAPIView.as_view()),
    path("claims/conversation/<uuid:conv_id>/upload/", ClaimsFileUploadView.as_view())

]
