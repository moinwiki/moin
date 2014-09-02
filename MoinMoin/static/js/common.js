//
// MoinMoin2 commonly used JavaScript functions
//
/*jslint browser: true, nomen: true, todo: true*/
/*global $:true, _:true*/

function MoinMoin() {
    "use strict";
}
// Utility function to add a message to moin flash area.
MoinMoin.prototype.MOINFLASHINFO = "moin-flash moin-flash-info";
MoinMoin.prototype.MOINFLASHWARNING = "moin-flash moin-flash-warning";
MoinMoin.prototype.moinFlashMessage = function (classes, message) {
    "use strict";
    var pTag = '<P class="' + classes + '">' + message + '</p>';
    $(pTag).appendTo($('#moin-flash'));
};


// Highlight currently selected link in side panel. Executed on page load
MoinMoin.prototype.selected_link = function () {
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
};


// toggleComments is executed when user clicks a Comments button and conditionally on dom ready.
MoinMoin.prototype.toggleComments = function () {
    "use strict";
    // Toggle visibility of every tag with class "comment"
    var pageComments = $('.comment'),   // will hold list of elements with class "comment"
        buttons = $('.moin-toggle-comments-button > a');
    if (pageComments.is(':hidden')) {
        pageComments.show();
        buttons.attr('title', _("Hide comments"));
    } else {
        pageComments.hide();
        buttons.attr('title', _("Show comments"));
    }
    return false;  // do not scroll to top of page
};

// Comments initialization is executed once after document ready.
MoinMoin.prototype.initToggleComments = function () {
    "use strict";
    var pageComments = $('.comment');
    if (pageComments.length > 0) {
        // There are comments, so show itemview Comments button
        $('.moin-toggle-comments-button').css('display', '');
        // comments are visible; per user option, hide comments if there is not a <br id="moin-show-comments" />
        if (!document.getElementById('moin-show-comments')) {
            this.toggleComments();
        }
    }
    $('.moin-toggle-comments-button').click(this.toggleComments);
};



// toggleTransclusionOverlays is executed when user clicks a Transclusions button on the Show item page.
MoinMoin.prototype.toggleTransclusionOverlays = function () {
    "use strict";
    var overlays = $('.moin-item-overlay-ul, .moin-item-overlay-lr'),
        buttons;
    if (overlays.length > 0) {
        buttons = $('.moin-transclusions-button > a, .moin-transclusions-button');
        if (overlays.is(':visible')) {
            overlays.hide();
            buttons.attr('title', _("Show transclusions"));
        } else {
            overlays.show();
            buttons.attr('title', _("Hide transclusions"));
        }
    }
    return false;  // do not scroll to top of page
};

// Transclusion initialization is executed once after document ready.
MoinMoin.prototype.initTransclusionOverlays = function () {
    "use strict";
    var elem, overlayUL, overlayLR, wrapper, wrappers, transclusions, classes,
        rightArrow = '\u2192',
        mediaTags = ['OBJECT', 'IMG', 'AUDIO', 'VIDEO' ];
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
            // copy user specified classes from img/object tag to wrapper
            if ($.inArray(elem.tagName, mediaTags) > -1) {
                // do not copy classes starting with moin-
                classes = $(elem).attr('class');
                classes = classes.split(" ").filter(function(c) {
                    return c.lastIndexOf('moin-', 0) !== 0;
                });
                $(wrapper).addClass(classes.join(' '));
            } else {
                // TODO: try to eliminate above else by changing include.py to
                //    do: <img class="moin-transclusion"...
                //    not: <span class="moin-transclusion"... <img...
                // copy all classes from img tags
                $(wrapper).addClass($(elem).find(">:first-child").attr('class'));
            }
            // insert wrapper after elem, append (move) elem, append overlays
            $(elem).after(wrapper);
            $(wrapper).append(elem);
            $(wrapper).append(overlayUL);
            $(wrapper).append(overlayLR);
        }
    });
    // if an element was wrapped above, then make the Transclusions buttons visible
    wrappers = $('.moin-item-wrapper');
    if (wrappers.length > 0) {
        $('.moin-transclusions-button').css('display', '');
    }
    $('.moin-transclusions-button').click(this.toggleTransclusionOverlays);
};



