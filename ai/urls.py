from django.urls import path
from django.contrib import admin
from cv.views.cv_upload_api import CVUploadAPIView
from cv.views.cv_search_api import CVSearchAPIView
from claims.views import ClaimsAPIView, ClaimsFileUploadView, ClaimPromptsAPIView
from finance.views import FinancialAdvisorView, FinancialAdvisorReportGenerator
from files.views.file_api import FileAPIView
from files.views.chat_api import ChatAPIView

urlpatterns = [
    path('admin/', admin.site.urls),

    #Resume AI
    path("cv/candidate/upload/", CVUploadAPIView.as_view(), name="cv-upload"),
    path("cv/candidate/search/", CVSearchAPIView.as_view(), name="cv-search-full"),
    path("cv/candidate/search/<str:id>/", CVSearchAPIView.as_view(), name="cv-search-single"),
    
     
    #Claims
    path("claims/prompts/", ClaimPromptsAPIView.as_view(), name="claim-prompts-list-create"),
    path("claims/prompts/<uuid:uid>/", ClaimPromptsAPIView.as_view(), name="claim-prompts-detail"),
    path("claims/conversation/", ClaimsAPIView.as_view()),
    path("claims/conversation/<uuid:conv_id>/", ClaimsAPIView.as_view()),
    path("claims/conversation/<uuid:conv_id>/upload/", ClaimsFileUploadView.as_view()),
    
     
    #Finance
    path("ai/finance/", FinancialAdvisorView.as_view()),
    path("ai/finance/<uuid:conv_id>/", FinancialAdvisorView.as_view()),
    path("ai/finance/<uuid:conv_id>/report/", FinancialAdvisorReportGenerator.as_view()),
    
    
    path("ai/files/filehandler/", FileAPIView.as_view()),
    path('ai/files/chat/', ChatAPIView.as_view()),
]