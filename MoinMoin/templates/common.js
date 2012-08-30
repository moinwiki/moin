//
// MoinMoin2 commonly used JavaScript functions
//
/*jslint browser: true, */
/*global $:false */


// Enter edit mode when user doubleclicks within the content area.  Executed once on page load.
function editOnDoubleClick() {
    "use strict";
    var modifyButton;
    // is edit on doubleclick available for this user and item?
    if (document.getElementById('moin-edit-on-doubleclick')) {
        modifyButton = $('.moin-modify-button')[0];
        if (modifyButton) {
            // add a doubleclick action to the moin content
            $('#moin-content').dblclick(function () {
                document.location = modifyButton.href;
            });
        }
    }
}
$(document).ready(editOnDoubleClick);

// Highlight currently selected link in side panel. Executed on page load
function selected_link() {
    "use strict";
    var selected = window.location.pathname,
        list = document.getElementsByClassName('panel'),
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
