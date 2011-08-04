/*
 * jQuery File Upload User Interface Extended Plugin 4.4.1
 * https://github.com/blueimp/jQuery-File-Upload
 *
 * Copyright 2010, Sebastian Tschan, https://blueimp.net
 * Copyright 2011, Thomas Waldmann (adapted for MoinMoin)
 *
 * Licensed under the MIT license:
 * http://creativecommons.org/licenses/MIT/
 */

/*jslint regexp: false */
/*global jQuery */

(function ($) {
    'use strict';

    var UploadHandler,
        methods;

    // Emulate jQuery UI button (without states) if not available:
    if (typeof $().button !== 'function') {
        $.fn.button = function (options) {
            return this.each(function () {
                if (options === 'destroy') {
                    $(this).removeClass(
                        'ui-button ui-widget ui-state-default ui-corner-all' +
                            ' ui-button-icon-only ui-button-text-icon-primary'
                    ).html($(this).text());
                } else {
                    $(this)
                        .addClass('ui-button ui-widget ui-state-default ui-corner-all')
                        .addClass(
                            options.text === false ? 'ui-button-icon-only' :
                                'ui-button-text-icon-primary'
                        )
                        .html($('<span class="ui-button-text"/>').text($(this).text()))
                        .prepend(
                            $('<span class="ui-button-icon-primary ui-icon"/>')
                                .addClass(options.icons.primary)
                        );
                }
            });
        };
    }
        
    UploadHandler = function (container, options) {
        var uploadHandler = this;

        this.url = container.find('form:first').attr('action');
        this.dropZone = container.find('form:first');
        this.uploadTable = container.find('.files:first');
        this.downloadTable = this.uploadTable;
        this.progressAllNode = container.find('.file_upload_overall_progress div:first');
        this.uploadTemplate = this.uploadTable.find('.file_upload_template:first');
        this.downloadTemplate = this.uploadTable.find('.file_download_template:first');
        this.multiButtons = container.find('.file_upload_buttons:first');
        
        this.formatFileName = function (name) {
            return name.replace(/^.*[\/\\]/, '');
        };
        
        this.enableDragToDesktop = function () {
            var link = $(this),
                url = link.get(0).href,
                name = decodeURIComponent(url.split('/').pop()).replace(/:/g, '-'),
                type = 'application/octet-stream';
            link.bind('dragstart', function (event) {
                try {
                    event.originalEvent.dataTransfer
                        .setData('DownloadURL', [type, name, url].join(':'));
                } catch (e) {}
            });
        };

        this.buildMultiUploadRow = function (files, handler) {
            var rows = $('<tbody style="display:none;"/>');
            $.each(files, function (index, file) {
                var row = handler.buildUploadRow(files, index, handler).show(),
                    cells = row.find(
                        '.file_upload_progress, .file_upload_start, .file_upload_cancel'
                    );
                if (index) {
                    cells.remove();
                } else {
                    cells.attr('rowspan', files.length);
                }
                rows.append(row);
            });
            return rows;
        };

        this.buildUploadRow = function (files, index, handler) {
            if (typeof index !== 'number') {
                return handler.buildMultiUploadRow(files, handler);
            }
            var file = files[index],
                fileName = handler.formatFileName(file.name),
                uploadRow = handler.uploadTemplate
                    .clone().removeAttr('id');
            uploadRow.find('.file_name')
                .text(fileName);
            uploadRow.find('.file_upload_start button')
                .button({icons: {primary: 'ui-icon-circle-arrow-e'}, text: false});
            uploadRow.find('.file_upload_cancel button')
                .button({icons: {primary: 'ui-icon-cancel'}, text: false});
            return uploadRow;
        };

        this.buildMultiDownloadRow = function (files, handler) {
            var rows = $('<tbody style="display:none;"/>');
            $.each(files, function (index, file) {
                rows.append(handler.buildDownloadRow(file, handler).show());
            });
            return rows;
        };

        this.buildDownloadRow = function (file, handler) {
            if ($.isArray(file)) {
                return handler.buildMultiDownloadRow(file, handler);
            }
            var fileName = handler.formatFileName(file.name),
                fileUrl = file.url,
                fileUrlDownload = file.url_download,
                downloadRow = handler.downloadTemplate
                    .clone().removeAttr('id');
            downloadRow.attr('data-id', file.id || file.name);
            downloadRow.find('.file_name a')
                .text(fileName);
            downloadRow.find('.file_name a')
                .attr('href', fileUrl || null);
            downloadRow.find('.file_download a')
                .text('DL');
            downloadRow.find('.file_download a')
                .attr('href', fileUrlDownload || null)
                .each(handler.enableDragToDesktop);
            return downloadRow;
        };
        
        this.beforeSend = function (event, files, index, xhr, handler, callBack) {
            var fileSize = null;
            if (typeof index === 'undefined') {
                fileSize = 0;
                $.each(files, function (index, file) {
                    if (file.size > fileSize) {
                        fileSize = file.size;
                    }
                });
            } else {
                fileSize = files[index].size;
            }
            if (fileSize === 0) {
                setTimeout(function () {
                    handler.onAbort(event, files, index, xhr, handler);
                }, 10000);
                return;
            }
            uploadHandler.multiButtons.find('.file_upload_start:first, .file_upload_cancel:first').fadeIn();
            handler.uploadRow.find('.file_upload_start button').click(function (e) {
                $(this).fadeOut(function () {
                    if (!$('.files .file_upload_start button:visible:first').length) {
                        uploadHandler.multiButtons.find('.file_upload_start:first').fadeOut();
                    }
                });
                callBack();
                e.preventDefault();
            });
        };

        this.onCompleteAll = function (list) {
            if (!uploadHandler.uploadTable.find('.file_upload_progress div:visible:first').length) {
                uploadHandler.multiButtons.find('.file_upload_start:first, .file_upload_cancel:first').fadeOut();
            }
        };

        this.initEventHandlers = function () {
            container.find('.file_upload_cancel button').live('click', function () {
                setTimeout(function () {
                    if (!uploadHandler.uploadTable.find('.file_upload_progress div:visible:first').length) {
                        uploadHandler.multiButtons.find('.file_upload_start:first, .file_upload_cancel:first').fadeOut();
                    }
                }, 500);
            });
        };

        this.destroyEventHandlers = function () {
        };
        
        this.multiButtonHandler = function (e) {
            uploadHandler.uploadTable.find(e.data.selector + ' button:visible').click();
            e.preventDefault();
        };
        
        this.initMultiButtons = function () {
            uploadHandler.multiButtons.find('.file_upload_start:first')
                .button({icons: {primary: 'ui-icon-circle-arrow-e'}})
                .bind('click', {selector: '.file_upload_start'}, uploadHandler.multiButtonHandler);
            uploadHandler.multiButtons.find('.file_upload_cancel:first')
                .button({icons: {primary: 'ui-icon-cancel'}})
                .bind('click', {selector: '.file_upload_cancel'}, uploadHandler.multiButtonHandler);
        };
        
        this.destroyMultiButtons = function () {
            uploadHandler.multiButtons.find(
                '.file_upload_start:first, .file_upload_cancel:first'
            ).unbind('click', uploadHandler.multiButtonHandler).button('destroy').show();
        };

        this.initExtended = function () {
            uploadHandler.initEventHandlers();
            uploadHandler.initMultiButtons();
        };

        this.destroyExtended = function () {
            uploadHandler.destroyEventHandlers();
            uploadHandler.destroyMultiButtons();
        };

        $.extend(this, options);
    };

    methods = {
        init : function (options) {
            return this.each(function () {
                $(this).fileUploadUI(new UploadHandler($(this), options));
            });
        },
        
        option: function (option, value, namespace) {
            if (!option || (typeof option === 'string' && typeof value === 'undefined')) {
                return $(this).fileUpload('option', option, value, namespace);
            }
            return this.each(function () {
                $(this).fileUploadUI('option', option, value, namespace);
            });
        },
            
        destroy : function (namespace) {
            return this.each(function () {
                $(this).fileUploadUI('destroy', namespace);
            });
        },
        
        upload: function (files, namespace) {
            return this.each(function () {
                $(this).fileUploadUI('upload', files, namespace);
            });
        }
    };
    
    $.fn.fileUploadUIX = function (method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method "' + method + '" does not exist on jQuery.fileUploadUIX');
        }
    };
    
}(jQuery));


/*
 * jQuery File Upload Plugin JS Example 4.4.1
 * https://github.com/blueimp/jQuery-File-Upload
 *
 * Copyright 2010, Sebastian Tschan
 * https://blueimp.net
 *
 * Licensed under the MIT license:
 * http://creativecommons.org/licenses/MIT/
 */

/*global $ */

$(function () {
    // Initialize jQuery File Upload (Extended User Interface Version):
    $('#file_upload').fileUploadUIX();

    // Load existing files:
    $.getJSON($('#file_upload').fileUploadUIX('option', 'url'), function (files) {
        var fileUploadOptions = $('#file_upload').fileUploadUIX('option');
        $.each(files, function (index, file) {
            fileUploadOptions.buildDownloadRow(file, fileUploadOptions)
                .appendTo(fileUploadOptions.downloadTable).fadeIn();
        });
    });
});
