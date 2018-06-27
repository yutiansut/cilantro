/* step control */

angular
.module('module.steps', [])
.factory("steps", ['documentsource', 'dataset', 'messenger', function(documentsource, dataset, messenger) {

    const cacheKiller = '?nd=' + Date.now();

    let steps = {
        current : "home",
        isStarted: false
    };

    steps.views = {
        "home": {
            "template": "partials/views/home.html",
            "title": "Start",
            "showIf": function() {return !steps.isStarted}
        },
        "restart": {
            "template": "partials/views/restart.html",
            "title": "Restart",
            "showIf": function() {return steps.isStarted}
        },
        "documents": {
            "template": "partials/views/documents.html",
            "title": "Documents",
            "showIf": function() {return documentsource.ready}
        },
        "overview": {
            "template": "partials/views/overview.html",
            "title": "Overview",
            "showIf": function() {return documentsource.ready}
        },
        "articles": {
            "template": "partials/views/articles.html",
            "title": "Articles",
            "showIf": function() {return documentsource.ready}
        },
        "publish": {
            "template": "partials/views/finish.html",
            "title": "Publish",
            "showIf": function() {return steps.isStarted && documentsource.ready && dataset.isReadyToUpload()}
        },
        "fatal": {
            "template": "partials/views/fatal.html",
            "title": "Fatal Error",
            "showIf": function() {return false}
        }
    };

    steps.change = function(to) {

        if (typeof steps.views[to] === "undefined") {
            console.warn('view ' + to + ' does not exist');
            return;
        }

        if (to === steps.current) {
            return;
        }

        console.log('Tab change to: ', to);
        //$scope.message.reset();
        steps.current = to;

    };

    steps.getTemplate = function() {
        if (angular.isUndefined(steps.views[steps.current]) || angular.isUndefined(steps.views[steps.current].template)) {
            messenger.error("View '" + steps.current + "' not found.");
            steps.current = "fatal";
        }
        return steps.views[steps.current].template + cacheKiller;
    };


    return (steps);
}]);
