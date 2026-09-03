// Copyright: 2026 NOQT
// License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const commonPath = path.join(__dirname, "..", "common.js");
const commonSource = fs.readFileSync(commonPath, "utf8");

function cancelScenario({changed, cancelClass = false, confirmResult = true}) {
    const state = {
        changed,
        confirmCalls: 0,
        confirmMessage: null,
        handler: null,
        prevented: false,
    };

    const cancelButton = {
        click(handler) {
            if (handler) {
                state.handler = handler;
            } else {
                state.handler.call(cancelButton, {
                    preventDefault() {
                        state.prevented = true;
                    },
                });
            }
            return cancelButton;
        },
        hasClass(className) {
            return className === "moin-cancel" && cancelClass;
        },
    };
    const modifyForm = {
        hasClass(className) {
            return className === "moin-changed-input" && state.changed;
        },
        removeClass(className) {
            if (className === "moin-changed-input") {
                state.changed = false;
            }
            return modifyForm;
        },
    };
    const document = {
        getElementById(id) {
            assert.equal(id, "moin-cancel-text-button");
            return cancelButton;
        },
    };
    const window = {
        confirm(message) {
            state.confirmCalls += 1;
            state.confirmMessage = message;
            return confirmResult;
        },
        location: "unchanged",
        trustedTypes: undefined,
    };

    function $(selector) {
        if (selector === document) {
            return {ready() {}};
        }
        if (selector === cancelButton || selector === "#moin-cancel-text-button") {
            return cancelButton;
        }
        if (selector === "#moin-modify") {
            return modifyForm;
        }
        if (selector === "#moin-wiki-root") {
            return {val: () => "/wiki"};
        }
        if (selector === "#moin-item-name") {
            return {val: () => "Example"};
        }
        throw new Error(`Unexpected selector: ${selector}`);
    }
    $.i18n = {_: (message) => message};

    const context = {document, $, window};
    vm.runInNewContext(commonSource, context, {filename: commonPath});
    context.cancelEdit();

    function result() {
        return {
            changed: state.changed,
            confirmCalls: state.confirmCalls,
            confirmMessage: state.confirmMessage,
            nativeNavigation: !state.prevented && !cancelClass,
            prevented: state.prevented,
            windowLocation: window.location,
        };
    }

    function click() {
        state.prevented = false;
        cancelButton.click();
        return result();
    }

    return {click, context, result};
}

test("rejecting discard keeps changed content on the form", () => {
    const scenario = cancelScenario({changed: true, confirmResult: false});
    assert.deepEqual(scenario.click(), {
        changed: true,
        confirmCalls: 1,
        confirmMessage: "All changes will be discarded!",
        nativeNavigation: false,
        prevented: true,
        windowLocation: "unchanged",
    });
});

test("accepting discard allows the themed form submission to leave", () => {
    const scenario = cancelScenario({changed: true});
    assert.deepEqual(scenario.click(), {
        changed: false,
        confirmCalls: 1,
        confirmMessage: "All changes will be discarded!",
        nativeNavigation: true,
        prevented: false,
        windowLocation: "unchanged",
    });
});

test("an unchanged themed form leaves without a dialog", () => {
    const scenario = cancelScenario({changed: false});
    assert.deepEqual(scenario.click(), {
        changed: false,
        confirmCalls: 0,
        confirmMessage: null,
        nativeNavigation: true,
        prevented: false,
        windowLocation: "unchanged",
    });
});

test("Basic theme Cancel navigates directly after confirmation", () => {
    const scenario = cancelScenario({changed: true, cancelClass: true});
    assert.deepEqual(scenario.click(), {
        changed: false,
        confirmCalls: 1,
        confirmMessage: "All changes will be discarded!",
        nativeNavigation: false,
        prevented: true,
        windowLocation: "/wiki/Example",
    });
});

test("Topside proxy dispatches the hidden Cancel control", () => {
    const layoutPath = path.join(__dirname, "..", "..", "..", "themes", "topside", "templates", "layout.html");
    const layout = fs.readFileSync(layoutPath, "utf8");
    const proxyAction = layout.match(/<button class="moin-button" onclick="([^"]+)">Cancel<\/button>/)[1];
    const scenario = cancelScenario({changed: true, confirmResult: false});

    vm.runInNewContext(proxyAction, scenario.context);

    assert.deepEqual(scenario.result(), {
        changed: true,
        confirmCalls: 1,
        confirmMessage: "All changes will be discarded!",
        nativeNavigation: false,
        prevented: true,
        windowLocation: "unchanged",
    });
});
