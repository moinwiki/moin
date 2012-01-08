# Copyright: 2011 MoinMoin:MichaelMayorov
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MoinMoin search package
"""

from MoinMoin.i18n import L_

from flatland import Form, String, Boolean
from flatland.validation import Validator

class ValidSearch(Validator):
    """Validator for a valid search form
    """
    too_short_query_msg = L_('Search query too short.')

    def validate(self, element, state):
        if element['q'].value is None:
            # no query, nothing to search for
            return False
        if len(element['q'].value) < 2:
            return self.note_error(element, state, 'too_short_query_msg')
        return True

class SearchForm(Form):
    q = String.using(optional=False, default=u'').with_properties(autofocus=True, placeholder=L_("Search Query"))
    history = Boolean.using(label=L_('search also in non-current revisions'), optional=True)
    submit = String.using(default=L_('Search'), optional=True)

    validators = [ValidSearch()]



