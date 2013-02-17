# Copyright: 2011 Prashant Kumar <contactprashantat AT gmail DOT com>
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Test for security.textcha
"""

from flask import current_app as app
from flask import g as flaskg

from MoinMoin.security.textcha import TextCha, TextChaValid, TextChaizedForm
from MoinMoin.constants.keys import LOCALE


class TestTextCha(object):
    """ Test: class TextCha """
    def setup_method(self, method):
        cfg = app.cfg
        cfg.textchas = {'test_user_locale':
                            {'Good Question': 'Good Answer',
                            'What is the question?': 'Test_Answer'}
                       }
        cfg.secrets['security/textcha'] = "test_secret"
        flaskg.user.profile[LOCALE] = 'test_user_locale'

    def teardown_method(self, method):
        cfg = app.cfg
        cfg.textchas = None
        cfg.secrets.pop('security/textcha')
        flaskg.user.profile[LOCALE] = None

    def test_textcha(self):
        """ test for textchas and its attributes """
        test_form = TextChaizedForm()
        test_form['textcha_question'].value = None

        textcha_obj = TextCha(test_form)

        # test for textcha
        test_textchas = textcha_obj.textchas
        expected_textchas = {'Good Question': 'Good Answer',
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
        test_form['textcha_question'].value = 'What is the question? 9876543210' + test_signature
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

    def test_amend_form(self):
        # textchas are disabled for 'some_locale'
        flaskg.user.profile[LOCALE] = 'some_locale'
        test_form = TextChaizedForm()
        test_form['textcha_question'].value = None
        textcha_obj = TextCha(test_form)
        # before calling amend_form
        assert not textcha_obj.form['textcha_question'].optional
        assert not textcha_obj.form['textcha'].optional
        # on calling amend_form
        textcha_obj.amend_form()
        assert textcha_obj.form['textcha_question'].optional
        assert textcha_obj.form['textcha'].optional


class TestTextChaValid(object):
    """ Test: class TextChaValid """
    def setup_method(self, method):
        cfg = app.cfg
        cfg.textchas = {'test_user_locale':
                            {'Good Question': 'Good Answer'}
                       }
        cfg.secrets['security/textcha'] = "test_secret"
        flaskg.user.profile[LOCALE] = 'test_user_locale'

    def teardown_method(self, method):
        cfg = app.cfg
        cfg.textchas = None
        cfg.secrets.pop('security/textcha')
        flaskg.user.profile[LOCALE] = None

    class Element(object):
        def __init__(self):
            self.parent = None
            self.value = 'Good Answer'

    def test_validate(self):
        test_form = TextChaizedForm()
        textchavalid_obj = TextChaValid()
        test_element = self.Element()
        test_element.parent = test_form
        result = textchavalid_obj.validate(test_element, 'test_state')
        assert result
