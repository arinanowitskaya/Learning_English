from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from ..models import Flashcard
from ..views import FlashcardListView, FlashcardCreateView, quiz_view

# Categories for testing
CATEGORIES = ['noun', 'verb', 'adjective', 'adverb']

class FlashcardModelTest(TestCase):
    def setUp(self):
        self.flashcard_data = {
            'word': 'hello',
            'translation': 'привет',
            'example': 'Hello world',
            'category': 'noun'
        }

    def test_create_flashcard(self):
        """Test flashcard creation with valid data"""
        for category in CATEGORIES:
            with self.subTest(category=category):
                data = self.flashcard_data.copy()
                data['category'] = category
                flashcard = Flashcard.objects.create(**data)
                self.assertEqual(flashcard.category, category)

    def test_word_validation(self):
        """Test word field validation"""
        # Test with numbers in word
        with self.assertRaises(ValidationError):
            flashcard = Flashcard(word='h3llo', translation='привет', category='noun')
            flashcard.full_clean()

    def test_translation_validation(self):
        """Test translation field validation"""
        # Test with numbers in translation
        with self.assertRaises(ValidationError):
            flashcard = Flashcard(word='hello', translation='привет123', category='verb')
            flashcard.full_clean()

    def test_unique_word_constraint(self):
        """Test word uniqueness"""
        Flashcard.objects.create(**self.flashcard_data)
        with self.assertRaises(Exception):
            Flashcard.objects.create(**self.flashcard_data)


class FlashcardListViewTest(TestCase):
    def setUp(self):
        self.url = reverse('flashcards-list')
        # Create flashcards with different categories
        Flashcard.objects.create(word='apple', translation='яблоко', category='noun')
        Flashcard.objects.create(word='run', translation='бежать', category='verb')
        Flashcard.objects.create(word='beautiful', translation='красивый', category='adjective')
        Flashcard.objects.create(word='quickly', translation='быстро', category='adverb')

    def test_view_url_exists(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'flashcards/list.html')

    def test_view_ordering_by_category(self):
        response = self.client.get(self.url)
        flashcards = response.context['flashcards']
        # Should be ordered by category then word
        self.assertEqual(flashcards[0].category, 'adjective')
        self.assertEqual(flashcards[1].category, 'adverb')
        self.assertEqual(flashcards[2].category, 'noun')
        self.assertEqual(flashcards[3].category, 'verb')


class FlashcardCreateViewTest(TestCase):
    def setUp(self):
        self.url = reverse('flashcards-create')
        self.valid_data = {
            'word': 'new',
            'translation': 'новый',
            'example': 'New word',
            'category': 'noun'
        }

    def test_view_url_exists(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_valid_form_submission_for_all_categories(self):
        for category in CATEGORIES:
            with self.subTest(category=category):
                data = self.valid_data.copy()
                data['category'] = category
                data['word'] = f'new_{category}'  # Unique word for each test
                response = self.client.post(self.url, data=data)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(Flashcard.objects.filter(word=f'new_{category}').exists())

    def test_invalid_word_submission(self):
        invalid_data = self.valid_data.copy()
        invalid_data['word'] = 'n3w'
        response = self.client.post(self.url, data=invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Flashcard.objects.filter(word='n3w').exists())

    def test_duplicate_word_submission(self):
        Flashcard.objects.create(**self.valid_data)
        response = self.client.post(self.url, data=self.valid_data)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('This word already exists', str(messages[0]))


class QuizViewTest(TestCase):
    def setUp(self):
        self.url = reverse('quiz')
        self.client = Client()
        # Create test flashcards with different categories
        self.flashcards = []
        for i, category in enumerate(CATEGORIES):
            for j in range(3):  # 3 flashcards per category
                self.flashcards.append(
                    Flashcard.objects.create(
                        word=f'{category}_{j}',
                        translation=f'trans_{category}_{j}',
                        category=category
                    )
                )

    def test_quiz_view_with_no_flashcards(self):
        Flashcard.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)

    def test_quiz_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('questions', response.context)
        # Should get 7 questions (or less if not enough flashcards)
        self.assertLessEqual(len(response.context['questions']), 7)

    def test_quiz_questions_distribution(self):
        """Test that questions come from different categories"""
        response = self.client.get(self.url)
        questions = response.context['questions']
        categories_in_quiz = set(q['flashcard'].category for q in questions)
        self.assertGreaterEqual(len(categories_in_quiz), min(3, len(CATEGORIES))

    def test_quiz_view_post(self):
        # First GET to generate quiz
        get_response = self.client.get(self.url)
        self.assertEqual(get_response.status_code, 200)
        
        # Prepare POST data with correct answers
        post_data = {}
        for i, question in enumerate(get_response.context['questions']):
            post_data[f'answer_{i}'] = question['flashcard'].translation
        
        # Submit answers
        post_response = self.client.post(self.url, post_data)
        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(post_response.context['score'], len(post_data))
        self.assertEqual(post_response.context['percentage'], 100)

    def test_quiz_session_management(self):
        self.client.get(self.url)
        self.assertIn('quiz_flashcards_ids', self.client.session)
        
        # Prepare POST data
        post_data = {}
        response = self.client.get(self.url)
        for i, question in enumerate(response.context['questions']):
            post_data[f'answer_{i}'] = question['flashcard'].translation
        
        self.client.post(self.url, post_data)
        self.assertNotIn('quiz_flashcards_ids', self.client.session)


class FlashcardFormTest(TestCase):
    def setUp(self):
        self.valid_data = {
            'word': 'valid',
            'translation': 'валидный',
            'example': 'Valid example',
            'category': 'noun'
        }
        Flashcard.objects.create(**self.valid_data)

    def test_valid_form_for_all_categories(self):
        for category in CATEGORIES:
            with self.subTest(category=category):
                form_data = {
                    'word': f'new_{category}',
                    'translation': 'новый',
                    'example': 'New example',
                    'category': category
                }
                form = FlashcardForm(data=form_data)
                self.assertTrue(form.is_valid())

    def test_invalid_category(self):
        form_data = self.valid_data.copy()
        form_data['category'] = 'invalid_category'
        form_data['word'] = 'unique_word'
        form = FlashcardForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)