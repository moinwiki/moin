//
// All translatable strings defined in other Javascript files must also be defined within i18n_dict below.
// The strange format will be mangled to normal by jinja before being passed to a browser.
//
// To jslint this jinja template file, copy and paste from a browser tool that displays js code.
//
/*jslint browser: true, nomen: true, todo: true*/
/*global $:true, _:true*/

// The _ function is defined in common.js.

$(document).ready(function () {
    'use strict';
    var i18n_dict = {
        "Hide comments": "{{ _("Hide comments") }}",
        "Show comments": "{{ _("Show comments") }}",
        "Hide transclusions": "{{ _("Hide transclusions") }}",
        "Show transclusions": "{{ _("Show transclusions") }}",
        "Hide tags": "{{ _("Hide tags") }}",
        "Show all tags": "{{ _("Show all tags") }}",
        "Your changes will be discarded if you leave this page without saving.": "{{ _("Your changes will be discarded if you leave this page without saving.") }}",
        "You missed! Double-click on text or to the right of text to auto-scroll text editor.": "{{ _("You missed! Double-click on text or to the right of text to auto-scroll text editor.") }}",
        "Your browser is obsolete. Upgrade to gain auto-scroll text editor feature.": "{{ _("Your browser is obsolete. Upgrade to gain auto-scroll text editor feature.") }}",
        "Deleting..": "{{ _("Deleting..") }}",
        "Destroying..": "{{ _("Destroying..") }}",
        "Items deleted: ": "{{ _("Items deleted: ") }}",
        "Items destroyed: ": "{{ _("Items destroyed: ") }}",
        ", Not authorized, items not deleted: ": "{{ _(", Not authorized, items not deleted: ") }}",
        ", Not authorized, items not destroyed: ": "{{ _(", Not authorized, items not destroyed: ") }}",
        "All changes will be discarded!": "{{ _("All changes will be discarded!") }}",
        "Download failed, no items were selected.": "{{ _("Download failed, no items were selected.") }}",
        "Your saved draft has been loaded.": "{{ _("Your saved draft has been loaded.") }}",
        "Your edit lock will expire in 1 minute: ": "{{ _("Your edit lock will expire in 1 minute: ") }}",
        "Add optional comment for Delete change log. ": "{{ _("Add optional comment for Delete change log. ") }}",
        "Add optional comment for Destroy change log. ": "{{ _("Add optional comment for Destroy change log. ") }}",
        "Action complete.": "{{ _("Action complete.") }}"
    };

    $.i18n.setDictionary(i18n_dict);
});
