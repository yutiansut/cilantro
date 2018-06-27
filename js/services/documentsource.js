angular
.module('module.documentsource', ['module.messenger', 'module.webservice'])
.factory('documentsource', ['$rootScope', 'settings', 'webservice', 'messenger', 'dataset', 'editables','repository',
    function($rootScope, settings, webservice, messenger, dataset, editables,repository) {

    var folder = {};

    folder.reset = function() {
        folder.dir = []; // filenames
        folder.files  = {}; // pdf.js documents / index: filenames
        folder.stats  = {
            files: 0,
            analyzed: 0,
            loaded:  0,
            thumbnails: 0,
            _isOk: function(k, v) {
                return v >= folder.stats.files ? 1 : -1;
            }
        };
        folder.ready = false;
    };

    folder.reset();

    var requirePdfJs = new Promise(function(resolve) {
        /**
         * @ TODO include pdf.js (& require) with npm as well and replace this stuff
         */
        require.config({paths: {'pdfjs': 'inc/pdf.js'}});
        require(['pdfjs/display/api', 'pdfjs/display/global'], function(pdfjs_api, pdfjs_global) {
            console.log('2. required pdf.js');
            folder.status  = 'pdf.js loaded';

            folder.PDF = {
                "api": pdfjs_api,
                "global": pdfjs_global,
                "data": null,
                'object': null
            };

            folder.PDF.global.PDFJS.workerSrc = 'js/other/pdfjs_worker_loader.js';

            resolve();
        });
    });

    var loadFilePromises = [];

    var loadFiles = function() {
        folder.ready = false;

        for (let fileid in folder.dir) {

            console.log("URL", fileid);
            var url = settings.files_url + folder.dir[fileid].path;
            console.log("URL is " + url);

            var promise = new Promise(
                function documentPromiseResolve(resolve, fail) {

                    folder.PDF.api.getDocument(url).then(
                        function onGotDocument(pdf) {
                            var fileInfo = {
                                pdf: pdf,
                                filename: folder.dir[fileid].name,
                                url: this.url,
                                pagecontext: new editables.types.Pagecontext({maximum: pdf.pdfInfo.numPages})
                            };

                            var promise1 = pdf.getMetadata().then(function (meta) {
                                console.log(meta);
                                this.meta = meta.info
                            }.bind(fileInfo));
                            var promise2 = pdf.getDownloadInfo().then(function (dil) {
                                function fileSize(b) {
                                    var u = 0, s = 1024;
                                    while (b >= s || -b >= s) {
                                        b /= s;//
                                        u++;
                                    }
                                    return (u ? b.toFixed(1) + ' ' : b) + ' KMGTPEZY'[u] + 'B';
                                }

                                this.size = fileSize(dil.length);
                            }.bind(fileInfo));

                            folder.files[this.url] = fileInfo;

                            let metadataLoaded = function () {
                                dataset.loadedFiles[this.url] = {
                                    size: this.size,
                                    url: this.url,
                                    pagecontext: this.pagecontext
                                };
                                console.log("loadedFiles updated", dataset.loadedFiles);
                                messenger.alert('document nr ' + Object.keys(folder.files).length + ' loaded');
                                $rootScope.$broadcast('gotFile', this.url);
                                refreshView();
                                resolve();
                            }.bind(fileInfo);


                            Promise.all([promise1, promise2]).then(metadataLoaded, metadataLoaded);
                            // if metadata could not be loaded, it's no reason not to continue... but we should at least try it


                        }.bind(
                            {
                                filename: folder.dir[fileid].name,
                                url: folder.dir[fileid].path
                            }
                        ),

                        function onFailDocument(reason) {
                            messenger.alert("get document " + url + " failed: " + reason, true);
                            resolve(); //!
                        }
                    )
                }
            );


            loadFilePromises.push(promise);
            //console.log('promises collected: ' + loadFilePromises.length);

        }

    }

    folder.getDocuments = function(path) {
        console.log("selected files to load", path);

        if (!path || path === "") {
            return;
        }

        let filesObject = repository.getFileInfo(path);

        if (filesObject.type === 'directory') {

            messenger.alert('loading folder contents: ' + path);

            folder.dir = repository.list[path].contents;

            console.log('got folder:' + path, folder);

            folder.stats.files = folder.dir.length;
            messenger.alert('folder contents loaded');

        } else {
            folder.dir = [filesObject];
            console.log(folder.dir)
            folder.stats.files = 1;
        }

        requirePdfJs.then(function() {
            messenger.alert('ready for loading files');
            loadFiles();
            Promise.all(loadFilePromises).then(function() {
                messenger.alert("All Files loaded");
                refreshView();
                $rootScope.$broadcast('gotAll');
                folder.ready = true;
            })
        });
    };

    /**
     *
     * @param article
     * @returns {*}
     */
    folder.getFileInfo = function(article) {

        if (article.filepath.value.value === 'none') {
            return {}
        }
        var file = folder.files[article.filepath.value.value];
        if (angular.isUndefined(file)) {
            return {'alert': 'file not known'}
        }

        return {
            'pages': file.pagecontext.maximum,
            'page offset': file.pagecontext.offset,
            'size': file.size
        }

    }


    /**
     * trigger trumbnail recreation (on page or filepath change)
     */
    $rootScope.$on('thumbnaildataChanged', function($event, article) {
        if (article.pages.value.startPdf === 0) { // while creation
            return;
        }
        if (!angular.isUndefined(folder.files[article.filepath.value.value])) {
            article.pages.context = folder.files[article.filepath.value.value].pagecontext;
            folder.updateThumbnail(article);
        } else {
            article.pages.resetContext();
            folder.removeThumbnail(article._.id);
        }
    });


    /**
     * call this from a button or something ...
     * @param article
     */
    folder.updateThumbnail = function(article) {
        console.log("recreate thumbnail for", article._.id, article.pages.value.startPdf, article.filepath.value.value);
        folder.files[article.filepath.value.value].pdf.getPage(article.pages.value.startPdf).then(
            function updateThumbnailGotPageSuccess(page) {
                folder.createThumbnail(page, article._.id)
            },
            function updateThumbnailGotPageFail(page) {
                messenger.alert("Page " + article.pages.value.startPdf + " not found", true);
                console.log('page not found', article.pages.value.startPdf, article._.id);
                folder.removeThumbnail(article._.id)
            }
        );
    }


    /**
     * ... or this from inside a getPage promise
     * @param page
     * @param containerId
     */
    folder.createThumbnail = function(page, containerId) {
        var container = angular.element(document.querySelector('#thumbnail-container-' + containerId));
        var img = container.find('img');

        var viewport = page.getViewport(1.5); // scale 1.5
        var canvas = document.createElement('canvas');
        var ctx = canvas.getContext('2d');
        canvas.height = viewport.height; // 626.16 * 1.5
        canvas.width = viewport.width; // 399.84 * 1.5

        var renderContext = {
            canvasContext: ctx,
            viewport: viewport
        };

        container.addClass('loader');
        img.unbind('load');
        img.on("load", function() {
            container.removeClass('loader');
        });

        page.render(renderContext).then(function(){
            console.log("thumbnail created");
            ctx.globalCompositeOperation = "destination-over";
            ctx.fillStyle = "#123456";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            dataset.thumbnails[containerId] = canvas.toDataURL();
            folder.stats.thumbnails = Object.keys(dataset.thumbnails).length;
            refreshView()
        });

    }

    folder.removeThumbnail = function(containerId) {
        console.log("thumbnail removed", containerId);
        delete dataset.thumbnails[containerId];
        folder.stats.thumbnails = Object.keys(dataset.thumbnails).length;
    }

    /**
     * since the pdf.js stuff is happening outside angular is is ansync we need this shit here
     *
     */
    function refreshView() {
        $rootScope.$broadcast('refreshView');
    }

    return folder;


}]);
