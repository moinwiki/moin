# Contributing to MoinMoin

Thank you for your interest in contributing to MoinMoin! We welcome contributions
and appreciate your support in improving this project. This guide outlines how
you can contribute, whether through bug reports, code contributions, or help with
documentation.


## How to Contribute

Find out how you can start reporting bugs, fixing bugs, adding new features, or
improving the documentation.

### Reporting Bugs

If you've encountered a bug, please report it by following these steps:

 1. Search the issue tracker to see if the bug has already been reported.
 2. Open a new issue in GitHub if it has not been reported yet.
 3. Provide as much detail as possible, including:
  - A description of the bug
  - Steps to reproduce the issue
  - Any relevant logs or error messages.

### Suggesting Enhancements

If you have an idea for a new feature or improvement:

 1. Check the issue tracker to see if the enhancement has already been suggested.
 2. Open a new issue with a detailed description of the suggested enhancement.
 3. Include a rough idea of how the enhancement could be implemented if possible.

### Submitting Code or Documentation Enhancements

To submit code or documentation updates, follow these steps:

 * Set up your development environment; see the next chapter.
 * Create a new branch for your changes:
   ```
   git checkout -b feature-branch
   ```
 * Implement your changes locally.
 * Run tests and ensure everything works before submitting your changes.
 * Commit your changes and push them to your fork on GitHub:
   ```
   git commit -am "Description of changes"
   git push --set-upstream origin feature-branch
   ```
 * Create a pull request against the master MoinMoin repository.

We encourage you to split complex changes into smaller, focused pull requests.
This makes it easier to review and merge your contributions.

## Development Setup

To begin contributing, you need to set up your development environment. Follow
the steps below to get started:

 * Fork the main Moin repository on GitHub.
 * Clone your fork (repository) to your local development system.
 * Create a virtual environment and install the required Python packages.
 * Activate the virtual environment.
 * Create a wiki instance with help data and a welcome page.
 * Start the built-in server.

For details on setting up your environment, please refer to the MoinMoin
development documentation at
[moin-20.readthedocs.io](https://moin-20.readthedocs.io/en/latest/devel/development.html#create-your-development-environment)


## Code Style and Best Practices

MoinMoin follows common coding standards to ensure the consistency of the
codebase. Here are some major things to keep in mind:

 * Python Version: MoinMoin is based on Python 3. Make sure your changes work
   with the versions specified in pyproject.toml.
 * Code Formatting: Follow PEP 8 standards for Python code.
 * Testing: Write tests for your changes to ensure stability. Tests should be
   added under the corresponding _tests directory.
 * Documentation: Ensure that your changes are well-documented. Add docstrings
   to your functions and classes where appropriate.

We use Git pre-commit hooks to help ensure consistent code quality.
The checks include the tools Black, Ruff, and Bandit. For details, please see
[moin-20.readthedocs.io](https://moin-20.readthedocs.io/en/latest/devel/development.html#install-pre-commit-hooks)


## Licensing

By submitting code to MoinMoin, you agree that your contributions are licensed
under the GNU General Public License, the license used by the MoinMoin project.

We appreciate your contributions to MoinMoin! If you have any questions that
are not covered in the docs, feel free to ask.
