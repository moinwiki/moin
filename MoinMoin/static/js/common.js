//
// MoinMoin commonly used JavaScript functions
//

var QUICKLINKS_EXPAND = ">>>";
var QUICKLINKS_COLLAPSE = "<<<";

// use this instead of assigning to window.onload directly:
function addLoadEvent(func) {
    // alert("addLoadEvent " + func)
    var oldonload = window.onload;
    if (typeof window.onload != 'function') {
        window.onload = func;
    } else {
        window.onload = function() {
            oldonload();
            func();
        }
    }
}

// copy from fckeditor browser check code (fckeditor.js:298, function : FCKeditor_IsCompatibleBrowser)
function can_use_gui_editor() {
    var sAgent = navigator.userAgent.toLowerCase() ;

    // Internet Explorer 5.5+
    if ( /*@cc_on!@*/false && sAgent.indexOf("mac") == -1 )
    {
        var sBrowserVersion = navigator.appVersion.match(/MSIE (.\..)/)[1] ;
        return ( sBrowserVersion >= 5.5 ) ;
    }

    // Gecko (Opera 9 tries to behave like Gecko at this point).
    if ( navigator.product == "Gecko" && navigator.productSub >= 20030210 && !( typeof(opera) == 'object' && opera.postError ) )
        return true ;

    // Opera 9.50+
    if ( window.opera && window.opera.version && parseFloat( window.opera.version() ) >= 9.5 )
        return true ;

/*
  // disable safari : until fck devteam fix http://dev.fckeditor.net/ticket/2333

    // Adobe AIR
    // Checked before Safari because AIR have the WebKit rich text editor
    // features from Safari 3.0.4, but the version reported is 420.
    if ( sAgent.indexOf( ' adobeair/' ) != -1 )
        return ( sAgent.match( / adobeair\/(\d+)/ )[1] >= 1 ) ; // Build must be at least v1

    // Safari 3+
    if ( sAgent.indexOf( ' applewebkit/' ) != -1 )
        return ( sAgent.match( / applewebkit\/(\d+)/ )[1] >= 522 ) ;    // Build must be at least 522 (v3)
*/
    return false ;

}


function update_edit_links() {
    // Update editlink according if if the browser is compatible
    if (can_use_gui_editor() == false){
        //alert("update_edit_links: can't use gui editor");
        return;
    }
    var editlinks = document.getElementsByName("editlink");
    for (i = 0; i < editlinks.length; i++) {
        var link = editlinks[i];
        href = link.href.replace('editor=textonly','editor=guipossible');
        link.href = href;
        //alert("update_edit_links: modified to guipossible");
    }
}


function add_gui_editor_links() {
    // Add gui editor link after the text editor link

    // If the variable is not set or browser is not compatible, exit
    try {gui_editor_link_href}
    catch (e) {
        //alert("add_gui_editor_links: gui_editor_link_href not here");
        return
    }
    if (can_use_gui_editor() == false){
        //alert("add_gui_editor_links: can't use gui_editor");
        return;
    }
    var all = document.getElementsByName('texteditlink');
    for (i = 0; i < all.length; i++) {
        var textEditorLink = all[i];
        // Create a list item with a link
        var guiEditorLink = document.createElement('a');
        guiEditorLink.href = gui_editor_link_href;
        var text = document.createTextNode(gui_editor_link_text);
        guiEditorLink.appendChild(text);
        var listItem = document.createElement('li')
        listItem.appendChild(guiEditorLink);
        // Insert in the itemviews
        var itemviews = textEditorLink.parentNode.parentNode
        var nextListItem = textEditorLink.parentNode.nextSibling;
        itemviews.insertBefore(listItem, nextListItem);
        //alert("add_gui_editor_links: added gui editor link");
    }
}


function show_switch2gui() {
    // Show switch to gui editor link if the browser is compatible
    if (can_use_gui_editor() == false) return;

    var switch2gui = document.getElementById('switch2gui')
    if (switch2gui) {
        switch2gui.style.display = 'inline';
    }
}

function load() {
    // Do not name this "onload", it does not work with IE :-)
    // TODO: create separate onload for each type of view and set the
    // correct function name in the html.
    // e.g <body onlod='editor_onload()'>

    // Page view stuff
    update_edit_links();
    add_gui_editor_links();

    // Editor stuff
    show_switch2gui();

    // data browser widget
    dbw_hide_buttons();
}


