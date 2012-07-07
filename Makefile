#
# Makefile for MoinMoin
#

# location for the wikiconfig.py we use for testing:
export PYTHONPATH=$(PWD)

all:
	python setup.py build

test:
	py.test --pep8 -rs

dist: clean-devwiki
	-rm MANIFEST
	python setup.py sdist

docs:
	make -C docs html

# this needs the sphinx-autopackage script in the toplevel dir:
apidoc:
	sphinx-apidoc -f -o docs/devel/api MoinMoin

interwiki:
	wget -U MoinMoin/Makefile -O contrib/interwiki/intermap.txt "http://master19.moinmo.in/InterWikiMap?action=raw"
	chmod 664 contrib/interwiki/intermap.txt

pylint:
	@pylint --disable-msg=W0142,W0511,W0612,W0613,C0103,C0111,C0302,C0321,C0322 --disable-msg-cat=R MoinMoin

clean: clean-devwiki clean-pyc clean-orig clean-rej
	-rm -rf build

clean-devwiki:
	-rm -rf wiki/data/content
	-rm -rf wiki/data/userprofiles
	-rm -rf wiki/index

clean-pyc:
	find . -name "*.pyc" -exec rm -rf "{}" \; 

clean-orig:
	find . -name "*.orig" -exec rm -rf "{}" \; 

clean-rej:
	find . -name "*.rej" -exec rm -rf "{}" \; 

.PHONY: all dist docs interwiki check-tabs pylint \
	clean clean-devwiki clean-pyc clean-orig clean-rej

