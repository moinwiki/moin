import { initialize } from "./storageDialog2.js";
//#region src/editor/extensions/ext-storage/ext-storage.js
/**
* @file ext-storage.js
*
* This extension allows automatic saving of the SVG canvas contents upon
*  page unload (which can later be automatically retrieved upon future
*  editor loads).
*
*  The functionality was originally part of the SVG Editor, but moved to a
*  separate extension to make the setting behavior optional, and adapted
*  to inform the user of its setting of local data.
*
* @license MIT
*
* @copyright 2010 Brett Zamir
* @todo Revisit on whether to use `svgEditor.pref` over directly setting
* `curConfig` in all extensions for a more public API (not only for `extPath`
* and `imagePath`, but other currently used config in the extensions)
* @todo We might provide control of storage settings through the UI besides the
*   initial (or URL-forced) dialog. *
*/
/**
* Expire the storage cookie.
* @returns {void}
*/
var removeStoragePrefCookie = () => {
	expireCookie("svgeditstore");
};
/**
* Set the cookie to expire.
* @param {string} cookie
* @returns {void}
*/
var expireCookie = (cookie) => {
	document.cookie = encodeURIComponent(cookie) + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
};
/**
* Replace `storagePrompt` parameter within URL.
* @param {string} val
* @returns {void}
* @todo Replace the string manipulation with `searchParams.set`
*/
var replaceStoragePrompt = (val) => {
	val = val ? "storagePrompt=" + val : "";
	const loc = top.location;
	if (loc.href.includes("storagePrompt=")) loc.href = loc.href.replace(/([&?])storagePrompt=[^&]*(&?)/, function(n0, n1, amp) {
		return (val ? n1 : "") + val + (!val && amp ? n1 : amp || "");
	});
	else loc.href += (loc.href.includes("?") ? "&" : "?") + val;
};
var ext_storage_default = {
	name: "storage",
	init() {
		const svgEditor = this;
		const { svgCanvas, svgeditPolicy, storage } = svgEditor;
		initialize(svgeditPolicy);
		const { noStorageOnLoad, forceStorage, canvasName } = svgEditor.configObj.curConfig;
		if (storage && (forceStorage || !noStorageOnLoad && /(?:^|;\s*)svgeditstore=prefsAndContent/.test(document.cookie))) {
			const key = "svgedit-" + canvasName;
			const cached = storage.getItem(key);
			if (cached) {
				svgEditor.loadFromString(cached);
				const name = storage.getItem(`title-${key}`) ?? "untitled.svg";
				svgEditor.topPanel.updateTitle(name);
				svgEditor.layersPanel.populateLayers();
			}
		}
		const storageBox = document.createElement("se-storage-dialog");
		storageBox.setAttribute("id", "se-storage-dialog");
		svgEditor.$container.append(storageBox);
		storageBox.init(svgEditor.i18next);
		storageBox.addEventListener("change", (e) => {
			storageBox.setAttribute("dialog", "close");
			if (e?.detail?.trigger === "ok") if (e?.detail?.select !== "noPrefsOrContent") {
				const storagePrompt = new URL(top.location).searchParams.get("storagePrompt");
				document.cookie = "svgeditstore=" + encodeURIComponent(e.detail.select) + "; expires=Fri, 31 Dec 9999 23:59:59 GMT";
				if (storagePrompt === "true" && e?.detail?.checkbox) {
					replaceStoragePrompt();
					return;
				}
			} else {
				removeStoragePrefCookie();
				if (svgEditor.configObj.curConfig.emptyStorageOnDecline && e?.detail?.checkbox) {
					setSvgContentStorage("");
					Object.keys(svgEditor.curPrefs).forEach((name) => {
						name = "svg-edit-" + name;
						if (svgEditor.storage) svgEditor.storage.removeItem(name);
						expireCookie(name);
					});
				}
				if (e?.detail?.select && e?.detail?.checkbox) {
					replaceStoragePrompt("false");
					return;
				}
			}
			else if (e?.detail?.trigger === "cancel") removeStoragePrefCookie();
			setupBeforeUnloadListener();
			svgEditor.storagePromptState = "closed";
			svgEditor.updateCanvas(true);
		});
		/**
		* Sets SVG content as a string with "svgedit-" and the current
		*   canvas name as namespace.
		* @param {string} svgString
		* @returns {void}
		*/
		const setSvgContentStorage = (svgString) => {
			const name = `svgedit-${svgEditor.configObj.curConfig.canvasName}`;
			if (!svgString) {
				storage.removeItem(name);
				storage.removeItem(`${name}-title`);
			} else {
				storage.setItem(name, svgString);
				storage.setItem(`title-${name}`, svgEditor.title);
			}
		};
		/**
		* Listen for unloading: If and only if opted in by the user, set the content
		*   document and preferences into storage:
		* 1. Prevent save warnings (since we're automatically saving unsaved
		*       content into storage)
		* 2. Use localStorage to set SVG contents (potentially too large to allow in cookies)
		* 3. Use localStorage (where available) or cookies to set preferences.
		* @returns {void}
		*/
		const setupBeforeUnloadListener = () => {
			window.addEventListener("beforeunload", function() {
				if (!/(?:^|;\s*)svgeditstore=(?:prefsAndContent|prefsOnly)/.test(document.cookie)) return;
				if (/(?:^|;\s*)svgeditstore=prefsAndContent/.test(document.cookie)) setSvgContentStorage(svgCanvas.getSvgString());
				svgEditor.setConfig({ no_save_warning: true });
				const { curPrefs } = svgEditor.configObj;
				Object.entries(curPrefs).forEach(([key, val]) => {
					const store = val !== void 0;
					key = "svg-edit-" + key;
					if (!store) return;
					if (storage) storage.setItem(key, val);
					else if (window.widget) window.widget.setPreferenceForKey(val, key);
					else {
						val = encodeURIComponent(val);
						document.cookie = encodeURIComponent(key) + "=" + val + "; expires=Fri, 31 Dec 9999 23:59:59 GMT";
					}
				});
			});
		};
		let loaded = false;
		return {
			name: "storage",
			callback() {
				const storagePrompt = new URL(top.location).searchParams.get("storagePrompt");
				if (loaded) return;
				loaded = true;
				if (!forceStorage && (storagePrompt === "true" || storagePrompt !== "false" && !/(?:^|;\s*)svgeditstore=(?:prefsAndContent|prefsOnly)/.test(document.cookie))) {
					const options = Boolean(storage);
					svgEditor.storagePromptState = "waiting";
					const $storageDialog = document.getElementById("se-storage-dialog");
					$storageDialog.setAttribute("dialog", "open");
					$storageDialog.setAttribute("storage", options);
				} else if (!noStorageOnLoad || forceStorage) setupBeforeUnloadListener();
			}
		};
	}
};
//#endregion
export { ext_storage_default as default };

//# sourceMappingURL=ext-storage.js.map