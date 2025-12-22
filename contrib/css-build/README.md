## Basic theme SCSS file compilation support

**Requirements**

Node.js and the node package manager (npm) have to be installed.

**Build**

To build `theme.css` from `src/moin/themes/basic/scss/theme.scss` using the SASS compiler, you may issue

    $ npm install && npm run build

**Notes**

Bootstrap 5.3 makes use of the deprecated `@import` directive and other deprecated SASS features, which causes many warnings to be output when compiling the Basic theme SCSS file.
This is a know issue and is currently being worked on (see [dart-sass 1.80.0+ throwing a lot of deprecations](https://github.com/twbs/bootstrap/issues/40962) for details).

The build command in `package.json` uses options to suppress warnings resulting from the use of `@import` and any included dependencies. 
