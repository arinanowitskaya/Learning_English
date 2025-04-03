from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class Flashcard(models.Model):
    CATEGORY_CHOICES = [
        ('noun', 'Noun'),
        ('verb', 'Verb'),
        ('adjective', 'Adjective'),
        ('adverb', 'Adverb'),
    ]
    
    word = models.CharField(max_length=100)
    translation = models.CharField(max_length=100)
    example = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    def __str__(self):
        return f"{self.word} ({self.get_category_display()})"