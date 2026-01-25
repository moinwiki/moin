//
// MoinMoin2 commonly used JavaScript functions
//
/*jslint browser: true, nomen: true, todo: true*/
/*global $:true, _:true*/

function MoinMoin() {
    "use strict";
}

// Utility function to add a message to moin flash area. Message can be removed by clicking on it.
MoinMoin.prototype.MOINFLASHINFO = "moin-flash moin-flash-info";
MoinMoin.prototype.MOINFLASHWARNING = "moin-flash moin-flash-warning";
MoinMoin.prototype.moinFlashMessage = function (classes, message) {
    "use strict";
    var pTag = '<P class="' + classes + '">' + message + '</p>';
    $(pTag).appendTo($('#moin-flash'));
    $('.moin-flash').click(function () {
        this.remove();
    });
};

// if /template/dictionary.js has not been loaded, untranslated strings will be returned by _(...)
function _(text) {
    "use strict";
    return $.i18n._(text);
}

// return true if browser localStorage is available
function localStorageAvailable() {
    "use strict";
    try {
        var x = '__storage_test__';
        localStorage.setItem(x, x);
        localStorage.removeItem(x);
        return true;
    }
    catch(e) {
        return false;
    }
}

// executed on page ready, if this is a modify view add action to Cancel button
function cancelEdit() {
    "use strict";
    $('.moin-cancel').click(function () {
        // do not ask to leave page; any edits will be lost, but browser back button may restore edits
        $('#moin-modify').removeClass('moin-changed-input');
        window.location = $('#moin-wiki-root').val() + '/' + $('#moin-item-name').val();
    });
}

// Initial user settings
MoinMoin.prototype.userSettings = {
    'user-actions-collapsed': true,
    'view-options-collapsed': true,
    'item-actions-collapsed': true
};

MoinMoin.prototype.loadUserSettings = function () {
    if (localStorageAvailable()) {
        let jsonData = localStorage.getItem("moin-user-settings");
        if (jsonData) {
            this.userSettings = JSON.parse(jsonData);
        }
    }
}

MoinMoin.prototype.saveUserSettings = function () {
    if (localStorageAvailable()) {
        localStorage.setItem("moin-user-settings", JSON.stringify(this.userSettings));
    }
}

MoinMoin.prototype.applyUserSettings = function () {

    if (this.userSettings['user-actions-collapsed']) {
        $('#moin-user-actions').addClass('hidden');
        $('.moin-useractions > i').removeClass('fa-rotate-90');
    } else {
        $('#moin-user-actions').removeClass('hidden');
        $('.moin-useractions > i').addClass('fa-rotate-90');
    }

    if (this.userSettings['view-options-collapsed']) {
        $('#moin-view-options').addClass('hidden');
        $('.moin-viewoptions > i').removeClass('fa-rotate-90');
    } else {
        $('#moin-view-options').removeClass('hidden');
        $('.moin-viewoptions > i').addClass('fa-rotate-90');
    }

    if (this.userSettings['item-actions-collapsed']) {
        $('#moin-item-actions').addClass('hidden');
        $('.moin-itemactions > i').removeClass('fa-rotate-90');
    } else {
        $('#moin-item-actions').removeClass('hidden');
        $('.moin-itemactions > i').addClass('fa-rotate-90');
    }

    if (this.userSettings["textarea-use-fixed-width-font"]) {
        $(".moin-edit-content").addClass("moin-fixed-width");
    } else {
        $(".moin-edit-content").removeClass("moin-fixed-width");
    }
}

// Highlight currently selected link in side panel. Executed on page load
MoinMoin.prototype.selected_link = function () {
    "use strict";
    var selected = window.location.pathname,
        list = $('.panel'),
        i,
        j,
        cls,
        nav_links,
        link;
    for (j = 0; j < list.length; j += 1) {
        nav_links = list[j].getElementsByTagName('a');

        for (i = 0; i < nav_links.length; i += 1) {
            link = nav_links[i].attributes.href.value;
            if (link === selected) {
                if (nav_links[i].attributes.class) {
                    cls = nav_links[i].attributes.class.value + ' ' + 'current-link';
                } else {
                    cls = 'current-link';
                }
                nav_links[i].setAttribute('class', cls);
                break;
            }
        }
    }
};


