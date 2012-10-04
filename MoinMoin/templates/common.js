//
// MoinMoin2 commonly used JavaScript functions
//
/*jslint browser: true, */
/*global $:false */

// This file is a Jinja2 template and is not jslint friendly in its raw state.
// To run jslint, use your browser debugging tools to view, copy and paste this file to jslint.


// Utility function to add a message to moin flash area.
var MOINFLASHHINT = "moin-flash moin-flash-hint",
    MOINFLASHINFO = "moin-flash moin-flash-info",
    MOINFLASHWARNING = "moin-flash moin-flash-warning",
    MOINFLASHERROR = "moin-flash moin-flash-error";
function moinFlashMessage(classes, message) {
    "use strict";
    var pTag = '<P class="' + classes + '">' + message + '</p>';
    $(pTag).appendTo($('#moin-flash'));
}


// Highlight currently selected link in side panel. Executed on page load
function selected_link() {
    "use strict";
    var selected = window.location.pathname,
        list = $('.panel'),
        i,
        j,
        nav_links,
        link;
    for (j = 0; j < list.length; j += 1) {
        nav_links = list[j].getElementsByTagName('a');

        for (i = 0; i < nav_links.length; i += 1) {
            link = nav_links[i].attributes.href.value;

            if (link === selected) {
                nav_links[i].setAttribute('class', 'current-link');
                break;
            }
        }
    }
}
$(document).ready(selected_link);


// Insert Zero-Width-Space characters into long text strings of textNode elements.  Executed on page load.
// Firefox does not support CSS with {word-wrap: break-word;} within tables.
// As a result, Firefox may display tables with long urls or page names as very wide tables.
// This function alters table cells by inserting a zero-width-space into long text strings after every 5 characters.
// The moin-wordbreak class is intended for use on TD elements, but may be used on TABLE, TR, THEAD, TBODY, or TFOOT.
function moinFirefoxWordBreak() {
    "use strict";
    // TODO:  Test for browser version when/if a future Firefox supports break-word within tables.
    if (!$.browser.mozilla) {
        return;
    }
    var child, words, parents, i, j;
    // Only textNodes are of interest, but there is no way to select them directly.
    // Select all elements with the moin-wordbreak class and add all selectable descendants of those elements.
    // Then search for children that are textNodes; TDs or THs and elements descended from them are likely parents of textNodes.
    parents = $(".moin-wordbreak").add(".moin-wordbreak *");
    for (i = 0; i < parents.length; i += 1) {
        child = parents[i].firstChild;
        while (child) {
            if (child.nodeType === 3) {
                words = child.textContent.split(" ");
                for (j = 0; j < words.length; j += 1) {
                    // \u200B denotes a zero-width-space character (for easy testing, replace with a visible character like Q)
                    words[j] = words[j].replace(/(.{5})/g, "$1\u200B");
                }
                child.textContent = words.join(" ");
            }
            child = child.nextSibling;
        }
    }
}
$(moinFirefoxWordBreak);



// toggleComments is executed when user clicks a Comments button and conditionally on dom ready.
var pageComments = null; // will hold list of elements with class "comment"
function toggleComments() {
    "use strict";
    // Toggle visibility of every tag with class "comment"
    var buttons = $('.moin-toggle-comments-button > a');
    if (pageComments.is(':hidden')) {
        pageComments.show();
        {{ "buttons.attr('title', '%s');" % _("Hide comments") }}
    } else {
        pageComments.hide();
        {{ "buttons.attr('title', '%s');" % _("Show comments") }}
    }
}

// Comments initialization is executed once after document ready.
function initToggleComments() {
    "use strict";
    var titles;
    pageComments = $('.comment');
    if (pageComments.length > 0) {
        // There are comments, so show itemview Comments button
        $('.moin-toggle-comments-button').css('display', '');
        // comments are visible; per user option, hide comments if there is not a <br id="moin-show-comments" />
        if (!document.getElementById('moin-show-comments')) {
            toggleComments();
        }
    }
}
$(document).ready(initToggleComments);



