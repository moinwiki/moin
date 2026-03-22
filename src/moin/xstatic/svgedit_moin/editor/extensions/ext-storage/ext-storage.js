import "./storageDialog.js";
const removeStoragePrefCookie = () => {
  expireCookie("svgeditstore");
};
const expireCookie = (cookie) => {
  document.cookie = encodeURIComponent(cookie) + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
};
const replaceStoragePrompt = (val) => {
  val = val ? "storagePrompt=" + val : "";
  const loc = top.location;
  if (loc.href.includes("storagePrompt=")) {
    loc.href = loc.href.replace(/([&?])storagePrompt=[^&]*(&?)/, function(n0, n1, amp) {
      return (val ? n1 : "") + val + (!val && amp ? n1 : amp || "");
    });
  } else {
    loc.href += (loc.href.includes("?") ? "&" : "?") + val;
  }
};
const extStorage = {
  name: "storage",
  init() {
    const svgEditor = this;
    const { svgCanvas, storage } = svgEditor;
    const {
      // When the code in svg-editor.js prevents local storage on load per
      //  user request, we also prevent storing on unload here so as to
      //  avoid third-party sites making XSRF requests or providing links
      // which would cause the user's local storage not to load and then
      // upon page unload (such as the user closing the window), the storage
      //  would thereby be set with an empty value, erasing any of the
      // user's prior work. To change this behavior so that no use of storage
      // or adding of new storage takes place regardless of settings, set
      // the "noStorageOnLoad" config setting to true in svgedit-config-*.js.
      noStorageOnLoad,
      forceStorage,
      canvasName
    } = svgEditor.configObj.curConfig;
    if (storage && // Cookies do not have enough available memory to hold large documents
    (forceStorage || !noStorageOnLoad && /(?:^|;\s*)svgeditstore=prefsAndContent/.test(document.cookie))) {
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
      if (e?.detail?.trigger === "ok") {
        if (e?.detail?.select !== "noPrefsOrContent") {
          const storagePrompt = new URL(top.location).searchParams.get(
            "storagePrompt"
          );
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
              if (svgEditor.storage) {
                svgEditor.storage.removeItem(name);
              }
              expireCookie(name);
            });
          }
          if (e?.detail?.select && e?.detail?.checkbox) {
            replaceStoragePrompt("false");
            return;
          }
        }
      } else if (e?.detail?.trigger === "cancel") {
        removeStoragePrefCookie();
      }
      setupBeforeUnloadListener();
      svgEditor.storagePromptState = "closed";
      svgEditor.updateCanvas(true);
    });
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
    const setupBeforeUnloadListener = () => {
      window.addEventListener("beforeunload", function() {
        if (!/(?:^|;\s*)svgeditstore=(?:prefsAndContent|prefsOnly)/.test(
          document.cookie
        )) {
          return;
        }
        if (/(?:^|;\s*)svgeditstore=prefsAndContent/.test(document.cookie)) {
          setSvgContentStorage(svgCanvas.getSvgString());
        }
        svgEditor.setConfig({ no_save_warning: true });
        const { curPrefs } = svgEditor.configObj;
        Object.entries(curPrefs).forEach(([key, val]) => {
          const store = val !== void 0;
          key = "svg-edit-" + key;
          if (!store) {
            return;
          }
          if (storage) {
            storage.setItem(key, val);
          } else if (window.widget) {
            window.widget.setPreferenceForKey(val, key);
          } else {
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
        const storagePrompt = new URL(top.location).searchParams.get(
          "storagePrompt"
        );
        if (loaded) {
          return;
        }
        loaded = true;
        if (!forceStorage && // If the URL has been explicitly set to always prompt the
        //  user (e.g., so one can be pointed to a URL where one
        // can alter one's settings, say to prevent future storage)...
        (storagePrompt === "true" || // ...or...if the URL at least doesn't explicitly prevent a
        //  storage prompt (as we use for users who
        // don't want to set cookies at all but who don't want
        // continual prompts about it)...
        storagePrompt !== "false" && // ...and this user hasn't previously indicated a desire for storage
        !/(?:^|;\s*)svgeditstore=(?:prefsAndContent|prefsOnly)/.test(
          document.cookie
        ))) {
          const options = Boolean(storage);
          svgEditor.storagePromptState = "waiting";
          const $storageDialog = document.getElementById("se-storage-dialog");
          $storageDialog.setAttribute("dialog", "open");
          $storageDialog.setAttribute("storage", options);
        } else if (!noStorageOnLoad || forceStorage) {
          setupBeforeUnloadListener();
        }
      }
    };
  }
};
export {
  extStorage as default
};
//# sourceMappingURL=ext-storage.js.map