// toggleComments is executed when user clicks a Comments button and conditionally on dom ready.
MoinMoin.prototype.toggleComments = function () {
    "use strict";
    // Toggle visibility of every tag with class "comment"
    var pageComments = $('.comment'),
        tooltips = $('.moin-toggle-comments-tooltip');
    if (pageComments.is(':hidden')) {
        pageComments.show();
        tooltips.attr('title', _("Hide comments"));
    } else {
        pageComments.hide();
        tooltips.attr('title', _("Show comments"));
    }
    return false;  // do not scroll to top of page
};

// Comments initialization is executed once after document ready.
MoinMoin.prototype.initToggleComments = function () {
    "use strict";
    var pageComments = $('.comment');
    if (pageComments.length > 0) {
        // comments are visible; per user option, hide comments if there is not a <br id="moin-show-comments" />
        if (!document.getElementById('moin-show-comments')) {
            this.toggleComments();
        }
    } else {
        // There are no comments, so hide Comments button
        $('.moin-toggle-comments-button').css('display', 'none');
    }
    $('.moin-toggle-comments-button').click(this.toggleComments);
};


// toggleTransclusionOverlays is executed when user clicks a Transclusions button on the Show item page.
MoinMoin.prototype.toggleTransclusionOverlays = function () {
    "use strict";
    var overlays = $('.moin-item-overlay-ul, .moin-item-overlay-lr'),
        tooltips;
    if (overlays.length > 0) {
        tooltips = $('.moin-transclusions-tooltip');
        if (overlays.is(':visible')) {
            overlays.hide();
            tooltips.attr('title', _("Show transclusions"));
        } else {
            overlays.show();
            tooltips.attr('title', _("Hide transclusions"));
        }
    }
    return false;  // do not scroll to top of page
};

// Transclusion initialization is executed once after document ready.
MoinMoin.prototype.initTransclusionOverlays = function () {
    "use strict";
    var elem, overlayUL, overlayLR, wrapper, wrappers, transclusions, classes,
        rightArrow = '\u2198',
        leftArrow = '\u2196',
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
            overlayLR = $(overlayUL).clone(true);
            $(overlayUL).append(rightArrow);
            $(overlayLR).append(leftArrow);
            $(overlayLR).attr('class', 'moin-item-overlay-lr');
            // if the parent of this element is an A, then wrap parent (avoid A's within A's)
            if ($(elem).parent()[0].tagName === 'A') {
                elem = $(elem).parent()[0];
            }
            // copy user specified classes from img/object tag to wrapper
            if ($.inArray(elem.tagName, mediaTags) > -1) {
                // do not copy classes starting with moin-
                classes = $(elem).attr('class');
                classes = classes.split(" ").filter(function (c) {
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
            // copy float styling to the wrapper so a SPAN enclosing an IMG does the floating (float will be 'none' if not specified)
            if ($(elem).filter(":first").css('float') !== 'none') {
                $(wrapper).css('float', $(elem).filter(":first").css('float'));
            }
            // insert wrapper after elem, append (move) elem, append overlays
            $(elem).after(wrapper);
            $(wrapper).append(elem);
            $(wrapper).append(overlayUL);
            $(wrapper).append(overlayLR);
        }
    });
    // docbook inline transclusions require classes to be copied up 2 levels
    transclusions = $($('.db-inlinemediaobject').get().reverse());
    transclusions.each(function (index) {
        elem = transclusions[index];
        classes = $($(elem).children('span').children('.moin-item-wrapper')[0]).attr('class');
        classes = classes.split(" ").filter(function (c) {
            return c.lastIndexOf('moin-', 0) !== 0;
        });
        $(elem).addClass(classes.join(' '));
    });
    // most themes will have a transclusions link within item views
    wrappers = $('.moin-item-wrapper');
    if (wrappers.length === 0) {
        // if there are no transclusions, make the Transclusions buttons invisible
        $('.moin-transclusions-button').css('display', 'none');
    }
    $('.moin-transclusions-button').click(this.toggleTransclusionOverlays);
};


