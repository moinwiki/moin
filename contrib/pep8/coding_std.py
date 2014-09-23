#!/usr/bin/env python
# Copyright: 2012-2014 by MoinMoin:RogerHaase
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Detect and correct violations of the moin2 coding standards:
    - no trailing blanks
    - exactly one linefeed at file end, see PEP8
    - DOS line endings on .bat and .cmd files, unix line endings everywhere else

Detect and write informative message:
    - improper indentation of template files ending with .html suffix

Execute this script from the root directory of the moin2 repository or
from anywhere within the contrib path to process all files in the repo.

Or, pass a directory path on the command line.
"""

import sys
import os


# file types to be processed
SELECTED_SUFFIXES = set("py bat cmd html css js styl less rst".split())

# stuff considered DOS/WIN
WIN_SUFFIXES = set("bat cmd".split())


class NoDupsLogger(object):
    """
    A simple report logger that suppresses duplicate headings and messages.
    """
    def __init__(self):
        self.messages = set()
        self.headings = set()

    def log(self, heading, message):
        if heading and heading not in self.headings:
            print u"\n%s" % heading
            self.headings.add(heading)

        if message and message not in self.messages:
            print u"   ", message
            self.messages.add(message)


def directories_to_ignore(starting_dir):
    """Return a list of directories that will not be processed."""
    # list format: [(fully qualified directory name, sub-directory name), ... ]
    ignore_dirs = []
    level2_dirs = ".hg contrib dlc env moin.egg-info wiki".split()
    for dir in level2_dirs:
        ignore_dirs.append((starting_dir, dir))
    ignore_dirs.append((starting_dir + os.sep + "MoinMoin", "translations"))
    ignore_dirs.append((starting_dir + os.sep + "docs", "_build"))
    return ignore_dirs


def calc_indentation(line):
    """
    Return tuple (length of indentation, line stripped of leading blanks).
    """
    stripped = line.lstrip(' ')
    indentation = len(line) - len(stripped)
    return indentation, stripped


def check_template_indentation(lines, filename, logger):
    """
    Identify non-standard indentation, print messages to assist user in manual correction.

    In simple cases, non-standard indent, non-standard dedent messages tells users which lines to indent.
    """
    indent_after = ('{% block ', '{% if ', '{% elif ', '{% else ', '{% for ', '{% macro ',
                    '{%- block ', '{%- if ', '{%- elif ', '{%- else ', '{%- for ', '{%- macro ', '{{ gen.form.open', )
    indent_before = ('{% endblock ', '{% endif ', '{% endfor ', '{% endmacro', '</',
                     '{%- endblock ', '{%- endif ', '{%- endfor ', '{%- endmacro', '{{ gen.form.close', )
    block_endings = {'{% block': ('{% endblock %}', '{%- endblock %}', '{%- endblock -%}', '{% endblock -%}', ),
                     '{% if': ('{% endif %}', '{%- endif %}', '{%- endif -%}', '{% endif -%}', ),
                     '{% elif': ('{% endif %}', '{%- endif %}', '{%- endif -%}', '{% endif -%}', ),
                     '{% else': ('{% endif %}', '{%- endif %}', '{%- endif -%}', '{% endif -%}', ),
                     '{% for': ('{% endfor %}', '{%- endfor %}', '{%- endfor -%}', '{% endfor -%}', ),
                     '{% macro': ('{% endmacro %}', '{%- endmacro %}', '{%- endmacro -%}', '{% endmacro -%}', ),
                     '{{ gen.form.open': ('{{ gen.form.close }}', ),
                    }
    ends = ('{% end', '{%- end')

    for idx, line in enumerate(lines):
        indentation, stripped = calc_indentation(line)

        if stripped.startswith(indent_after):
            # we have found the beginning of a block
            incre = 1
            try:
                while lines[idx + incre].strip() == '':
                    incre += 1
                next_indentation, next_line = calc_indentation(lines[idx + incre])
                if next_indentation <= indentation:
                    # next non-blank line does not have expected indentation
                    # truncate "{{ gen.form.open(form, ..." to "{{ gen.form.open"; "{%- if ..." to "{% if"
                    block_start = stripped.replace('-', '').split('(')[0].split(' ')
                    block_start = ' '.join(block_start[:2])
                    block_end = block_endings.get(block_start)
                    if not block_end:
                        # should never get here, mismatched indent_after and block_endings
                        logger.log(filename, u"Unexpected block type '%s' discovered at line %d!" % (block_start, idx + 1))
                        continue
                    if any(x in stripped for x in block_end):
                        # found line similar to: {% block ... %}...{% endblock %}
                        continue
                    if any(x in lines[idx + incre] for x in block_end):
                        # found 2 consecutive lines similar to: {% block....\n{% endblock %}
                        continue
                    logger.log(filename, u"Non-standard indent after line %d -- not fixed!" % (idx + 1))
            except IndexError:
                # should never get here, there is an unclosed block near end of template
                logger.log(filename, u"End of file reached with open block element at line %d!" % (idx + 1))

        elif stripped.startswith(indent_before):
            # we have found the end of a block
            decre = -1
            while idx + decre >= 0 and lines[idx + decre].strip() == '':
                decre -= 1
            if idx + decre < 0:
                # should never get here; file begins with something like {% endblock %} or </div>
                logger.log(filename, u"Beginning of file reached searching for block content at line %d!" % (idx + 1))
                continue
            prior_indentation, prior_line = calc_indentation(lines[idx + decre])
            if prior_indentation <= indentation:
                # prior non-blank line does not have expected indentation
                if stripped.startswith('</'):
                    tag_open = stripped.split('>')[0].replace('/', '')  # convert </div> to <div, etc.
                    if prior_line.startswith(tag_open):
                        # found lines similar to: <td>...\n</td>
                        continue
                if stripped.startswith(ends):
                    # convert {% endif %} to tuple ('{% if', '{%- if') or similar
                    block_open = (stripped.split(' %}')[0].replace('end', '').replace('-', ''),)
                    block_open += ((block_open[0].replace('{%', '{%-')), )
                    if prior_line.startswith(block_open):
                        # found lines similar to: {% block...\n{% endblock %}
                        continue
                logger.log(filename, u"Non-standard dedent before line %d -- not fixed!" % (idx + 1))


def check_files(filename, suffix):
    """
    Delete trailing blanks, single linefeed at file end, line ending to be \r\n for bat files and \n for all others.
    """
    suffix = suffix.lower()
    if suffix in WIN_SUFFIXES:
        line_end = "\r\n"
    else:
        line_end = "\n"
    logger = NoDupsLogger()

    with open(filename, "rb") as f:
        lines = f.readlines()

    if filename.endswith('.html'):
        check_template_indentation(lines, filename, logger)

    # now look at file end and get rid of all whitespace-only lines there:
    while lines:
        if not lines[-1].strip():
            del lines[-1]
            logger.log(filename, u"Empty lines at eof removed.")
        else:
            break

    with open(filename, "wb") as f:
        for idx, line in enumerate(lines):
            line_length = len(line)
            line = line.replace('\t', '    ')
            if len(line) != line_length:
                logger.log(filename, u"Tab characters replaced with 4 spaces.")
            pep8_line = line.rstrip() + line_end
            f.write(pep8_line)
            # if line was changed, issue warning once for each type of change
            if suffix in WIN_SUFFIXES and not line.endswith("\r\n"):
                logger.log(filename, u"Line endings changed to DOS style.")
            elif suffix not in WIN_SUFFIXES and line.endswith("\r\n"):
                logger.log(filename, u"Line endings changed to Unix style.")
            elif pep8_line != line:
                if len(pep8_line) < len(line):
                    logger.log(filename, u"Trailing blanks removed.")
                else:
                    logger.log(filename, u"End of line character added at end of file.")


def file_picker(starting_dir):
    """Select target files and pass each to file checker."""
    ignore_dirs = directories_to_ignore(starting_dir)

    for root, dirs, files in os.walk(starting_dir):
        # delete directories in ignore list
        for mama_dir, baby_dir in ignore_dirs:
            if mama_dir == root and baby_dir in dirs:
                dirs.remove(baby_dir)
        # check files with selected suffixes
        for file in files:
            suffix = file.split(".")[-1]
            if suffix in SELECTED_SUFFIXES:
                filename = os.path.join(root, file)
                check_files(filename, suffix)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        starting_dir = os.path.abspath(sys.argv[1])
    else:
        starting_dir = os.path.abspath(os.path.dirname(__file__))
        starting_dir = starting_dir.split(os.sep + 'contrib')[0]
    NoDupsLogger().log(u"Starting directory is %s" % starting_dir, None)
    file_picker(starting_dir)