function before_unload(evt) {
    // TODO: Better to set this in the editor html, as it does not make
    // sense elsehwere.
    // confirmleaving is available when editing
    try {return confirmleaving();}
    catch (e) {}
}

// Initialize after loading the page
addLoadEvent(load)

// Catch before unloading the page
window.onbeforeunload = before_unload

function dbw_update_search(dbw_id)
{
    var table = document.getElementById(dbw_id+'table');
    var cell;
    var shown;
    var i
    var cols = table.rows[0].cells.length;
    var filter = new Array();
    var dofilter = new Array();
    var form = document.forms[dbw_id+'form'];

    for (i = 0; i < cols; i++) {
        dofilter[i] = false;
        if (form[dbw_id+'filter'+i]) {
            dofilter[i] = true;
            filter[i] = form[dbw_id+'filter'+i].value;
            if (filter[i] == '[all]')
                dofilter[i] = false;
            if (filter[i] == '[empty]')
                filter[i] = '';
        }
    }

    for (i = 1; i < table.rows.length; i++) {
        var show = true;
        for (col = 0; col < cols; col++) {
            if (!dofilter[col])
                continue;

            cell = table.rows[i].cells[col];

            if (filter[col] == '[notempty]') {
                if (cell.abbr == '') {
                    show = false;
                    break;
                }
            } else if (filter[col] != cell.abbr) {
                show = false;
                break;
            }
        }
        if (show)
            table.rows[i].style.display = '';
        else
            table.rows[i].style.display = 'none';
    }
}

function dbw_hide_buttons() {
    var form;
    var elem;
    var name;

    for (var fidx = 0; fidx < document.forms.length; fidx++) {
        form = document.forms[fidx];
        for (var eidx = 0; eidx < form.elements.length; eidx++) {
            elem = form.elements[eidx];
            name = elem.name;
            if (name) {
                if (name.indexOf('dbw.') >= 0 && name.substr(-7) == '.submit')
                    elem.style.display = 'none';
            }
        }
    }
}

/*  getElementsByClassName
    Developed by Robert Nyman, http://www.robertnyman.com
    Code/licensing: http://code.google.com/p/getelementsbyclassname/ (MIT license)
    Version: 1.0.1
*/
var getElementsByClassName = function (className, tag, elm){
    if (document.getElementsByClassName) {
        getElementsByClassName = function (className, tag, elm) {
            elm = elm || document;
            var elements = elm.getElementsByClassName(className),
                nodeName = (tag)? new RegExp("\\b" + tag + "\\b", "i") : null,
                returnElements = [],
                current;
            for(var i=0, il=elements.length; i<il; i+=1){
                current = elements[i];
                if(!nodeName || nodeName.test(current.nodeName)) {
                    returnElements.push(current);
                }
            }
            return returnElements;
        };
    }
    else if (document.evaluate) {
        getElementsByClassName = function (className, tag, elm) {
            tag = tag || "*";
            elm = elm || document;
            var classes = className.split(" "),
                classesToCheck = "",
                xhtmlNamespace = "http://www.w3.org/1999/xhtml",
                namespaceResolver = (document.documentElement.namespaceURI === xhtmlNamespace)? xhtmlNamespace : null,
                returnElements = [],
                elements,
                node;
            for(var j=0, jl=classes.length; j<jl; j+=1){
                classesToCheck += "[contains(concat(' ', @class, ' '), ' " + classes[j] + " ')]";
            }
            try {
                elements = document.evaluate(".//" + tag + classesToCheck, elm, namespaceResolver, 0, null);
            }
            catch (e) {
                elements = document.evaluate(".//" + tag + classesToCheck, elm, null, 0, null);
            }
            while ((node = elements.iterateNext())) {
                returnElements.push(node);
            }
            return returnElements;
        };
    }
    else {
        getElementsByClassName = function (className, tag, elm) {
            tag = tag || "*";
            elm = elm || document;
            var classes = className.split(" "),
                classesToCheck = [],
                elements = (tag === "*" && elm.all)? elm.all : elm.getElementsByTagName(tag),
                current,
                returnElements = [],
                match;
            for(var k=0, kl=classes.length; k<kl; k+=1){
                classesToCheck.push(new RegExp("(^|\\s)" + classes[k] + "(\\s|$)"));
            }
            for(var l=0, ll=elements.length; l<ll; l+=1){
                current = elements[l];
                match = false;
                for(var m=0, ml=classesToCheck.length; m<ml; m+=1){
                    match = classesToCheck[m].test(current.className);
                    if (!match) {
                        break;
                    }
                }
                if (match) {
                    returnElements.push(current);
                }
            }
            return returnElements;
        };
    }
    return getElementsByClassName(className, tag, elm);
};


