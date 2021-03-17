/*
    * Copyright 2010, Sebastian Tschan, https://blueimp.net
-   * Licensed under the MIT license:
-   * http://creativecommons.org/licenses/MIT/

    * Copyright 2021 MoinMoin:RogerHaase, modified for moinmoin2
    * License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

    Upload multiple jpg files using jquery-file-upload. Tested with version 10.31.0.

    Reference: https://github.com/blueimp/jQuery-File-Upload/wiki/Basic-plugin#how-to-display-individual-upload-progress-with-the-basic-plugin

    Uploads are started when files are selected, there are no limits on file size
    nor number of files.
*/

$(function () {
    "use strict";
    $('#jfu-fileupload').fileupload({
        dataType: 'json',
        add: function(e, data) {
            // show file upload progress bar and overall progress bar after user selects files
            data.context = $('<p class="jfu-file"></p>')
            .text('Uploading... ')
            .appendTo('#jfu-progress')
            .append($('<b>').text(data.files[0].name))
            data.submit();
        },
        progressall: function (e, data) {
            // overall progress bar
            var progress = parseInt(data.loaded / data.total * 100, 10);
            $('#jfu-progress .jfu-bar').text('\u00a0 Overall Progress');
            $('#jfu-progress .jfu-bar').css('padding', '1em 0 1em 0');
            $('#jfu-progress .jfu-bar').css('width', progress + '%');
        },
        progress: function(e, data) {
            // create file progress bar for each file selected
            var progress = parseInt((data.loaded / data.total) * 100, 10);
            data.context.css("background-position-x", 100 - progress + "%");
        },
        done: function (e, data) {
            // show success/fail message for each file uploaded
            var url;
            $.each(data.result.files, function (index, file) {
                data.context.text(JSON.parse(data.jqXHR.responseText).message);
                // class is passed when upload fails, 403s are returned as 200 with error message
                data.context.addClass(JSON.parse(data.jqXHR.responseText).class);

                if (!(JSON.parse(data.jqXHR.responseText).class)) {
                    url = JSON.parse(data.jqXHR.responseText).url;
                    name = JSON.parse(data.jqXHR.responseText).name;
                    $(".moin-item-index").prepend('<div class="jfu-recent"><i class="fa fa-upload" /><a href=' + url + '>' + name + '</a></div>');
                }
            });
        }
    });
});
