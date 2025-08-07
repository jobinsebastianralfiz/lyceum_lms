#!/usr/bin/env python
"""
Example script to add questions to a quiz programmatically.
Run this from the Django shell: python manage.py shell < add_quiz_questions_example.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')
django.setup()

from apps.courses.models import Quiz, QuizQuestion, QuizChoice

def add_sample_questions_to_quiz(quiz_id):
    """Add sample questions to a quiz"""
    try:
        quiz = Quiz.objects.get(id=quiz_id)
        print(f"Adding questions to quiz: {quiz.title}")
        
        # Question 1: Multiple choice about Python
        question1 = QuizQuestion.objects.create(
            quiz=quiz,
            question_text="What is Python primarily known for?",
            points=5,
            explanation="Python is known for its simple, readable syntax that makes it beginner-friendly."
        )
        
        # Add choices for question 1
        QuizChoice.objects.create(
            question=question1,
            choice_text="Simple and readable syntax",
            is_correct=True
        )
        QuizChoice.objects.create(
            question=question1,
            choice_text="Complex syntax structure",
            is_correct=False
        )
        QuizChoice.objects.create(
            question=question1,
            choice_text="Only for web development",
            is_correct=False
        )
        QuizChoice.objects.create(
            question=question1,
            choice_text="Hardware programming only",
            is_correct=False
        )
        
        # Question 2: Python data types
        question2 = QuizQuestion.objects.create(
            quiz=quiz,
            question_text="Which of these is NOT a Python data type?",
            points=3,
            explanation="All the others (str, int, list) are built-in Python data types, but 'char' is not."
        )
        
        # Add choices for question 2
        QuizChoice.objects.create(
            question=question2,
            choice_text="str",
            is_correct=False
        )
        QuizChoice.objects.create(
            question=question2,
            choice_text="int",
            is_correct=False
        )
        QuizChoice.objects.create(
            question=question2,
            choice_text="char",
            is_correct=True
        )
        QuizChoice.objects.create(
            question=question2,
            choice_text="list",
            is_correct=False
        )
        
        # Question 3: Python variables
        question3 = QuizQuestion.objects.create(
            quiz=quiz,
            question_text="How do you create a variable in Python?",
            points=2,
            explanation="In Python, you simply assign a value to a variable name without declaring its type."
        )
        
        # Add choices for question 3
        QuizChoice.objects.create(
            question=question3,
            choice_text="var x = 5",
            is_correct=False
        )
        QuizChoice.objects.create(
            question=question3,
            choice_text="x = 5",
            is_correct=True
        )
        QuizChoice.objects.create(
            question=question3,
            choice_text="int x = 5",
            is_correct=False
        )
        QuizChoice.objects.create(
            question=question3,
            choice_text="declare x = 5",
            is_correct=False
        )
        
        print(f"✅ Successfully added 3 questions to '{quiz.title}'")
        print(f"Quiz now has {quiz.questions.count()} questions total")
        
        return True
        
    except Quiz.DoesNotExist:
        print(f"❌ Quiz with ID {quiz_id} not found")
        return False
    except Exception as e:
        print(f"❌ Error adding questions: {e}")
        return False

def list_all_quizzes():
    """List all available quizzes"""
    quizzes = Quiz.objects.all()
    print("\n=== Available Quizzes ===")
    for quiz in quizzes:
        print(f"ID: {quiz.id} | Title: {quiz.title} | Questions: {quiz.questions.count()}")
    print("========================\n")
    return quizzes

if __name__ == "__main__":
    print("🎯 Quiz Questions Management Script")
    print("=" * 40)
    
    # List all available quizzes
    quizzes = list_all_quizzes()
    
    if quizzes.exists():
        # Add questions to the first quiz as an example
        first_quiz = quizzes.first()
        print(f"Adding sample questions to: {first_quiz.title}")
        add_sample_questions_to_quiz(first_quiz.id)
        
        # Show updated question count
        print(f"\n📊 Quiz '{first_quiz.title}' now has {first_quiz.questions.count()} questions")
        
        # List all questions for this quiz
        print(f"\nQuestions in '{first_quiz.title}':")
        for i, question in enumerate(first_quiz.questions.all(), 1):
            print(f"{i}. {question.question_text} ({question.points} pts)")
            for j, choice in enumerate(question.choices.all(), 1):
                correct_mark = "✓" if choice.is_correct else " "
                print(f"   {j}. [{correct_mark}] {choice.choice_text}")
    else:
        print("❌ No quizzes found. Create a quiz first!")