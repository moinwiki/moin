from MoinMoin.security.textcha import TextCha
from flask import current_app as app
from flask import g as flaskg

import pytest

class TestTextCha(object):

    class Question():
        def __init__(self):
            self.value = None

    def test_textcha(self):
        question = self.Question()
        test_form = {'textcha_question':question}
        cfg = app.cfg
        cfg.textchas = {'test_user_locale': 
                            {'Good Question': 'Good Answer',
                            'What is the question?': 'Test_Answer'}
                       }
        cfg.secrets['security/textcha'] = "test_secret"
        flaskg.user.locale = 'test_user_locale'

        textcha_obj = TextCha(test_form)

        # test for textcha
        test_textchas = textcha_obj.textchas
        expected_textchas  = {'Good Question': 'Good Answer', 
                                'What is the question?': 'Test_Answer'}
        assert test_textchas == expected_textchas
        # test for the question
        test_question = textcha_obj.question
        possible_questions = ['Good Question', 'What is the question?']
        assert test_question in possible_questions
        # test for answer_re
        possible_answers = ['Good Answer', 'Test_Answer']
        result_answer1 = textcha_obj.answer_re.match(expected_textchas[test_question])
        test_answer = result_answer1.group()
        assert test_answer in possible_answers
        # invalid value
        result_answer2 = textcha_obj.answer_re.match('Bad Answer')
        assert not result_answer2
        # test for answer_regex
        result_answer = textcha_obj.answer_regex
        assert result_answer in possible_answers

        # when question is specified earlier
        test_signature = 'fb5a8cc203b07b66637aafa7b0647da17e249e9c'
        question.value = 'What is the question? 9876543210' + test_signature
        textcha_obj = TextCha(test_form)
        # test for the question
        test_question = textcha_obj.question
        expected_question = 'What is the question?'
        assert test_question == expected_question
        # test the answer
        test_answer = textcha_obj.answer_regex
        assert test_answer == 'Test_Answer'
        assert test_signature == textcha_obj.signature
        assert textcha_obj.timestamp == 9876543210

