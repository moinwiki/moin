//
// All translatable strings defined in other Javascript files must also be defined within i18n_dict below.
// To jslint this jinja template file, copy and paste from a browser tool that displays js code.
//
/*jslint browser: true, nomen: true, todo: true*/
/*global $:true, _:true*/

function _(text) {
    'use strict';
    return $.i18n._(text);
}

$(document).ready(function () {
    'use strict';
    var i18n_dict = {
        "Hide comments": "{{ _("Hide comments") }}",
        "Show comments": "{{ _("Show comments") }}",
        "Hide transclusions": "{{ _("Hide transclusions") }}",
        "Show transclusions": "{{ _("Show transclusions") }}",
        "Hide tags": "{{ _("Hide tags") }}",
        "Show all tags": "{{ _("Show all tags") }}",
        "Select All": "{{  _("Select All") }}",
        "Deselect All": "{{  _("Deselect All") }}",
        "Your changes will be discarded if you leave this page without saving.": "{{ _("Your changes will be discarded if you leave this page without saving.") }}",
        "You missed! Double-click on text or to the right of text to auto-scroll text editor.": "{{ _("You missed! Double-click on text or to the right of text to auto-scroll text editor.") }}",
        "Your browser is obsolete. Upgrade to gain auto-scroll text editor feature.": "{{ _("Your browser is obsolete. Upgrade to gain auto-scroll text editor feature.") }}",
        "Your browser is old. Upgrade to gain auto-scroll page after edit feature.": "{{ _("Your browser is old. Upgrade to gain auto-scroll page after edit feature.") }}",
        "Deleting": "{{ _("Deleting") }}",
        "Deleting..": "{{ _("Deleting..") }}",
        "Destroying": "{{ _("Destroying") }}",
        "Destroying..": "{{ _("Destroying..") }}",
        "Items deleted: ": "{{ _("Items deleted: ") }}",
        "Items destroyed: ": "{{ _("Items destroyed: ") }}",
        ", Items not deleted: ": "{{ _(", Items not deleted: ") }}",
        ", Items not destroyed: ": "{{ _(", Items not destroyed: ") }}",
        "Nothing was selected.": "{{ _("Nothing was selected.") }}"
    };

    $.i18n.setDictionary(i18n_dict);
});