// toggleTransclusionOverlays is executed when user clicks a Transclusions button on the Show item page.
function toggleTransclusionOverlays() {
    "use strict";
    var overlays = $('.moin-item-overlay-ul, .moin-item-overlay-lr'),
        buttons;
    if (overlays.length > 0) {
        buttons = $('.moin-transclusions-button > a');
        if (overlays.is(':visible')) {
            overlays.hide();
            {{ "buttons.attr('title', '%s');" % _("Show transclusions") }}
        } else {
            overlays.show();
            {{ "buttons.attr('title', '%s');" % _("Hide transclusions") }}
        }
    }
}

// Transclusion initialization is executed once after document ready.
function initTransclusionOverlays() {
    "use strict";
    var elem, overlayUL, overlayLR, wrapper, wrappers, transclusions, titles,
        rightArrow = '\u2192';
    // get list of elements to be wrapped; must work in reverse order in case there are nested transclusions
    transclusions = $($('.moin-transclusion').get().reverse());
    transclusions.each(function (index) {
        elem = transclusions[index];
        // if this is the transcluded item page, do not wrap (avoid creating useless overlay links to same page)
        if (location.pathname !== elem.getAttribute('data-href')) {
            if (elem.tagName === 'DIV') {
                wrapper = $('<div class="moin-item-wrapper"></div>');
            } else {
                wrapper = $('<span class="moin-item-wrapper"></span>');
            }
            overlayUL = $('<a class="moin-item-overlay-ul"></a>');
            $(overlayUL).attr('href', elem.getAttribute('data-href'));
            $(overlayUL).append(rightArrow);
            overlayLR = $(overlayUL).clone(true);
            $(overlayLR).attr('class', 'moin-item-overlay-lr');
            // if the parent of this element is an A, then wrap parent (avoid A's within A's)
            if ($(elem).parent()[0].tagName === 'A') {
                elem = $(elem).parent()[0];
            }
            // wrap element, add UL and LR overlay siblings, and replace old elem with wrapped elem
            $(wrapper).append($(elem).clone(true));
            $(wrapper).append(overlayUL);
            $(wrapper).append(overlayLR);
            $(elem).replaceWith(wrapper);
        }
    });
    // if an element was wrapped above, then make the Transclusions buttons visible
    wrappers = $('.moin-item-wrapper');
    if (wrappers.length > 0) {
        $('.moin-transclusions-button').css('display', '');
    }
}
$(document).ready(initTransclusionOverlays);



