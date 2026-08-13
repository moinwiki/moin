import { __vitePreload } from "../_virtual/_vite/preload-helper.js";
//#region src/editor/extensions/ext-helloworld/ext-helloworld.js
function __variableDynamicImportRuntime0__(path) {
	switch (path) {
		case "./locale/en.js": return __vitePreload(() => import("./locale/en.js"), [], import.meta.url);
		case "./locale/fr.js": return __vitePreload(() => import("./locale/fr.js"), [], import.meta.url);
		case "./locale/tr.js": return __vitePreload(() => import("./locale/tr.js"), [], import.meta.url);
		case "./locale/uk.js": return __vitePreload(() => import("./locale/uk.js"), [], import.meta.url);
		case "./locale/zh-CN.js": return __vitePreload(() => import("./locale/zh-CN.js"), [], import.meta.url);
		default: return new Promise(function(resolve, reject) {
			(typeof queueMicrotask === "function" ? queueMicrotask : setTimeout)(reject.bind(null, /* @__PURE__ */ new Error("Unknown variable dynamic import: " + path)));
		});
	}
}
/**
* @file ext-helloworld.js
*
* @license MIT
*
* @copyright 2010 Alexis Deveria
*
*/
/**
* This is a very basic SVG-Edit extension. It adds a "Hello World" button in
*  the left ("mode") panel. Clicking on the button, and then the canvas
*  will show the user the point on the canvas that was clicked on.
*/
var name = "helloworld";
var loadExtensionTranslation = async function(svgEditor) {
	let translationModule;
	const lang = svgEditor.configObj.pref("lang");
	try {
		translationModule = await __variableDynamicImportRuntime0__(`./locale/${lang}.js`);
	} catch (_error) {
		console.warn(`Missing translation (${lang}) for ${name} - using 'en'`);
		translationModule = await __vitePreload(() => import("./locale/en.js"), [], import.meta.url);
	}
	svgEditor.i18next.addResourceBundle(lang, name, translationModule.default);
};
var ext_helloworld_default = {
	name,
	async init({ _importLocale }) {
		const svgEditor = this;
		await loadExtensionTranslation(svgEditor);
		const { svgCanvas } = svgEditor;
		const { $id, $click } = svgCanvas;
		return {
			name: svgEditor.i18next.t(`${name}:name`),
			callback() {
				const buttonTemplate = document.createElement("template");
				buttonTemplate.innerHTML = `
        <se-button id="hello_world" title="${`${name}:buttons.0.title`}" src="hello_world.svg"></se-button>
        `;
				$id("tools_left").append(buttonTemplate.content.cloneNode(true));
				$click($id("hello_world"), () => {
					svgCanvas.setMode("hello_world");
				});
			},
			mouseDown() {
				if (svgCanvas.getMode() === "hello_world") return { started: true };
			},
			mouseUp(opts) {
				if (svgCanvas.getMode() === "hello_world") {
					const zoom = svgCanvas.getZoom();
					const x = opts.mouse_x / zoom;
					const y = opts.mouse_y / zoom;
					const text = svgEditor.i18next.t(`${name}:text`, {
						x,
						y
					});
					alert(text);
				}
			}
		};
	}
};
//#endregion
export { ext_helloworld_default as default };

//# sourceMappingURL=ext-helloworld.js.map