// Enter edit mode when user doubleclicks within the page body.  Executed once on page load.
function editOnDoubleClick() {
    var modifyButton;
    // is edit on doubleclick available for this user and item?
    if (document.getElementById('moin-edit-on-doubleclick')) {
        modifyButton = jQuery('.moin-modify-button')[0];
        if (modifyButton) {
            // add a doubleclick action to the body tag
            jQuery('body').dblclick(function () {
                document.location = modifyButton.href;
            });
        }
    }
}
jQuery(document).ready(editOnDoubleClick);


// ===========================================================================
// The following functions are part of jQuery code

$(function() {
    // Only submit actions menu form if option of select is not first
    $('.moin-actionsmenu-select').change(function() {
        if ((this.selectedIndex != 0) && (this.options[this.selectedIndex].disabled == false)) {
            $(this).parents('form').submit();
        }
        this.selectedIndex = 0;
    });

});

// Insert Zero-Width-Space characters into long text strings of textNode elements.
// Firefox does not support CSS with {word-wrap: break-word;} within tables.
// As a result, Firefox may display tables with long urls or page names as very wide tables.
// This function alters tables by inserting a zero-width-space into long text strings after every 5 characters.
// The moin-wordbreak class is intended for use on TD elements, but may be used on TABLE, TR, THEAD, TBODY, or TFOOT.
function moinFirefoxWordBreak() {
    // TODO:  Test for browser version when/if a future Firefox supports break-word within tables.
    if (!jQuery.browser.mozilla) {
        return;
    }
    var child;
    var words;
    var parents;
    var i, j;
    // Only textNodes are of interest, but there is no way to select them directly.
    // Select all elements with the moin-wordbreak class and add all selectable descendants of those elements.
    // Then search for children that are textNodes; TDs or THs and elements descended from them are likely parents of textNodes.
    parents = jQuery(".moin-wordbreak").add(".moin-wordbreak *");
    for (i = 0; i < parents.length; i++) {
        child = parents[i].firstChild;
        while(child) {
            if (child.nodeType === 3) {
                words = child.textContent.split(" ");
                for (j = 0; j < words.length; j++) {
                    // \u200B denotes a zero-width-space character (for easy testing, replace with a visible character like Q)
                    words[j] = words[j].replace(/(.{5})/g,"$1\u200B");
                }
                child.textContent = words.join(" ");
            }
            child = child.nextSibling;
        }
    }
}
jQuery(moinFirefoxWordBreak);

// globals used to save translated show/hide titles (tooltips) for Comments buttons
var pageComments = null;
var commentsShowTitle = ''; // "Show comments"
var commentsHideTitle = ''; // "Hide comments"

// This is executed when user clicks a Comments button and conditionally on dom ready
function toggleComments() {
    // Toggle visibility of every tag with class "comment"
    var buttons = jQuery('.moin-toggle-comments-button > a');
    if (pageComments.is(':hidden')) {
        pageComments.show();
        buttons.attr('title', commentsHideTitle);
    } else {
        pageComments.hide();
        buttons.attr('title', commentsShowTitle);
    }
}

// Comments initialization is executed once after document ready
function initToggleComments() {
    var titles;
    var show_comments = '0';
    pageComments = jQuery('.comment');
    if (pageComments.length > 0) {
        // There are comments, so show itemview Comments button
        jQuery('.moin-toggle-comments-button').css('display', '');
        // read translated show|hide Comments button title, split into show and hide parts, and save
        titles = jQuery('.moin-toggle-comments-button > a').attr('title').split('|');
        if (titles.length === 2) {
            commentsShowTitle = titles[0];
            commentsHideTitle = titles[1];
            jQuery('.moin-toggle-comments-button > a').attr('title', commentsHideTitle);
        }
        // comments are visible; per user option, hide comments if there is not a <br id="moin-show-comments" />
        if (!document.getElementById('moin-show-comments')) {
            toggleComments();
        }
    }
}
jQuery(document).ready(initToggleComments);

