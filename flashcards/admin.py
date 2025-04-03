from django.contrib import admin
from .models import Flashcard

@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('word', 'translation', 'category')
    list_filter = ('category',)
    search_fields = ('word', 'translation')