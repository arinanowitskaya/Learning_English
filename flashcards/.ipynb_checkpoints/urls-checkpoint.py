from django.urls import path
from .views import FlashcardListView, quiz_view, FlashcardCreateView

urlpatterns = [
    path('', FlashcardListView.as_view(), name='flashcards-list'),
    path('quiz/', quiz_view, name='quiz'),
    path('create/', FlashcardCreateView.as_view(), name='create-flashcard'),
]