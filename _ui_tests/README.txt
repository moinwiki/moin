Functional tests
================

Summary
=======

This directory contains functional tests, which directly test the ui, without
needing access to the underlying code.

These tests use selenium.

Licensing issues
----------------

The selenium license is apache 2.0.  MoinMoin license is "GPL v2 or later".  
GPL v2 license is currently considered by some to be incompatible with apache 
2 license. GPL v3 is currently considered by many to be ok for use in 
conjunction with apache 2 license.

By separating the functional tests from the unit tests, we avoid having to 
import selenium and MoinMoin in the same python runtime, which
means that there should not be any licensing issues.

Everything in this 'tests/functional' folder should be licensed "GPL v3 or 
later", and not link to anything GPL v2.  Specifically, these tests should 
not link with MoinMoin itself.

Pre-requisites
--------------

- have activated the MoinMoin environment:
      source env/bin/activate
- have installed selenium:
      pip install selenium
- have installed firefox

Instructions
------------

1. Open a terminal
2. Change into the directory of this README
3. Execute 'py.test -v -s'

If any tests fail, screenshots will be generated in the current directory 
with names corresponding to the test class name and method name.

To run in the background
------------------------

Pre-requisite:
- have installed xfvb

1. Open a terminal
2. Change into the directory of this README
3. Execute 'xfvb-run py.test -v -s'

Configuration
-------------

configuration is in 'config.py'.  You can define where your MoinMoin 
installation is running, ie which URL.

