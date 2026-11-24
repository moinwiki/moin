// Copyright: 2026 MoinMoin project
// License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const searchPath = path.join(__dirname, "..", "search.js");
const searchSource = fs.readFileSync(searchPath, "utf8");

// Load search.js with a minimal fake jQuery and fake timers.
function searchPage() {
    const state = {
        query: "",
        trash: "exclude",
        requests: [],
        results: null,
        timers: new Map(),
        nextTimer: 1,
        handlers: {},
    };

    function noop() {
        return this;
    }

    function stub(extra = {}) {
        return {
            attr: noop, addClass: noop, toggleClass: noop, hide: noop, remove: noop,
            each: noop, val: () => undefined, html: noop, ...extra,
        };
    }

    function fakeRequest(data) {
        const callbacks = {done: [], fail: [], always: []};
        const request = {
            data,
            aborted: false,
            done(cb) { callbacks.done.push(cb); return request; },
            fail(cb) { callbacks.fail.push(cb); return request; },
            always(cb) { callbacks.always.push(cb); return request; },
            abort() {
                request.aborted = true;
                callbacks.fail.forEach((cb) => cb(request, "abort"));
                callbacks.always.forEach((cb) => cb(request, "abort"));
            },
            respond(body) {
                callbacks.done.forEach((cb) => cb(body));
                callbacks.always.forEach((cb) => cb(body));
            },
            error() {
                callbacks.fail.forEach((cb) => cb(request, "error"));
                callbacks.always.forEach((cb) => cb(request, "error"));
            },
        };
        return request;
    }

    const document = {};

    function $(selector) {
        if (selector === document) {
            return {
                ready(fn) { fn(); },
                on(event, sel, fn) { state.handlers[`${event} ${sel}`] = fn; },
            };
        }
        switch (selector) {
            case "#moin-long-searchform":
                return stub({submit(fn) { state.handlers.submit = fn; }});
            case ".moin-search-query":
                return stub({
                    val: () => state.query,
                    on(event, fn) { state.handlers[`${event} query`] = fn; },
                });
            case "#moin-wiki-root":
                return stub({val: () => "/wiki"});
            case '[name="trash"]:checked':
                return stub({val: () => state.trash});
            case "#finalresults":
                return stub({html(body) { state.results = body; }});
            default:
                return stub();
        }
    }
    $.param = (params) => JSON.stringify(params);
    $.ajax = (options) => {
        const request = fakeRequest(options.data);
        state.requests.push(request);
        return request;
    };

    const context = {
        $,
        document,
        setTimeout(fn) {
            const id = state.nextTimer++;
            state.timers.set(id, fn);
            return id;
        },
        clearTimeout(id) {
            state.timers.delete(id);
        },
    };
    vm.runInNewContext(searchSource, context, {filename: searchPath});

    return {
        state,
        type(text) {
            state.query = text;
            state.handlers["input query"]();
        },
        changeOption() {
            state.handlers["change .moin-searchoptions input"]();
        },
        pressEnter() {
            return state.handlers.submit({preventDefault() {}});
        },
        elapse() {
            const pending = [...state.timers.values()];
            state.timers.clear();
            pending.forEach((fn) => fn());
        },
    };
}

test("typing does not send a request before the input is quiet", () => {
    const page = searchPage();
    page.type("w");
    page.type("wi");
    page.type("wik");
    assert.equal(page.state.requests.length, 0);
    assert.equal(page.state.timers.size, 1);
    page.elapse();
    assert.equal(page.state.requests.length, 1);
    assert.equal(page.state.requests[0].data.q, "wik");
});

test("unchanged search parameters send no new request", () => {
    const page = searchPage();
    page.type("wiki");
    page.elapse();
    page.type("wiki");  // e.g. arrow key or modifier key: same text
    page.elapse();
    page.pressEnter();
    assert.equal(page.state.requests.length, 1);
});

test("Enter searches right away and cancels the pending delayed search", () => {
    const page = searchPage();
    page.type("wiki");
    page.pressEnter();
    assert.equal(page.state.requests.length, 1);
    assert.equal(page.state.timers.size, 0);
});

test("a newer request aborts the running one and stale results are not shown", () => {
    const page = searchPage();
    page.type("wiki");
    page.elapse();
    page.type("wikis");
    page.elapse();
    const [first, second] = page.state.requests;
    assert.equal(first.aborted, true);
    assert.equal(second.aborted, false);
    first.respond("stale results");
    assert.equal(page.state.results, null);
    second.respond("fresh results");
    assert.equal(page.state.results, "fresh results");
    // aborting the first request must not have made the second one look unsent
    page.type("wikis");
    page.elapse();
    assert.equal(page.state.requests.length, 2);
});

test("changing a search option triggers a delayed search", () => {
    const page = searchPage();
    page.type("wiki");
    page.elapse();
    page.state.trash = "include";
    page.changeOption();
    assert.equal(page.state.requests.length, 1);
    page.elapse();
    assert.equal(page.state.requests.length, 2);
    assert.equal(page.state.requests[1].data.trash, true);
});

test("a failed request can be retried with the same parameters", () => {
    const page = searchPage();
    page.type("wiki");
    page.elapse();
    page.state.requests[0].error();
    page.pressEnter();
    assert.equal(page.state.requests.length, 2);
});
