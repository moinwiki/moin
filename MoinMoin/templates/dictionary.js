function _(text){
    return $.i18n._(text);
}

$(document).ready(function(){
     i18n_dict = {
        "Hide comments"  : "{{  _("Hide comments") }}",
        "Show comments"  : "{{  _("Show comments") }}",
        "Hide transclusions"  : "{{  _("Hide transclusions") }}",
        "Show transclusions"  : "{{  _("Show transclusions") }}",
        "Select All"  : "{{  _("Select All") }}",
        "Deselect All"  : "{{  _("Deselect All") }}",
        "Your changes will be discarded if you leave this page without saving." : "{{ _("Your changes will be discarded if you leave this page without saving.") }}",
        "You missed! Double-click on text or to the right of text to auto-scroll text editor."  : "{{ _("You missed! Double-click on text or to the right of text to auto-scroll text editor.") }}",
        "Your browser is obsolete. Upgrade to gain auto-scroll text editor feature."  : "{{ _("Your browser is obsolete. Upgrade to gain auto-scroll text editor feature.") }}",
        "Your browser is old. Upgrade to gain auto-scroll page after edit feature."  : "{{ _("Your browser is old. Upgrade to gain auto-scroll page after edit feature.") }}",
        "Deleting"  : "{{ _("Deleting") }}",
        "Destroying"  : "{{ _("Destroying") }}",
        "Items deleted: "  : "{{ _("Items deleted: ") }}",
        "Items destroyed: "  : "{{ _("Items destroyed: ") }}",
        ", Items not deleted: "  : "{{ _(", Items not deleted: ") }}",
        ", Items not destroyed: "  : "{{ _(", Items not destroyed: ") }}"
    };

    $.i18n.setDictionary(i18n_dict);
});
