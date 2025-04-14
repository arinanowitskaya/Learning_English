from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Flashcard
import random

class FlashcardListView(ListView):
    model = Flashcard
    template_name = 'flashcards/list.html'
    context_object_name = 'flashcards'
    
    def get_queryset(self):
        return Flashcard.objects.all().order_by('category', 'word')

def quiz_view(request):
    # Получаем все карточки
    all_flashcards = list(Flashcard.objects.all())
    if not all_flashcards:
        return render(request, 'flashcards/quiz.html', {'error': 'No flashcards available'})

    if request.method == 'POST':
        # Восстанавливаем порядок карточек из сессии
        quiz_flashcards_ids = request.session.get('quiz_flashcards_ids')
        if not quiz_flashcards_ids:
            return redirect('quiz')
            
        quiz_flashcards = Flashcard.objects.filter(id__in=quiz_flashcards_ids)
        quiz_flashcards_dict = {card.id: card for card in quiz_flashcards}
        
        score = 0
        questions_data = []
        
        for i, card_id in enumerate(quiz_flashcards_ids):
            flashcard = quiz_flashcards_dict[card_id]
            user_answer = request.POST.get(f'answer_{i}', '').strip()
            correct_answer = flashcard.translation.strip()
            
            is_correct = user_answer.lower() == correct_answer.lower()
            if is_correct:
                score += 1
                
            questions_data.append({
                'word': flashcard.word,
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct
            })
        
        # Очищаем сессию
        if 'quiz_flashcards_ids' in request.session:
            del request.session['quiz_flashcards_ids']
        
        return render(request, 'flashcards/quiz_result.html', {
            'score': score,
            'total': len(quiz_flashcards_ids),
            'questions_data': questions_data,
            'percentage': int((score / len(quiz_flashcards_ids)) * 100) if quiz_flashcards_ids else 0
        })
    
    # Генерация нового теста
    quiz_flashcards = random.sample(all_flashcards, min(7, len(all_flashcards)))
    quiz_questions = []
    
    # Сохраняем ID карточек в сессии
    request.session['quiz_flashcards_ids'] = [card.id for card in quiz_flashcards]
    
    for i, flashcard in enumerate(quiz_flashcards):
        # Получаем 3 уникальных неправильных ответа
        wrong_answers = list(Flashcard.objects.exclude(
            id=flashcard.id
        ).exclude(
            translation=flashcard.translation
        ).values_list('translation', flat=True).distinct())
        
        wrong_answers = random.sample(wrong_answers, min(3, len(wrong_answers)))
        options = [flashcard.translation] + wrong_answers
        random.shuffle(options)
        
        quiz_questions.append({
            'index': i,
            'flashcard': flashcard,
            'options': options,
            'correct_answer': flashcard.translation
        })
    
    return render(request, 'flashcards/quiz.html', {
        'questions': quiz_questions
    })

class FlashcardCreateView(CreateView):
    model = Flashcard
    template_name = 'flashcards/create.html'
    fields = ['word', 'translation', 'example', 'category']
    success_url = reverse_lazy('flashcards-list')

    def form_valid(self, form):
        # Валидация слова
        word = form.cleaned_data.get('word')
        if not word.isalpha():
            form.add_error('word', 'Word should contain only letters')
            return self.form_invalid(form)
        
        # Валидация перевода (для русского языка)
        translation = form.cleaned_data.get('translation')
        if not all(c.isalpha() or c.isspace() for c in translation):
            form.add_error('translation', 'Translation should contain only letters and spaces')
            return self.form_invalid(form)
        
        # Проверка на дубликаты
        if Flashcard.objects.filter(word__iexact=word).exists():
            form.add_error('word', 'This word already exists')
            return self.form_invalid(form)
            
        messages.success(self.request, 'Flashcard created successfully!')
        return super().form_valid(form)