// Executed on page load.  If logged in user has less than 6 quicklinks,  do nothing.
// Else, show the first five links, hide the others, and append a >>> button to show hidden quicklinks on mouseover.
MoinMoin.prototype.QuicklinksExpander = function () {
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
        getHideableLinks().each(function () {
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
        this.expandIcon.mouseenter(function () {
            newThis.showLinks();
            newThis.expandIcon.hide();
            newThis.closeIcon.show();
        });
        this.closeIcon.mouseenter(function () {
            newThis.hideLinks();
            newThis.expandIcon.show();
            newThis.closeIcon.hide();
        });
    }
};



// When a page has subitems, this toggles the subtrees in the Subitems sidebar.
MoinMoin.prototype.toggleSubtree = function (item) {
    "use strict";
    var subtree = $(item).siblings("ul");
    subtree.toggle(200);
};



// OnMouseOver show the fqname of the item else only show the value/id.
function togglefqname() {
    "use strict";
    var fullname, value;
    $(".moin-fqname").hover(function () {
        fullname = $(this).attr('data-fqname');
        value = $(this).html();
        $(this).html(fullname);
    }, function () {
        $(this).html(value);
    });
}
$(document).ready(togglefqname);


// Executed when user clicks insert-name button defined in modify.html.
// When a page with subitems is modified, a subitems sidebar is present. User may
// position caret in textarea and click button to insert name into textarea.
MoinMoin.prototype.InsertName = function (fullname) {
    "use strict";
    var textArea, endPos, startPos;
    textArea = document.getElementById('f_content_form_data_text');
    startPos = textArea.selectionStart;
    endPos = textArea.selectionEnd;
    textArea.value = textArea.value.substring(0, startPos) + fullname + textArea.value.substring(endPos, textArea.value.length);
    textArea.focus();
    textArea.setSelectionRange(startPos + fullname.length, startPos + fullname.length);
};


// User Settings page enhancements - make long multi-form page appear as a shorter page
// with a row of tabs at the top or side that may be clicked to select a form.
MoinMoin.prototype.enhanceUserSettings = function () {
    "use strict";
    // do nothing if this is not a User Settings page
    if ($('#moin-usersettings').length === 0) { return; }

    // create a UL that will be displayed as row of tabs or column of buttons
    var tabs = $('#moin-usersettings'),
        titles = $('<ul class="moin-tab-titles">'),
        hashTag = window.location.hash,
        tab;
    // for each form on page, create a corresponding LI
    $('.moin-tab-body').each(function () {
        var li = $(document.createElement('li')),
        // copy a-tag defined in heading
            aTagClone = $(this).find('a').clone();
        li.append(aTagClone);
        titles.append(li);
        // add click handler to show this form and hide all others
        aTagClone.click(function (ev) {
            tab = this.hash;
            window.location.hash = tab;
            $('.moin-current-tab').removeClass('moin-current-tab');
            $(ev.target).addClass('moin-current-tab');
            tabs.children('.moin-tab-body').hide().removeClass('moin-current-form');
            tabs.children(tab).show().addClass('moin-current-form');
            return false;
        });
    });
    // if this is foobar (or similar sidebar theme) remove buttons that work when javascript is disabled
    $('.moin-tabs ul').remove();
    // add tabs/buttons with click handlers to top/side per theme template
    $('.moin-tabs').prepend(titles);

    // check for the hashtag and switch tab
    if (hashTag !== '') {
        tab = $('.moin-tab-titles li a[href="' + hashTag + '"]');
        if (tab.length !== 0) {
            $(tab)[0].click();
        }
    } else {
        // click a tab to show first form and hide all other forms
        $(titles.children('li').children('a')[0]).click();
    }

    // save initial values of each form; used in changeHandler to detect changes to a form
    $('#moin-usersettings form').each(function () {
        $(this).data('initialForm', $(this).serialize());
    });

    // add/remove "*" indicator if user changes/saves form
    function changeHandler(ev) {
        var form = $(ev.currentTarget),
            title = $('.moin-tab-titles a.moin-current-tab', form.parentsUntil('.moin-tabs').parent());
        if (form.data('initialForm') === form.serialize()) {
            // current values are identicaly to initial ones, remove all change indicators (if any)
            $('.moin-change-indicator', title).remove();
        } else {
            // the values differ
            if (!$('.moin-change-indicator', title).length) {
                // only add a change indicator if there none
                title.append($('<span class="moin-change-indicator">*</span>'));
            }
        }
    }
    // attach above function to all forms as a change handler
    $('#moin-usersettings form').change(changeHandler);

    // executed when user clicks submit button on a user settings form
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
        $('.moin-tab-titles a.moin-current-tab .moin-change-indicator',
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
            location.reload(true);
        }, 'json');
        return false;
    }
    // attach above function as a submit handler to each user setting form
    $('#moin-usersettings form').submit(submitHandler);

    // warn user if he tries to leave page when there are unsaved changes (Opera 12.10 does not support onbeforeunload)
    window.onbeforeunload = function () {
        var discardMessage = _("Your changes will be discarded if you leave this page without saving.");
        if ($('.moin-change-indicator').length > 0) {
            return discardMessage;
        }
    };
};  // end of User Settings page enhancements