// Executed on page load.  If logged in user has less than 6 quicklinks,  do nothing.
// Else, show the first five links, hide the others, and append a >>> button to show hidden quicklinks on mouseover.
function QuicklinksExpander() {
    "use strict";
    var QUICKLINKS_EXPAND = ">>>",
        QUICKLINKS_COLLAPSE = "<<<",
        QUICKLINKS_MAX = 5,
        newThis;
    // 8 helper functions
    function getLinks() {
        return $(".userlink:not(.moin-navibar-icon)");
    }
    function createIcon(txt) {
        var li = document.createElement("li"),
            arrows = document.createTextNode(txt);
        li.setAttribute("class", "moin-userlink moin-navibar-icon");
        li.appendChild(arrows);
        return li;
    }
    function appendIcon(txt) {
        var elem = createIcon(txt);
        document.getElementById("moin-navibar").appendChild(elem);
        return elem;
    }
    function shouldHide(links) {
        // links should be hidden only if user has created so many that it impacts nice page layout
        return (links.length > QUICKLINKS_MAX);
    }
    function getHideableLinks() {
        return getLinks().slice(QUICKLINKS_MAX);
    }
    function hideShowHideableLinks(action) {
        getHideableLinks().each(function (i) {
            if (action === "hide") {
                $(this).hide();
            } else {
                $(this).show();
            }
        });
    }
    function hideLinks() {
        hideShowHideableLinks("hide");
    }
    function showLinks() {
        hideShowHideableLinks("show");
    }

    this.getLinks = getLinks;
    this.appendIcon = appendIcon;
    this.shouldHide = shouldHide;
    this.getHideableLinks = getHideableLinks;
    this.hideLinks = hideLinks;
    this.showLinks = showLinks;
    this.navibar = $("#moin-header");
    this.link = this.getLinks();
    this.hideable = this.getHideableLinks();

    if (this.shouldHide(this.link)) {
        this.expandIcon = $(this.appendIcon(QUICKLINKS_EXPAND));
        this.closeIcon = $(this.appendIcon(QUICKLINKS_COLLAPSE));
        this.closeIcon.hide();
        // Hide everything after the first QUICKLINKS_MAX links
        this.hideLinks();
        newThis = this;
        // When the user mouses over the icon link,
        // Show the hidden links
        this.expandIcon.mouseenter(function (e) {
            newThis.showLinks();
            newThis.expandIcon.hide();
            newThis.closeIcon.show();
        });
        this.closeIcon.mouseenter(function (e) {
            newThis.hideLinks();
            newThis.expandIcon.show();
            newThis.closeIcon.hide();
        });
    }
}
$(document).ready(QuicklinksExpander);



// When a page has subitems, this toggles the subtrees in the Subitems sidebar.
function toggleSubtree(item) {
    "use strict";
    var subtree = $(item).siblings("ul");
    subtree.toggle(200);
}



