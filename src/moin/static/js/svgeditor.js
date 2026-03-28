import Editor from "/+serve/svgedit_moin/editor/Editor.js";

// SVG Editor
const svgedit_elem = document.querySelector(".svgedit");
if (svgedit_elem) {
    const svg_editor = new Editor(svgedit_elem);
    svg_editor.setConfig({
        allowInitialUserOverride: true,
        curPrefs: { lang: "en" },
        extensions: [
            "ext-connector",
            "ext-eyedropper",
            "ext-grid",
            "ext-layer_view",
            "ext-markers",
            "ext-overview_window",
            "ext-panning",
            "ext-polystar",
            "ext-shapes",
            "ext-storage"
        ],
        extPath: "/+serve/svgedit_moin/editor/extensions",
        imgPath: "/+serve/svgedit_moin/editor/images",
        noDefaultExtensions: true,
        userExtensions: [
            { pathName: './extensions/ext-moin2/ext-moin2.js' }
        ]
    });
    svg_editor.init();
    const data_url = svgedit_elem.getAttribute("data-url");
    if (data_url) {
        svg_editor.loadFromURL(data_url, { cache: false, noAlert: true });
    }
}