// This anonymous function supports doubleclick to edit, auto-scroll the edit textarea and page after edit
MoinMoin.prototype.enhanceEdit = function () {
    // NOTE: if browser does not support sessionStorage, then auto-scroll is not available
    //       (sessionStorage is supported by FF3.5+, Chrome4+, Safari4+, Opera10.5+, and IE8+).
    //       IE8 does not scroll page after edit (cannot determine caret position within textarea).
    "use strict";

    var TOPID = 'moin-content',
        LINENOATTR = "data-lineno",
        MESSAGEMISSED = _("You missed! Double-click on text or to the right of text to auto-scroll text editor."),
        MESSAGEOBSOLETE = _("Your browser is obsolete. Upgrade to gain auto-scroll text editor feature."),
        MESSAGEOLD = _("Your browser is old. Upgrade to gain auto-scroll page after edit feature."),
        OPERA = 'Opera', // special handling required because textareas have \r\n line endings
        modifyButton,
        modifyForm,
        lineno,
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
        this.moinFlashMessage(this.MOINFLASHWARNING, MESSAGEOLD);
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
            } else {
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
        elem.scrollIntoView();
        window.scrollTo(window.pageXOffset, window.pageYOffset - 100);
        // highlight background of selected element for a second or so
        saveColor = elem.style.backgroundColor;
        elem.style.backgroundColor = 'yellow';
        setTimeout(function () { elem.style.backgroundColor = saveColor; }, 1500);
    }

    // called after user doubleclicks, return a line number close to doubleclick point
    function findLineNo(elem) {
        var dataLineno;
        // first try easy way via jquery checking event node and all parent nodes
        dataLineno = $(elem).closest("[" + LINENOATTR + "]");
        if (dataLineno.length) { return $(dataLineno).attr(LINENOATTR); }
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
            // IE9 - user has clicked ouside of textarea causing loss of textarea focus and caret position
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
                    if (lineno > 0 || $("*[data-lineno]").length > 0) {
                        // do only if there were data-lineno attrs - do not give "you missed" message to html or image items
                        sessionStorage.moinDoubleLineNo = lineno;
                    }

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
                this.moinFlashMessage(this.MOINFLASHINFO, MESSAGEMISSED);
                lineno = 1;
            }
            scrollTextarea(lineno - 1);
            // is option to scroll page after edit set?
            if (document.getElementById('moin-scroll-page-after-edit')) {
                // add click handler to OK (save) button to capture position of caret in textarea
                $("#moin-save-text-button").click(function () {
                    caretLineno = getCaretLineno(document.getElementById('f_content_form_data_text'));
                    // save lineno for use in "show" page load
                    if (caretLineno > 0) { sessionStorage.moinCaretLineNo = caretLineno; }
                });
            }
        }
    } else {
        // provide reduced functionality for obsolete browsers that do not support local storage: IE6, IE7, etc.
        if (document.getElementById('moin-edit-on-doubleclick')) {
            modifyButton = $('.moin-modify-button')[0];
            if (modifyButton) {
                // this is a "show" page, add doubleclick event handler to content node
                $('#moin-content').dblclick(function () {
                    document.location = modifyButton.href;
                });
            }
        } else {
            modifyForm = $('#moin-modify')[0];
            if (modifyForm) {
                // user is editing with obsolete browser, give warning about missing features
                this.moinFlashMessage(this.MOINFLASHWARNING, MESSAGEOBSOLETE);
            }
        }
    }
};

$(document).ready(function () {
    "use strict";
    var moin = new MoinMoin();

    moin.selected_link();
    moin.initTransclusionOverlays();
    if(document.getElementById('moin-navibar')!=null) {
        moin.QuicklinksExpander();
    }

    $('.moin-insertname-action').click(function () {
        var fullname = $(this).data('name');
        moin.InsertName(fullname);
    });

    $('.expander').click(function () {
        moin.toggleSubtree(this);
    });

    $('.moin-useractions').click(function () {
        $('#user-actions').toggleClass('hidden');
        return false;
    });

    $('.moin-viewoptions').click(function () {
        $('#view-options').toggleClass('hidden');
        return false;
    });

    $('.moin-itemactions').click(function () {
        $('#item-actions').toggleClass('hidden');
        return false;
    });

    moin.enhanceUserSettings();
    moin.enhanceEdit();
    $('.moin-sortable').tablesorter();

    $('#moin-modify').on('change keyup keydown', 'input, textarea, select', function (e) {
        $('#moin-modify').addClass('moin-changed-input');
    });

    $('#moin-save-text-button').on('click', function() {
        $('#moin-modify').removeClass('moin-changed-input');
    });

    $(window).on('beforeunload', function() {
        if ($('.moin-changed-input').length) {
            return "Data you may have entered will be discarded!";
        }
    });

    // placing initToggleComments after enhanceEdit prevents odd autoscroll issue when editing hidden comments
    moin.initToggleComments();
});