// guessContentType is a helper function for the transcludeSubitem and linkSubItem functions defined below.
function guessContentType() {
    "use strict";
    // Used in the modify_text template to guess the data content type client-side
    // This approach has the advantage of reacting to content type changes for the
    // link/transclude code without having to re-fetch the page
    var match,
        meta_text = $("#f_meta_text").val(),
        ctype_regex = /["']contenttype["']\s*:\s*["']([\w-_+.]+\/[\w-_+.]+)(;|["'])/;
    if (meta_text) {
        match = ctype_regex.exec(meta_text);
        if (match) {return match[1]; }
    }
    // text/plain is the default value
    return "text/plain";
}

// Executed when user clicks transclude-action button defined in modify_text.html.
// When a page with subitems is modified, a subitems sidebar is present. User may
// position caret in textarea and click button to insert transclusion into textarea.
function transcludeSubitem(subitem_name, fullname) {
    "use strict";
    function moinwiki(subitem_name, fullname) {
        // note: keep the many plusses, to avoid jinja2 templating kicking in
        // when seeing two curly opening / closing braces
        return "{" + "{" + fullname.replace("{" + "{", "\\" + "}" + "}") + "}" + "} ";
    }
    function mediawiki(subitem_name, fullname) {
        // note: keep the many plusses, to avoid jinja2 templating kicking in
        // when seeing two curly opening / closing braces
        return "{" + "{:" + fullname.replace("}" + "}", "\\" + "}" + "}") + "}" + "} ";
    }
    function rst(subitem_name, fullname) {
        return "\n.. include:: " + subitem_name + "\n";
    }
    function docbook(subitem_name, fullname) {
        return ""; //XXX: the docbook converter currently doesn't handle transclusion with <ref> tags
    }
    var transclude_formats = {
            "text/x.moin.wiki" : moinwiki,
            "text/x.moin.creole" : moinwiki,
            "text/x-mediawiki" : mediawiki,
            "text/x-rst" : rst,
            "application/docbook+xml" : docbook,
            "text/plain" : function (x) {return x + " "; }
        },
        ctype = guessContentType(),
        input_element = $("#f_content_form_data_text"),
        ctype_format = transclude_formats[ctype];
    if (!ctype_format) {
        ctype_format = transclude_formats["text/plain"];
    }
    input_element.val(input_element.val() + ctype_format(subitem_name, fullname));
    input_element.focus();
}

// Executed when user clicks link-action button defined in modify_text.html.
// When a page with subitems is modified, a subitems sidebar is present. User may
// position caret in textarea and click button to insert link into textarea.
function linkSubitem(subitem_name, fullname) {
    "use strict";
    function moinwiki(subitem_name, fullname) {
        return "[[" + fullname.replace("]", "\\]") + "|" + subitem_name.replace("]", "\\]") + "]] ";
    }
    function rst(subitem_name, fullname) {
        return "`" + subitem_name.replace(">", "\\>").replace("`", "\\`") + " <" + fullname.replace(">", "\\>") + ">`_ ";
    }
    function docbook(subitem_name, fullname) {
        return '<ulink url="/' + fullname.replace('"', '\\"') + '">' + subitem_name + "</ulink>";
    }
    var link_formats = {
            "text/x.moin.wiki" : moinwiki,
            "text/x.moin.creole" : moinwiki,
            "text/x-mediawiki" : moinwiki,
            "text/x-rst" : rst,
            "application/docbook+xml" : docbook,
            "text/plain" : function (x) {return x + " "; }
        },
        ctype = guessContentType(),
        input_element = $("#f_content_form_data_text"),
        ctype_format = link_formats[ctype];
    if (!ctype_format) {
        ctype_format = link_formats["text/plain"];
    }
    input_element.val(input_element.val() + ctype_format(subitem_name, fullname));
    input_element.focus();
}



// Executed on page load.  If this is the user "Settings" page, make the long 6-form page
// appear as a shorter page with a row of tabs near the top.  User clicks a tab to select target form.
function initMoinTabs() {
    "use strict";
    // find all .moin-tabs elements and initialize them
    $('.moin-tabs').each(function () {
        var tabs = $(this),
            titles = $(document.createElement('ul')),
            lastLocationHash;
        titles.addClass('moin-tab-titles');

        // switching between tabs based on the current location hash
        function updateFromLocationHash() {
            if (location.hash !== undefined && location.hash !== '' && tabs.children(location.hash).length) {
                if (location.hash !== lastLocationHash) {
                    lastLocationHash = location.hash;
                    tabs.children('.moin-tab-body').hide();
                    tabs.children(location.hash).show();
                    titles.children('li').children('a').removeClass('current');
                    titles.children('li').children('a[href="' + location.hash + '"]').addClass('current');
                }
            } else {
                $(titles.children('li').children('a')[0]).click();
            }
        }

        // move all tab titles to an <ul> at the beginning of .moin-tabs
        tabs.children('.moin-tab-title').each(function () {
            var li = $(document.createElement('li')),
                a = $(this).children('a');
            a.click(function () {
                location.hash = this.hash;
                updateFromLocationHash();
                return false;
            });
            li.append(a);
            titles.append(li);
            $(this).remove();
        });
        tabs.prepend(titles);

        updateFromLocationHash();
        setInterval(updateFromLocationHash, 40); // there is no event for that
    });
}
$(document).ready(initMoinTabs);



// Executed on page load.  Useful only if this is the user "Settings" page.
// Saves initial values of user "Settings" forms on client side.
// Detects unsaved changes and sets visual indicator.
// Processes form Submit and displays status messages and updated data.
function initMoinUsersettings() {
    "use strict";
    // save initial values of each form
    $('#moin-usersettings form').each(function () {
        $(this).data('initialForm', $(this).serialize());
    });

    // check if any changes were made, add indicator if user changes tabs without saving form
    function changeHandler(ev) {
        var form = $(ev.currentTarget),
            title = $('.moin-tab-titles a.current', form.parentsUntil('.moin-tabs').parent()),
            e;
        if (form.data('initialForm') === form.serialize()) {
            // current values are identicaly to initial ones, remove all change indicators (if any)
            $('.change-indicator', title).remove();
        } else {
            // the values differ
            if (!$('.change-indicator', title).length) {
                // only add a change indicator if there none
                e = $(document.createElement('span'));
                e.addClass('change-indicator');
                e.text('*');
                title.append(e);
            }
        }
    }
    // attach above function to all forms on page
    $('#moin-usersettings form').change(changeHandler);

    // executed when user clicks submit button on one of the tabbed forms
    function submitHandler(ev) {
        var form = $(ev.target),
            button = $('button', form),
            buttonBaseText = button.html(),
            buttonDotList = [' .&nbsp;&nbsp;', ' &nbsp;.&nbsp;', ' &nbsp;&nbsp;.'],
            buttonDotIndex = 0,
            buttonDotAnimation;

        // disable the button
        button.attr('disabled', true);

        // remove change indicators from the current tab as we are now saving it
        $('.moin-tab-titles a.current .change-indicator',
                form.parentsUntil('.moin-tabs').parent()).remove();

        // animate the submit button to indicating a running request
        function buttonRunAnimation() {
            button.html(buttonBaseText + buttonDotList[buttonDotIndex % buttonDotList.length]);
            buttonDotIndex += 1;
        }
        buttonDotAnimation = setInterval(buttonRunAnimation, 500);
        buttonRunAnimation();

        // send the form to the server
        $.post(form.attr('action'), form.serialize(), function (data) {
            var i, f, newform;
            clearInterval(buttonDotAnimation);
            // if the response indicates a redirect, set the new location
            if (data.redirect) {
                location.href = data.redirect;
                return;
            }
            // remove all flash messages previously added via javascript
            $('#moin-flash .moin-flash-javascript').remove();
            // add new flash messages from the response
            for (i = 0; i < data.flash.length; i += 1) {
                f = $(document.createElement('p'));
                f.html(data.flash[i][0]);
                f.addClass('moin-flash');
                f.addClass('moin-flash-javascript');
                f.addClass('moin-flash-' + data.flash[i][1]);
                $('#moin-flash').append(f);
            }
            // get the new form element from the response
            newform = $(data.form);
            // set event handlers on the new form
            newform.submit(submitHandler);
            newform.change(changeHandler);
            // store the forms initial data
            newform.data('initialForm', newform.serialize());
            // replace the old form with the new one
            form.replaceWith(newform);
        }, 'json');
        return false;
    }
    // attach above function to all form submit buttons
    $('#moin-usersettings form').submit(submitHandler);
}
$(document).ready(initMoinUsersettings);


// This anonymous function supports doubleclick to edit, auto-scroll the edit textarea and page after edit
$(function () {
    // NOTE: if browser does not support sessionStorage, then auto-scroll is not available
    //       (sessionStorage is supported by FF3.5+, Chrome4+, Safari4+, Opera10.5+, and IE8+).
    //       IE8 does not scroll page after edit (cannot determine caret position within textarea).
    "use strict";

    var TOPID = 'moin-content',
        LINENOATTR = "data-lineno",
        MESSAGEMISSED = ' {{ _("You missed! Double-click on text or to the right of text to auto-scroll text editor.") }} ',
        MESSAGEOBSOLETE = ' {{ _("Your browser is obsolete. Upgrade to gain auto-scroll text editor feature.") }} ',
        MESSAGEOLD = ' {{ _("Your browser is old. Upgrade to gain auto-scroll page after edit feature.") }} ',
        OPERA = 'Opera', // special handling required because textareas have \r\n line endings
        modifyButton,
        lineno,
        message,
        caretLineno;

    // IE8 workaround for missing setSelectionRange
    function setSelection(textArea, charStart) {
        // scroll IE8 textarea, target line will be near bottom of textarea
        var range = textArea.createTextRange();
        range.collapse(true);
        range.moveEnd('character', charStart);
        range.moveStart('character', charStart);
        range.select();
        //warn user that features are missing with IE8
        moinFlashMessage(MOINFLASHWARNING, MESSAGEOLD);
    }

    // called after +modify page loads -- scrolls the textarea after a doubleclick
    function scrollTextarea(jumpLine) {
        // jumpLine is textarea scroll-to line
        var textArea = document.getElementById('f_content_form_data_text'),
            textLines,
            scrolledText,
            scrollAmount,
            textAreaClone;

        if (textArea && (textArea.setSelectionRange || textArea.createTextRange)) {
            window.scrollTo(0, 0);
            // get data from textarea, split into array of lines, truncate based on jumpLine, make into a string
            textLines = $(textArea).val();
            scrolledText = textLines.split("\n"); // all browsers yield \n rather than \r\n or \r
            scrolledText = scrolledText.slice(0, jumpLine);
            if (navigator.userAgent && navigator.userAgent.substring(0, OPERA.length) === OPERA) {
                scrolledText = scrolledText.join('\r\n') + '\r\n';
            } else {
                scrolledText = scrolledText.join('\n') + '\n';
            }
            // clone textarea, paste in truncated textArea data, measure height, delete clone
            textAreaClone = $(textArea).clone(true);
            textAreaClone = textAreaClone[0];
            textAreaClone.id = "moin-textAreaClone";
            textArea.parentNode.appendChild(textAreaClone);
            $("#moin-textAreaClone").val(scrolledText);
            textAreaClone.rows = 1;
            scrollAmount = textAreaClone.scrollHeight - 100; // get total height of clone - 100 pixels
            textAreaClone.parentNode.removeChild(textAreaClone);
            // position the caret
            textArea.focus();
            if (scrollAmount > 0) { textArea.scrollTop = scrollAmount; }
            if (textArea.setSelectionRange) {
                // html5 compliant browsers, highlight the position of the caret for a second or so
                textArea.setSelectionRange(scrolledText.length, scrolledText.length + 8);
                setTimeout(function () {textArea.setSelectionRange(scrolledText.length, scrolledText.length + 4); }, 1000);
                setTimeout(function () {textArea.setSelectionRange(scrolledText.length, scrolledText.length); }, 1500);
            } else{
                // IE8 workaround to position the caret and scroll textarea
                setSelection(textArea, scrolledText.length);
            }
        }
    }

    // called after a "show" page loads, scroll page to textarea caret position
    function scrollPage(lineno) {
        var elem = document.getElementById(TOPID),
            notFound = true,
            RADIX = 10,
            saveColor;

        lineno = parseInt(lineno, RADIX);
        // find a starting point at bottom of moin-content
        while (elem.lastChild) { elem = elem.lastChild; }
        // walk DOM backward looking for a lineno attr equal or less than lineno
        while (notFound && elem.id !== TOPID) {
            if (elem.hasAttribute && elem.hasAttribute(LINENOATTR) && parseInt(elem.getAttribute(LINENOATTR), RADIX) <= lineno) {
                notFound = false;
            }
            if (notFound) {
                if (elem.previousSibling) {
                    elem = elem.previousSibling;
                    while (elem.lastChild) { elem = elem.lastChild; }
                } else {
                    elem = elem.parentNode;
                }
            }
        }
        // scroll element into view and then back off 100 pixels
        // TODO: does not scroll when user setting for show comments is off; user toggles show comments on; user doubleclicks and updates comments; (elem has display:none)
        elem.scrollIntoView();
        window.scrollTo(window.pageXOffset, window.pageYOffset - 100);
        // highlight background of selected element for a second or so
        saveColor = elem.style.backgroundColor;
        elem.style.backgroundColor = 'yellow';
        setTimeout(function () { elem.style.backgroundColor = saveColor; }, 1500);
    }

    // called after user doubleclicks, return a line number close to doubleclick point
    function findLineNo(elem) {
        var lineno;
        // first try easy way via jquery checking event node and all parent nodes
        lineno = $(elem).closest("[" + LINENOATTR + "]");
        if (lineno.length) { return $(lineno).attr(LINENOATTR); }
        // walk DOM backward looking for a lineno attr among siblings, cousins, uncles...
        while (elem.id !== TOPID) {
            if (elem.hasAttribute && elem.hasAttribute(LINENOATTR)) {
                // not perfect, a lineno prior to target
                return elem.getAttribute(LINENOATTR);
            }
            if (elem.previousSibling) {
                elem = elem.previousSibling;
                while (elem.lastChild) { elem = elem.lastChild; }
            } else {
                elem = elem.parentNode;
            }
        }
        // user double-clicked on dead zone so we walked back to #moin-content
        return 0;
    }

    // called after user clicks OK button to save edit changes
    function getCaretLineno(textArea) {
        // return the line number of the textarea caret
        var caretPoint,
            textLines;
        if (textArea.selectionStart) {
            caretPoint = textArea.selectionStart;
        } else {
            // IE7, IE8 or
            // IE9 - user has clicked ouside of textarea and textarea focus and caret position has been lost
            return 0;
        }
        // get textarea text, split at caret, return number of lines before caret
        if (navigator.userAgent && navigator.userAgent.substring(0, OPERA.length) === OPERA) {
            textLines = textArea.value;
        } else {
            textLines = $(textArea).val();
        }
        textLines = textLines.substring(0, caretPoint);
        return textLines.split("\n").length;
    }

    // doubleclick processing starts here
    if (window.sessionStorage) {
        // Start of processing for "show" pages
        if (document.getElementById('moin-edit-on-doubleclick')) {
            // this is a "show" page and the edit on doubleclick option is set for this user
            modifyButton = $('.moin-modify-button')[0];
            if (modifyButton) {
                // add doubleclick event handler when user doubleclicks within the content area
                $('#moin-content').dblclick(function (e) {
                    // get clicked line number, save, and go to +modify page
                    lineno = findLineNo(e.target);
                    sessionStorage.moinDoubleLineNo = lineno;
                    document.location = modifyButton.href;
                });
            }
            if (sessionStorage.moinCaretLineNo) {
                // we have just edited this page; scroll "show" page to last position of caret in edit textarea
                scrollPage(sessionStorage.moinCaretLineNo);
                sessionStorage.removeItem('moinCaretLineNo');
            }
        }

        // Start of processing for "modify" pages
        if (sessionStorage.moinDoubleLineNo) {
            // this is a +modify page, scroll the textarea to the doubleclicked line
            lineno = sessionStorage.moinDoubleLineNo;
            sessionStorage.removeItem('moinDoubleLineNo');
            if (lineno === '0') {
                // give user a hint because the double-click was a miss
                moinFlashMessage(MOINFLASHINFO, MESSAGEMISSED);
                lineno = 1;
            }
            scrollTextarea(lineno - 1);
            // is option to scroll page after edit set?
            if (document.getElementById('moin-scroll-page-after-edit')) {
                // add click handler to OK (save) button to capture position of caret in textarea
                $("#f_submit").click(function () {
                    caretLineno = getCaretLineno(document.getElementById('f_content_form_data_text'));
                    // save lineno for use in "show" page load
                    if (caretLineno > 0) { sessionStorage.moinCaretLineNo = caretLineno; }
                });
            }
        }
    } else {
        // provide reduced functionality for obsolete browsers that do not support local storage: IE6, IE7, etc.
        if (document.getElementById('moin-edit-on-doubleclick')) {
            moinFlashMessage(MOINFLASHWARNING, MESSAGEOBSOLETE);
            modifyButton = $('.moin-modify-button')[0];
            if (modifyButton) {
                // add doubleclick event handler when user doubleclicks within the content area
                $('#moin-content').dblclick(function (e) {
                    document.location = modifyButton.href;
                });
            }
        }
    }
});
