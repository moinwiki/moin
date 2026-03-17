# Copyright: 2015-2017 MoinMoin:RogerHaase
# Copyright: 2023-2024 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - CLI command to create a static HTML dump for each current item in this wiki.

Usage:
    moin dump-html <options>

Options:
    --theme=<theme name>
    --directory=<output directory name>  # If the name contains a '/', it is treated as a full path; otherwise it is created under the Moin root directory.
    --exclude-ns=<comma-separated list of namespaces to exclude>
    --query=<item name or regex to select items>

Defaults:
    --theme=topside_cms
    --directory=<install root dir>/HTML
    --exclude-ns=userprofiles

Works best with a CMS-like theme that excludes wiki navigation links for login, edit, etc., which are not useful in a static HTML dump.

Most HTML-formatted files created in the root (HTML) directory will not have names ending with .html, just as the paths used by the wiki server do not end with .html (e.g., http://127.0.0.1/Home). All tested browsers follow links to pages without .html suffixes without complaint.

Duplicate copies of the home page and index page are created with names ending with .html.

Items with media content types and names ending in common media suffixes (.png, .svg, .mp4, …) will have their raw data (not HTML-formatted pages) stored in the root HTML directory. All tested browsers treat HTML-formatted pages with names ending in common media suffixes as corrupt files.

The raw data for all items is stored in the +get subdirectory.
"""

from __future__ import annotations

import shutil
import re

import click
from flask import render_template
from flask.cli import FlaskGroup

from pathlib import Path
from urllib.parse import urlparse

from whoosh.query import Every, Regex

from werkzeug.exceptions import Forbidden

from moin import current_app, flaskg, log
from moin.app import create_app, before_wiki, setup_user_anon
from moin.apps.frontend.views import show_item
from moin.constants.keys import CONTENTTYPE, CURRENT, NAME_EXACT, THEME_NAME, LATEST_REVS
from moin.constants.contenttypes import (
    CONTENTTYPE_MEDIA,
    CONTENTTYPE_MEDIA_SUFFIX,
    CONTENTTYPE_OTHER,
    CONTENTTYPE_OTHER_SUFFIX,
)
from moin.items import Item
from moin.utils import get_xstatic_module_path_map
from moin.storage.middleware.indexing import Item as IndexedItem, Revision

logging = log.getLogger(__name__)

PARENT_DIR = "../"


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command("dump-html", help="Create a static HTML snapshot of this wiki")
@click.option(
    "--directory",
    "-d",
    type=str,
    required=False,
    default="HTML",
    help="Directory name for the output files; default: HTML",
)
@click.option(
    "--theme",
    "-t",
    required=False,
    default="topside_cms",
    help="Name of the theme used to create output pages; default: topside_cms",
)
@click.option(
    "--exclude-ns",
    "-e",
    required=False,
    default="userprofiles",
    help="Comma-separated list of excluded namespaces; default: userprofiles",
)
@click.option("--query", "-q", required=False, default=None, help="name or regex of items to be included")
@click.option(
    "--convenience-duplicates", required=False, default=False, help="create convenience duplicates of toplevel pages"
)
def Dump(
    directory: str = "HTML",
    theme: str = "topside_cms",
    exclude_ns: str | None = "userprofiles",
    user: str | None = None,
    query: str | None = None,
    convenience_duplicates: bool = False,
) -> None:
    with current_app.test_request_context():
        logging.info("Dump html started")
        if theme:
            current_app.cfg.user_defaults[THEME_NAME] = theme
        excluded_namespaces = exclude_ns.split(",") if exclude_ns else []

        before_wiki()
        setup_user_anon()

        wiki_root = Path(current_app.cfg.wikiconfig_dir)
        moinmoin = Path(log.__file__).parent  # log is imported from moin -> this is src/moin
        logging.debug("wiki_root dir: %s, moin src dir: %s", wiki_root, moinmoin)
        if "/" in directory:
            # user has specified complete path to root
            html_root = Path(directory)
        else:
            html_root = Path(wiki_root) / directory

        # override ACLs with permission to read all items
        for _, acls in current_app.cfg.acl_mapping:
            acls["before"] = "All:read"

        # create an empty output directory after deleting any existing directory
        click.echo(f"Creating output directory {html_root}, starting to copy supporting files")
        if html_root.exists():
            shutil.rmtree(html_root, ignore_errors=False)

        html_root.mkdir(parents=True)

        # create subdirectories and copy static css, icons, images into "static" subdirectory
        shutil.copytree(moinmoin / "static", html_root / "static")
        shutil.copytree(get_wiki_local_dir(), html_root / "+serve" / "wiki_local")

        # render script dictionary.js (i18n strings)
        with open(html_root / "static" / "js" / "dictionary.js", "wt", encoding="utf-8") as f:
            f.write(render_dictionary_js())

        # copy files from xstatic packaging into "+serve" subdirectory
        xstatic_dirs = ["font_awesome"]
        module_path_map = get_xstatic_module_path_map(xstatic_dirs)
        for xs_dir in xstatic_dirs:
            shutil.copytree(module_path_map[xs_dir], html_root / "+serve" / xs_dir)

        # copy directories for theme's static files
        if theme == "topside_cms":
            # topside_cms uses topside CSS files
            from_dir = moinmoin / "themes" / "topside" / "static"
        else:
            from_dir = moinmoin / "themes" / theme / "static"
        to_dir = html_root / "_themes" / theme
        shutil.copytree(from_dir, to_dir)

        # get ready to render and copy individual items
        names: list[tuple[str, str]] = []
        home_page: str | None = None
        get_dir = Path(html_root) / "+get"  # images and other raw data from wiki content
        get_dir.mkdir()

        if query:
            q = Regex(NAME_EXACT, query)
        else:
            q = Every()

        click.echo("Starting to dump items")

        # In the filesystem the item cannot have the same name as the directory.
        # so we append .html to the filename for items in used_dirs.
        for current_rev in current_app.storage.search(q, limit=None, sortedby=("namespace", "name")):

            if current_rev.namespace in excluded_namespaces:
                # we usually do not copy userprofiles, no one can login to a static wiki
                continue

            if not current_rev.name:
                # TODO: we skip nameless tickets, but named tickets and comments are processed with ugly names
                continue

            try:
                item_name = current_rev.fqname.fullname
                rendered = show_item(item_name, CURRENT)
            except Forbidden:
                click.echo(f"Failed to dump {current_rev.name}: Forbidden")
                continue
            except KeyError:
                click.echo(f"Failed to dump {current_rev.name}: KeyError")
                continue

            if not isinstance(rendered, str):
                click.echo(f"Rendering failed for {item_name} with response {rendered}")
                continue

            rendered = fixup_item_content(item_name, rendered, default_root=current_app.cfg.default_root)

            item = current_app.storage[current_rev.fqname.fullname]
            rev = item[CURRENT]

            file_name = Path(item_name)

            # copy raw data for all items to output /+get directory;
            # images are required, text items are of marginal/no benefit
            create_raw_data_file(get_dir / adjust_raw_filename_suffix(file_name), rev)

            # save rendered items or raw data to dump directory root
            if is_raw_data_content(item, file_name):
                # do not put a rendered html-formatted file with a name like video.mp4 into root;
                # browsers want raw data
                create_raw_data_file(Path(html_root) / file_name, rev)
            else:
                # extension ".html" is required for browsing html content
                if file_name.suffix != ".html":
                    file_name = add_path_suffix(file_name, ".html")
                create_html_file(Path(html_root) / file_name, rendered)

            # save item_name for the index generation
            names.append((item_name, str(file_name)))

            if current_rev.fqname.fullname == current_app.cfg.default_root:
                if convenience_duplicates:
                    # make duplicates of home page that are easy to find in directory list and open with a click
                    for target in [(current_rev.name + ".html"), ("_" + current_rev.name + ".html")]:
                        create_html_file(html_root / target, rendered)
                # save a copy for creation of index page
                home_page = rendered

        create_index_page(home_page, theme, names, html_root, current_app.cfg.default_root)

        logging.info("Dump html complete")


def add_path_suffix(path: Path, suffix: str):
    return path.parent / (path.name + suffix)


def is_raw_data_content(item: IndexedItem, filename: Path) -> bool:
    contenttype = item.meta[CONTENTTYPE].split(";")[0]
    return contenttype in (CONTENTTYPE_MEDIA + CONTENTTYPE_OTHER) and filename.suffix in (
        CONTENTTYPE_MEDIA_SUFFIX + CONTENTTYPE_OTHER_SUFFIX
    )


def adjust_raw_filename_suffix(filename: Path):
    """
    Add the suffix ".raw" to filename in case it doesn't have a dot suffix or the existing suffix
    does not belong to a media or other content type.
    """
    if filename.suffix in (CONTENTTYPE_MEDIA_SUFFIX + CONTENTTYPE_OTHER_SUFFIX):
        return filename
    else:
        return add_path_suffix(filename, ".raw")


def adjust_raw_url_suffix(url: str) -> str:
    """
    Add the suffix ".raw" to a raw content url in case it has no dot suffix or the existing suffix
    does not belong to a media or other content type.
    """
    try:
        suffix = "." + url.rsplit(".", 1)[1]
        if suffix in (CONTENTTYPE_MEDIA_SUFFIX + CONTENTTYPE_OTHER_SUFFIX):
            return url
    except IndexError:
        pass
    return url + ".raw"


def get_wiki_local_dir() -> Path:
    return Path(current_app.cfg.wiki_local_dir)


def is_raw_url(url: str):
    """
    Detect if url points to raw content item.
    """
    return url.startswith("/+get/")


def is_page_url(url: str):
    if url.startswith("#") or url.startswith("/+") or url.startswith("/_") or url.startswith("/static/"):
        return False
    parsed = urlparse(url)
    if parsed.scheme:
        return False
    return True


def fixup_page_link(m: re.Match) -> str:
    target = m.group(2)
    extra = ""
    if is_raw_url(target):
        filename = target.rsplit("/", 1)[-1]
        target = adjust_raw_url_suffix(target)
        extra = f' download="{filename}"'
    elif is_page_url(target):
        parsed = urlparse(target)
        target = parsed._replace(path=parsed.path + ".html").geturl()
    return f"{m.group(1)}{target}{m.group(3)}{extra}{m.group(4)}"


INVALID_SRC = re.compile(r' src="/\+get/\+[0-9a-f]{32}/')

INVALID_HREF = re.compile(r' href="/\+get/\+[0-9a-f]{32}/')

LINK_REGEX = re.compile(r"((?:href|src)\s*=\s*[\"\']?)([^\"\'\s>]+)([\"\'])(\s?)")


def fixup_item_content(item_name: str, rendered: str, /, default_root: str = "Home") -> str:

    # remove item ID from: href="/+get/+7cb364b8ca5d4b7e960a4927c99a2912/example.drawio"
    rendered = re.sub(INVALID_HREF, ' href="/+get/', rendered)

    # remove item ID from: src="/+get/+7cb364b8ca5d4b7e960a4927c99a2912/svg"
    rendered = re.sub(INVALID_SRC, ' src="/+get/', rendered)

    # make internal links target ".html" files
    rendered = re.sub(LINK_REGEX, fixup_page_link, rendered)

    # make hrefs relative to root folder
    rel_path2root = PARENT_DIR * len(re.findall("/", item_name))
    rendered = rendered.replace('href="/', 'href="' + rel_path2root)
    rendered = rendered.replace('src="/static/', f'src="{rel_path2root}static/')
    rendered = rendered.replace('src="/+get/', f'src="{rel_path2root}+get/')
    rendered = rendered.replace('src="/+serve/', f'src="{rel_path2root}+serve/')
    rendered = rendered.replace('src="/+template/dictionary.js', f'src="{rel_path2root}static/js/dictionary.js')
    rendered = rendered.replace('href="+index/"', 'href="+index"')  # trailing slash changes relative position

    # TODO: fix basic theme
    rendered = rendered.replace('<a href="">', f'<a href="{default_root}">')

    return rendered


def get_used_dirs(query) -> set[str]:
    """
    get a list of item_names which have subitems (nodes in a tree)
    """
    item = Item.create()  # gives toplevel index
    revs = flaskg.storage.search_meta(query, idx_name=LATEST_REVS, limit=None)
    dirs, files = item.make_flat_index(revs, True)
    # get intersection of dirs and files: items that have subitems
    used_dir_fullnames = {x.fullname for x in dirs} & {x.fullname for x in files}
    used_dirs = set()
    for file_ in used_dir_fullnames:
        if file_.namespace:
            used_dirs.add("/".join((file_.namespace, file_.value)))
        else:
            used_dirs.add(file_.value)
    logging.debug("used_dirs: %s", str(used_dirs))
    return used_dirs


def create_raw_data_file(filename: Path, rev: Revision) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "wb") as f:
        rev.data.seek(0)
        shutil.copyfileobj(rev.data, f)
        try:
            click.echo(f"Saved file named {filename} as raw data")
        except UnicodeEncodeError:
            safe_filename = str(filename).encode("ascii", errors="replace").decode()
            click.echo(f"Saved file named {safe_filename} as raw data")


def create_html_file(filename: Path, content: str) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "wb") as f:
        f.write(content.encode("utf8"))
        try:
            click.echo(f"Saved file named {filename}")
        except UnicodeEncodeError:
            safe_filename = str(filename).encode("ascii", errors="replace").decode()
            click.echo(f"Saved file named {safe_filename}")


def create_index_page(
    home_page: str, theme: str, names: list[tuple[str, str]], html_root: Path, wiki_root: str
) -> None:
    if not home_page:
        click.echo(
            'Error: index pages not created because no home page exists, expected an item named "{}".'.format(wiki_root)
        )
        return

    # create an index page by replacing the content of the home page with a list of items
    # work around differences in basic and modernized theme layout
    # TODO: this is likely to break as new themes are added
    if theme == "basic":
        start = '<div class="moin-content" role="main">'  # basic
        end = '<footer class="navbar moin-footer">'
        div_end = "</div>"
    else:
        start = '<div id="moin-content">'  # modernized , topside, topside cms
        end = '<footer id="moin-footer">'
        div_end = "</div></div>"

    # build a page named "+index" containing links to all wiki items
    links = []
    names.sort(key=lambda item: item[0])
    for name in names:
        links.append(f'<li><a href="{name[1]}">{name[0]}</a></li>')
    name_links = "<h1>Index</h1><ul>{0}</ul>".format("\n".join(links))

    try:
        part1 = home_page.split(start)[0]
        part2 = home_page.split(end)[1]
        page = part1 + start + name_links + div_end + end + part2
    except IndexError:
        page = home_page
        click.echo(f"Error: failed to find {end} in item named {wiki_root}")

    for target in ["+index", "index.html"]:
        with open(html_root / target, "wb") as f:
            f.write(page.encode("utf8"))


def render_dictionary_js() -> str:
    return render_template("dictionary.js")