// Executed on page load.  If logged in user has less than 6 quicklinks,  do nothing.
// Else, show the first five links, hide the others, and append a >>> button to show hidden quicklinks on mouseover.
MoinMoin.prototype.QuicklinksExpander = function () {
    "use strict";
    var QUICKLINKS_EXPAND = ">>>",
        QUICKLINKS_COLLAPSE = "<<<",
        QUICKLINKS_MAX = $('#moin-navibar').data('expanded_quicklinks_size'),
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


MoinMoin.prototype.displayFlashMessages = function (messages) {
    for (i = 0; i < messages.length; i += 1) {
        f = $(document.createElement('p'));
        f.html(messages[i][0]);
        f.addClass('moin-flash');
        f.addClass('moin-flash-javascript');
        f.addClass('moin-flash-' + messages[i][1]);
        $(f).click(function () {
            this.remove();
        });
        $('#moin-flash').append(f);
    }
}

// remove all flash messages previously added via javascript
MoinMoin.prototype.clearFlashMessages = function () {
    $('#moin-flash .moin-flash-javascript').remove();
}

MoinMoin.prototype.saveFlashMessages = function (messages) {
    localStorage.setItem("moin-flash-messages", JSON.stringify(messages))
}

MoinMoin.prototype.restoreFlashMessages = function () {
    messages = JSON.parse(localStorage.getItem("moin-flash-messages") || "[]")
    localStorage.removeItem("moin-flash-messages")
    this.clearFlashMessages()
    this.displayFlashMessages(messages)
}

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
            $('#moin-flash .moin-flash-javascript').remove();
            tab = this.hash;
            window.location.hash = tab;
            $('.moin-current-tab').removeClass('moin-current-tab');
            $(ev.target).addClass('moin-current-tab');
            tabs.children('.moin-tab-body').hide().removeClass('moin-current-form');
            tabs.children(tab).show().addClass('moin-current-form');
            return false;
        });
    });
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

        MoinMoin.prototype.clearFlashMessages();

        // send the form to the server
        $.post(form.attr('action'), form.serialize(), function (data) {
            clearInterval(buttonDotAnimation);
            // if the response indicates a redirect, set the new location
            if (data.redirect) {
                MoinMoin.prototype.saveFlashMessages(data.flash)
                location.href = data.redirect;
                return;
            }
            // get the new form element from the response
            const newform = $(data.form);
            // set event handlers on the new form
            newform.submit(submitHandler);
            newform.change(changeHandler);
            // store the forms initial data
            newform.data('initialForm', newform.serialize());
            // replace the old form with the new one
            form.replaceWith(newform);
            // check if form processing gave back an error; don't reload the page
            // in case an error is present as this would cause validation error
            // messages present in 'newform' to get lost.
            const has_error = 'flash' in data && data.flash[0][1] === 'error';
            if ((ev.currentTarget.id === 'usersettings_ui' || ev.currentTarget.id === 'usersettings_personal') &&
                !has_error
            ) {
                MoinMoin.prototype.saveFlashMessages(data.flash)
                // theme or language may have changed, show user the new theme/language
                location.reload(true);
                return;
            }
            // show any flash messages received with the server response
            MoinMoin.prototype.displayFlashMessages(data.flash)
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
    "use strict";

    var TOPID = 'moin-content',
        LINENOATTR = "data-lineno",
        MESSAGEMISSED = _("You missed! Double-click on text or to the right of text to auto-scroll text editor."),
        MESSAGEOBSOLETE = _("Your browser is obsolete. Upgrade to gain auto-scroll text editor feature."),
        OPERA = 'Opera', // special handling required because textareas have \r\n line endings
        modifyButton,
        modifyForm,
        lineno,
        caretLineno;

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
            // position the caret, works for all browsers if textarea rows option is > 0 in user settings
            // if textarea rows == 0 user must press right arrow key to scroll window to caret position
            textArea.focus();
            if (scrollAmount > 0) { textArea.scrollTop = scrollAmount; }
            // html5 compliant browsers, highlight the position of the caret for a second or so
            textArea.setSelectionRange(scrolledText.length, scrolledText.length + 8);
            setTimeout(function () {textArea.setSelectionRange(scrolledText.length, scrolledText.length + 4); }, 2000);
            setTimeout(function () {textArea.setSelectionRange(scrolledText.length, scrolledText.length); }, 3000);
        }
    }

    // called after a "show" page loads after Save, scroll page to textarea caret position
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
            // this is a "show" or "preview" page and the edit on doubleclick option is set for this user
            modifyButton = $('.moin-modify-button')[0];
            if (modifyButton) {
                // add doubleclick event handler when user doubleclicks the rendered content area or draft
                $('#moin-content').dblclick(function (e) {
                    lineno = findLineNo(e.target);
                    if (lineno > 0 || $("*[data-lineno]").length > 0) {
                        // do only if there were data-lineno attrs - do not give "you missed" message to html or image items
                        sessionStorage.moinDoubleLineNo = lineno;
                    }
                    if ($('.moin-watermark').length) {
                        // this is a preview page and user has double-clicked on rendered draft, scroll textarea
                        scrollTextarea(lineno);
                        return false;
                    } else {
                        // call server for preview
                        document.location = modifyButton.href;
                    }
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


// diffScroll is executed on page load.
// Adds an onclick function to the line # links in a diff view.
// Multiple consecutive blank lines in Markdown source make diff and DOM line numbers out of sync,
// so window may be scrolled to wrong line.
MoinMoin.prototype.diffScroll = function () {
    "use strict";
    var difflinks = $(".moin-diff-line-number");
    // the above class is used only on TR tags within a diff view,  if this is not a diff page, do nothing
    if (difflinks.length === 0) { return; }
    difflinks.each(function (index) {
        // loop through TR tags, change all left-side hrefs to value on right side because only right side revision is displayed
        var tr = difflinks[index],
            href = $(tr).find("td:last-child").children("a").attr("href");
        $(tr).find("td:first-child").children("a").attr("href", href);
        // add onclick function to both line number anchors under TR > TDs
        $(tr).children().find("a").click(function () {
            var url = window.location.href.split("#")[0],
                start = parseInt(href.slice(1)),
                next,
                j,
                target;
            // find the element that has the current data-lineno attribute or next higher
            for (j = 0; j < 99; j += 1) {
                next = j + start;
                target = $('[data-lineno="' + next + '"]');
                if (target.length === 1) { break; }
            }
            next = parseInt(next);
            // remove any prior duplicate ID or class addition
            $("#" + next).remove();
            $(".moin-diff-highlight").removeClass("moin-diff-highlight");
            // if target has been found, highlight element and scroll to it
            $(target).addClass("moin-diff-highlight");
            $(target).prepend($('<span id="' + next + '"></span>'));
            window.location.href = url + "#" + next;
            return false;
        });
    });
};


// show all options on form so user can choose output type with one click
function showAllOptions() {
    "use strict";
    //  itemviews convert
    var numberOptions = $('#f_new_type > option').length;
    if (numberOptions) {
        $('#f_new_type')[0].setAttribute('size', numberOptions);
    }
    // usersettings theme name
    numberOptions = $('#f_usersettings_ui_theme_name > option').length;
    if (numberOptions) {
        $('#f_usersettings_ui_theme_name')[0].setAttribute('size', numberOptions);
    }
}


// admin/item_acl_report.html processing - disable all Save buttons, then selectively enable after item ACL selected or changed
function aclSaveButtons() {
    "use strict";
    $(".moin-acl-name-cell .moin-button").attr("disabled", true);
    $("textarea.moin-acl-string").one("click keydown", function (e) {
        $(e.target).parent().parent().find(".moin-button").attr("disabled", false);
    });
}


$(document).ready(function () {
    "use strict";
    var moin = new MoinMoin();

    moin.loadUserSettings()
    moin.applyUserSettings();

    moin.diffScroll();
    moin.selected_link();
    moin.initTransclusionOverlays();
    if (document.getElementById('moin-navibar') !== null) {
        moin.QuicklinksExpander();
    }

    // redirect when page contains an A tag with "redirect" class, see JSRedirect macro
    if ($('a.redirect').length) {
        window.location = $('a.redirect').prop('href');
    }

    // remove a server-side flash message by clicking on it
    $('.moin-flash').click(function () {
        this.remove();
    });

    // toggle item_acl_report show all items or show items with modified acls
    $('.moin-show-hide-acls').click(function (event) {
        event.preventDefault();
        $('.moin-show-hide-acls').toggleClass('hidden');
        $('form.moin-acl-default').toggleClass('hidden');
    });

    // XXX dead code?
    $('.expander').click(function () {
        moin.toggleSubtree(this);
    });

    $('.moin-useractions').click(function (event) {
        event.preventDefault();
        $('#moin-user-actions').toggleClass('hidden');
        $('.moin-useractions > i').toggleClass('fa-rotate-90');
        moin.userSettings['user-actions-collapsed'] = $('#moin-user-actions').hasClass('hidden');
        moin.saveUserSettings();
    });

    $('.moin-viewoptions').click(function (event) {
        event.preventDefault();
        $('#moin-view-options').toggleClass('hidden');
        $('.moin-viewoptions > i').toggleClass('fa-rotate-90');
        moin.userSettings['view-options-collapsed'] = $('#moin-view-options').hasClass('hidden');
        moin.saveUserSettings();
    });

    $('.moin-itemactions').click(function (event) {
        event.preventDefault();
        $('#moin-item-actions').toggleClass('hidden');
        $('.moin-itemactions > i').toggleClass('fa-rotate-90');
        moin.userSettings['item-actions-collapsed'] = $('#moin-item-actions').hasClass('hidden');
        moin.saveUserSettings();
    });

    // executed when user clicks button to toggle modify textarea between fixed/variable width fonts
    $('#moin-toggle-fixed-font-button').on('click', function (event) {
        event.preventDefault();
        $(".moin-edit-content").toggleClass("moin-fixed-width");
        moin.userSettings['textarea-use-fixed-width-font'] = $(".moin-edit-content").hasClass("moin-fixed-width");
        moin.saveUserSettings();
    });

    moin.enhanceUserSettings();
    moin.enhanceEdit();

    $('.moin-sortable').tablesorter();

    $('#moin-modify').on('change keyup keydown', 'input, textarea, select', function (e) {
        $('#moin-modify').addClass('moin-changed-input');
    });

    $('#moin-save-text-button').on('click', function () {
        $('#moin-modify').removeClass('moin-changed-input');
        location.hash = '';
    });

    // CKEditor
    const editor_elem = document.querySelector(".ckeditor");
    if (editor_elem) {
        createEditor(editor_elem)
    }

    // add function to be executed when user clicks Load Draft button on +modify page
    $('.moin-load-draft').on('click', function () {
        const draft_data = $('#moin-draft-data').val()
        try {
            window.ckeditor.setData(draft_data);
        }
        catch {
            $('.moin-edit-content').val(draft_data);
        }
        $('#moin-modify').addClass('moin-changed-input');
        $('.moin-load-draft').hide();
        $('#moin-flash .moin-flash').remove();
        MoinMoin.prototype.moinFlashMessage(MoinMoin.prototype.MOINFLASHINFO, _("Your saved draft has been loaded."));
    });

    // if this is preview: scroll to diff and mark textarea changed
    if ($('#moin-preview-diff').length && $('#moin-modify').length) {
        window.location = window.location.href.split('#')[0] + '#moin-preview-diff';
        $('#moin-modify').addClass('moin-changed-input');
    }

    // warn user about unsaved changes; if user leaves page with unsaved edits, edit lock remains until timeout
    window.onbeforeunload = function () {
        if ($('.moin-changed-input').length) {
            return _("All changes will be discarded!");
        }
    }

    // give user 1 minute warning before edit lock expires
    if ($("#moin-lock_duration").length) {
        setTimeout(function() {
            alert(_("Your edit lock will expire in 1 minute: ") + $('#moin-item-name').val())}, (($("#moin-lock_duration").val() - 60) * 1000));
    }

    // convert FontAwesome data-style color & font-size attributes to css attr,
    // cannot do style in macros/FontAwesome.py because CSP flags inline style attributes
    var styl;
    var elements = $('[data-style]');
    elements.each(function() {
        styl = $(this).data('style').split(",");
        if (styl.length > 0) {
            $(this).css('color', styl[0]);
        }
        if (styl.length > 1) {
            $(this).css('font-size', styl[1] + "em");
        }
    });

    $('textarea.moin-autosize').each(function(){autosize(this)});

    showAllOptions();

    aclSaveButtons();

    cancelEdit();

    // placing initToggleComments after enhanceEdit prevents odd autoscroll issue when editing hidden comments
    moin.initToggleComments();
    $('.moin-table-of-contents .moin-showhide').on('click', function (event) {
        event.preventDefault();
        var parent = $(this).parent();
        if ($(parent).is('.moin-table-of-contents-heading')) {
            parent = $(parent).parent();
        }
        $(parent).find('ol:first-of-type').toggle();
    });

    moin.restoreFlashMessages();
});