// globals used to save translated show/hide titles (tooltips) for Transclusions buttons
var transclusionShowTitle = ''; // "Show Transclusions"
var transclusionHideTitle = ''; // "Hide Transclusions"

// This is executed when user clicks a Transclusions button
function toggleTransclusionOverlays() {
    var overlays = jQuery('.moin-item-overlay-ul, .moin-item-overlay-lr');
    if (overlays.length > 0) {
        var buttons = jQuery('.moin-transclusions-button > a');
        if (overlays.is(':visible')) {
            overlays.hide();
            buttons.attr('title', transclusionShowTitle);
        } else {
            overlays.show();
            buttons.attr('title', transclusionHideTitle);
}
            }
}

// Transclusion initialization is executed once after document ready
function initTransclusionOverlays() {
    var elem, overlayUL, overlayLR, wrapper, wrappers;
    var rightArrow = '\u2192';
    // get list of elements to be wrapped;  must work in reverse order in case there are nested transclusions
    var transclusions = jQuery(jQuery('.moin-transclusion').get().reverse());
    transclusions.each(function (index) {
        elem = transclusions[index];
        // if this is the transcluded item page, do not wrap (avoid creating useless overlay links to same page)
        if (location.href !== elem.getAttribute('data-href')) {
            if (elem.tagName === 'DIV') {
                wrapper = jQuery('<div class="moin-item-wrapper"></div>');
            } else {
                wrapper = jQuery('<span class="moin-item-wrapper"></span>');
            }
            overlayUL = jQuery('<a class="moin-item-overlay-ul"></a>');
            jQuery(overlayUL).attr('href', elem.getAttribute('data-href'));
            jQuery(overlayUL).append(rightArrow);
            overlayLR = jQuery(overlayUL).clone(true);
            jQuery(overlayLR).attr('class', 'moin-item-overlay-lr');
            // if the parent of this element is an A, then wrap parent (avoid A's within A's)
            if (jQuery(elem).parent()[0].tagName === 'A') {
                elem = jQuery(elem).parent()[0];
            }
            // wrap element, add UL and LR overlay siblings, and replace old elem with wrapped elem
            jQuery(wrapper).append(jQuery(elem).clone(true));
            jQuery(wrapper).append(overlayUL);
            jQuery(wrapper).append(overlayLR);
            jQuery(elem).replaceWith(wrapper);
        }
    });
    // if an element was wrapped above, then make the Transclusions buttons visible
    wrappers = jQuery('.moin-item-wrapper');
    if (wrappers.length > 0) {
        jQuery('.moin-transclusions-button').css('display', '');
        // read translated show|hide Transclusions button title, split into show and hide parts, and save
        var titles = jQuery('.moin-transclusions-button > a').attr('title').split('|');
        if (titles.length === 2) {
            transclusionShowTitle = titles[0];
            transclusionHideTitle = titles[1];
            jQuery('.moin-transclusions-button > a').attr('title', transclusionShowTitle);
        }
    }
}
jQuery(document).ready(initTransclusionOverlays);

/*
    For the quicklinks patch that
    makes all quicklinks after the 5th visible only by mousing over an icon.
*/
function getLinks() {
    return jQuery(".userlink:not(.moin-navibar-icon)");
}

function createIcon(txt) {
    var li = document.createElement("li");
    li.setAttribute("class", "moin-userlink moin-navibar-icon");

    var txt = document.createTextNode(txt);
    li.appendChild(txt);

    return li
}

function appendIcon(txt) {
    var elem = createIcon(txt);

    document.getElementById("moin-navibar").appendChild(elem);
    return elem
}

function shouldHide(links) {
    return (links.length > 5);
}

function getHideableLinks() {
    return getLinks().slice(5);
}

