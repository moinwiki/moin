# Copyright: 2007 by MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - Text CAPTCHAs

    This is just asking some (admin configured) questions and
    checking if the answer is as expected. It is up to the wiki
    admin to setup questions that a bot can not easily answer, but
    humans can. It is recommended to setup SITE SPECIFIC questions
    and not to share the questions with other sites (if everyone
    asks the same questions / expects the same answers, spammers
    could adapt to that).

    TODO:
    * roundtrip the question in some other way:
     * make sure a q/a pair in the POST is for the q in the GET before
    * make some nice CSS
    * make similar changes to GUI editor
"""


import re
import random

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app
from flask import request
from flask import flaskg

import hashlib
import hmac

from time import time

from flatland import Form, String
from flatland.validation import Validator

from MoinMoin.i18n import _, L_, N_

SHA1_LEN = 40 # length of hexdigest
TIMESTAMP_LEN = 10 # length of timestamp

class TextCha(object):
    """ Text CAPTCHA support """

    def __init__(self, form):
        """ Initialize the TextCha.

            :param form: flatland form to use; must subclass TextChaizedForm
        """
        self.user_info = flaskg.user.valid and flaskg.user.name or request.remote_addr
        self.textchas = self._get_textchas()
        if self.textchas:
            self.secret = app.cfg.secrets["security/textcha"]
            self.expiry_time = app.cfg.textchas_expiry_time
        self.init_qa(form['textcha_question'].value)
        self.form = form

    def _get_textchas(self):
        """ get textchas from the wiki config for the user's language (or default_language or en) """
        groups = flaskg.groups
        cfg = app.cfg
        user = flaskg.user
        disabled_group = cfg.textchas_disabled_group
        textchas = cfg.textchas

        use_textchas = not (disabled_group and user.name and user.name in groups.get(disabled_group, []))

        if textchas and use_textchas:
            locales = [user.locale, cfg.locale_default, 'en', ]
            for locale in locales:
                logging.debug(u"TextCha: trying locale == '%s'." % locale)
                if locale in textchas:
                    logging.debug(u"TextCha: using locale = '%s'" % locale)
                    return textchas[locale]

    def _compute_signature(self, question, timestamp):
        return hmac.new(self.secret, "%s%d" % (question, timestamp), digestmod=hashlib.sha1).hexdigest()

    def init_qa(self, question=None):
        """ Initialize the question / answer.

         :param question: If given, the given question will be used.
                          If None, a new question will be generated.
        """
        if self.is_enabled():
            if question is None:
                self.question = random.choice(self.textchas.keys())
                self.timestamp = time()
                self.signature = self._compute_signature(self.question, self.timestamp)
            else:
                # the signature is the last SHA1_LEN bytes of the question
                self.signature = question[-SHA1_LEN:]

                # operate on the remainder
                question = question[:-SHA1_LEN]

                try:
                    # the timestamp is the next TIMESTAMP_LEN bytes
                    self.timestamp = int(question[-TIMESTAMP_LEN:])
                except ValueError:
                    self.question = None
                else:
                    if self.timestamp + self.expiry_time < time():
                        self.question = None
                    else:
                        # there is a space between the timestamp and the question, so take away 1
                        self.question = question[:-TIMESTAMP_LEN - 1]

                        if self._compute_signature(self.question, self.timestamp) != self.signature:
                            self.question = None

            try:
                self.answer_regex = self.textchas[self.question]
                self.answer_re = re.compile(self.answer_regex, re.U|re.I)
            except KeyError:
                # this question does not exist, thus there is no answer
                self.answer_regex = ur"[Invalid question]"
                self.answer_re = None
                logging.warning(u"TextCha: Non-existing question '%s' for %s. May be invalid or user may be trying to cheat." % (
                                self.question, self.user_info))
            except re.error:
                logging.error(u"TextCha: Invalid regex in answer for question '%s'" % self.question)
                self.init_qa()

    def is_enabled(self):
        """ check if textchas are enabled.

            They can be disabled for all languages if you use textchas = None or = {},
            also they can be disabled for some specific language, like:
            textchas = {
                'en': {
                    'some question': 'some answer',
                    # ...
                },
                'de': {}, # having no questions for 'de' means disabling textchas for 'de'
                # ...
            }
        """
        return not not self.textchas # we don't want to return the dict

    def amend_form(self):
        """ Amend the form by doing the following:

            * set the question if textcha is enabled, or
            * make the fields optional if it isn't.
        """
        if self.is_enabled():
            if self.question:
                self.form['textcha_question'].set("%s %d%s" % (self.question, self.timestamp, self.signature))
        else:
            self.form['textcha_question'].optional = True
            self.form['textcha'].optional = True

class TextChaValid(Validator):
    """Validator for TextChas
    """
    textcha_incorrect_msg = L_('The entered TextCha was incorrect.')
    textcha_invalid_msg = L_('The TextCha question is invalid or has expired. Please try again.')

    def validate(self, element, state):
        textcha = TextCha(element.parent)

        if textcha.is_enabled():
            if textcha.answer_re is None:
                textcha.init_qa()
                textcha.amend_form()
                element.set("")
                return self.note_error(element, state, 'textcha_invalid_msg')
            if textcha.answer_re.match(element.value.strip()) is None:
                return self.note_error(element, state, 'textcha_incorrect_msg')

        return True

class TextChaizedForm(Form):
    """a form providing TextCha support"""
    textcha_question = String
    textcha = String.using(label=L_('TextCha')).validated_by(TextChaValid())
