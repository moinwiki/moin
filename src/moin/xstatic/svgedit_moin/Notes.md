## Notes on the use of Trusted Types

SVG-Edit already performs rigorous input sanitization internally.

Use of trusted HTML assumes the input is safe (does not contain unvalidated user or external input).
In most of the cases input is a JS template literal.

A detailed risk analysis would be nice to have.

## Build the SVG Editor with Moin2 modifications

    git clone https://github.com/roland-ruedenauer/elix.git
    cd elix
    git checkout moin2
    npm install
    cd ..

    git clone https://github.com/roland-ruedenauer/svgedit.git
    cd svgedit
    git checkout moin2
    npm install
    npm run build
    cd ..

## Update Moin2 with the modified SVG Editor

    git clone https://github.com/moinwiki/moin.git
    cd moin
    git checkout -b update-svgedit-moin
    rsync -av --exclude=editor/tests  ../svgedit/dist/editor src/moin/xstatic/svgedit_moin/
    git add -u
    git commit -m "Update svgedit_moin"
    cd ..

## Latest Update

* __svgedit__: commit `244a26c88e1ab1c32911c5b3637e214d7a7d8b25` plus Moin2 changes
* __elix__: commit `8cb7ed40e45af4a7823b8f3437d21a92e8b574c5` plus Moin2 changes
