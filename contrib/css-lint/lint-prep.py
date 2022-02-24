"""
    Reads a variables.css file and a common.css (or theme.css) file, outputs a lint.css file
    similar to the common.css file but having all var(...) expressions replaced with the values
    within the variables.css file. The output file can then be submitted to a css validator.

    This program will be obsolete when a css lint program supports variables.
"""

variables_in = "../../src/moin/static/css/variables.css"
css_in = "../../src/moin/static/css/common.css"
# variables_in = "../../src/moin/themes/modernized/static/css/variables.css"
# css_in = "../../src/moin/themes/modernized/static/css/theme.css"
css_out = "/GIT/moin/contrib/css-lint/lint.css"


def parse_variables():
    """
    Return a dict after converting input lines like this:
        --primary: #000;  /* primary text color */
    into a dict entry like this:
        vars["var(--primary)"] = "#000"
    """
    vars = {}
    with open(variables_in) as f:
        lines = f.readlines()

    for line in lines:
        if "--" in line:
            name, val = line.split(":")
            val, rest = val.split(";")
            name = name.strip()
            val = val.strip()
            name = "var(%s)" % name
            vars[name] = val
    return vars


def create_lint(vars):
    """
    Read css file and replace variable names with values.
    """
    with open(css_in) as f:
        lines = f.readlines()

    with open(css_out, "w") as f:
        for line in lines:
            if "var(--" in line:
                for key, val in vars.items():
                    line = line.replace(key, val)
            f.write(line)


if __name__ == "__main__":
    vars = parse_variables()
    create_lint(vars)
    print("Done!")
