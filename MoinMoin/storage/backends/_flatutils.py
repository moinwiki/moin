"""
    MoinMoin - helpers for flatfile meta/data stores

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""


def split_body(body):
    """ Extract the processing instructions / acl / etc. at the beginning of a page's body.

        Hint: if you have a Page object p, you already have the result of this function in
              p.meta and (even better) parsed/processed stuff in p.pi.

        Returns a list of (pi, restofline) tuples and a string with the rest of the body.
    """
    pi = {}
    while body.startswith('#'):
        try:
            line, body = body.split('\n', 1) # extract first line
            line = line.rstrip('\r')
        except ValueError:
            line = body
            body = ''

        # end parsing on empty (invalid) PI
        if line == "#":
            body = line + '\n' + body
            break

        if line[1] == '#':# two hash marks are a comment
            comment = line[2:]
            if not comment.startswith(' '):
                # we don't require a blank after the ##, so we put one there
                comment = ' ' + comment
                line = '##%s' % comment

        verb, args = (line[1:] + ' ').split(' ', 1) # split at the first blank
        pi.setdefault(verb.lower(), []).append(args.strip())

    for key, value in pi.iteritems():
        if key in ['#', ]:
            # transform the lists to tuples:
            pi[key] = tuple(value)
        elif key in ['acl', ]:
            # join the list of values to a single value
            pi[key] = u' '.join(value)
        else:
            # for keys that can't occur multiple times, don't use a list:
            pi[key] = value[-1] # use the last value to copy 1.9 parsing behaviour

    return pi, body


def add_metadata_to_body(metadata, data):
    """
    Adds the processing instructions to the data.
    """
    from MoinMoin.items import NAME, ACL, MIMETYPE, LANGUAGE

    meta_keys = [NAME, ACL, MIMETYPE, LANGUAGE, ]

    metadata_data = ""
    for key, value in metadata.iteritems():
        if key not in meta_keys:
            continue
        # special handling for list metadata
        if isinstance(value, (list, tuple)):
            for line in value:
                metadata_data += "#%s %s\n" % (key, line)
        else:
            metadata_data += "#%s %s\n" % (key, value)
    return metadata_data + data