function hideShowHideableLinks(action) {
    getHideableLinks().each(function(i) {
        if (action == "hide") {
            $(this).hide();
        }
        else  {
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

function QuicklinksExpander() {
    this.getLinks = getLinks;
    this.appendIcon = appendIcon;
    this.shouldHide = shouldHide;
    this.getHideableLinks = getHideableLinks;
    this.hideLinks = hideLinks;
    this.showLinks = showLinks;

    this.navibar = $("#moin-header");
    this.links = this.getLinks();
    this.hideable = this.getHideableLinks();

    // If there's less than 5 items, don't bother doing anything.
    if (this.shouldHide(this.links)) {
        this.expandIcon = $(this.appendIcon(QUICKLINKS_EXPAND));
        this.closeIcon = $(this.appendIcon(QUICKLINKS_COLLAPSE));

        this.closeIcon.hide();

        // Hide everything after the first 5
        this.hideLinks();

        /*
        TODO: when FF4.0 becomes stable/popular, delete the following hack
        and use function.bind(this)
        */
        var newThis = this;

        // When the user mouses over the icon link,
        // Show the hidden links
        this.expandIcon.mouseenter(function(e) {
            newThis.showLinks();
            newThis.expandIcon.hide();
            newThis.closeIcon.show();

        });

        this.closeIcon.mouseenter(function(e) {
            newThis.hideLinks();
            newThis.expandIcon.show();
            newThis.closeIcon.hide();
        });
    }
}

jQuery(document).ready(function() {
    new QuicklinksExpander();
})

function toggleSubtree(item) {
    /* used to toggle subtrees in the subitem widget */
    var subtree = $(item).siblings("ul");
    subtree.toggle(200);
}

function guessContentType() {
    /* Used in the modify_text template to guess the data content type client-side
     * This approach has the advantage of reacting to content type changes for the
     * link/transclude code without having to re-fetch the page */
    var meta_text = $("#f_meta_text").val();
    var ctype_regex = /["']contenttype["']\s*:\s*["']([\w-_+.]+\/[\w-_+.]+)(;|["'])/;
    if (meta_text) {
        var match = ctype_regex.exec(meta_text);
        if (match) return match[1];
    }
    // text/plain is the default value
    return "text/plain";
}

function transcludeSubitem(subitem_name, fullname) {
    function moinwiki(subitem_name, fullname) {
        return "{{" + fullname.replace("{{", "\\}}") + "}} ";
    }
    function mediawiki(subitem_name, fullname) {
        return "{{:" + fullname.replace("}}", "\\}}") + "}} ";
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
        "text/plain" : function(x){return x + " ";},
    }
    var ctype = guessContentType();
    var input_element = $("#f_data_text");
    var ctype_format = transclude_formats[ctype];
    if (!ctype_format) ctype_format = transclude_formats["text/plain"];
    input_element.val(input_element.val() + ctype_format(subitem_name, fullname));
    input_element.focus();
}

function linkSubitem(subitem_name, fullname) {
    function moinwiki(subitem_name, fullname) {
        return "[[" + fullname.replace("]", "\\]") + "|" + subitem_name.replace("]", "\\]") + "]] ";
    }
    function rst(subitem_name, fullname) {
        return "`" + subitem_name.replace(">", "\\>").replace("`", "\\`") + " <" + fullname.replace(">", "\\>") + ">`_ ";
    }
    function docbook(subitem_name, fullname) {
        return '<ulink url="/' + fullname.replace('"', '\\"') + '">' + subitem_name + "</ulink>";;
    }
    var link_formats = {
        "text/x.moin.wiki" : moinwiki,
        "text/x.moin.creole" : moinwiki,
        "text/x-mediawiki" : moinwiki,
        "text/x-rst" : rst,
        "application/docbook+xml" : docbook,
        "text/plain" : function(x){return x + " ";},
    }
    var ctype = guessContentType();
    var input_element = $("#f_data_text");
    var ctype_format = link_formats[ctype];
    if (!ctype_format) ctype_format = link_formats["text/plain"];
    input_element.val(input_element.val() + ctype_format(subitem_name, fullname));
    input_element.focus();
}

function initMoinTabs($) {
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

jQuery(document).ready(initMoinTabs);

function initMoinUsersettings($) {
    "use strict";
    // save initial values of each form
    $('#moin-usersettings form').each(function () {
        $(this).data('initialForm', $(this).serialize());
    });

    // check if any changes were made
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
    $('#moin-usersettings form').change(changeHandler);

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
            $('#moin-header .moin-flash-javascript').remove();
            // add new flash messages from the response
            for (i = 0; i < data.flash.length; i += 1) {
                f = $(document.createElement('p'));
                f.html(data.flash[i][0]);
                f.addClass('moin-flash');
                f.addClass('moin-flash-javascript');
                f.addClass('moin-flash-' + data.flash[i][1]);
                $('#moin-header').append(f);
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
    $('#moin-usersettings form').submit(submitHandler);
}

jQuery(document).ready(initMoinUsersettings);
