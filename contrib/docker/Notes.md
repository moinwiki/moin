## Using Moin2 with the docker or podman container runtime

### Some notes

* the container uses the [hypercorn](https://hypercorn.readthedocs.io/en/latest/index.html) web server to run moin
* moin2 wheel files must reside in the subfolder `dist`
* the script `create_image.sh` searches for a wheel file in `dist` if none is provided as an argument
* test code and resources should be removed from the python package

### Download a Moin2 (beta) release from pypi

Visit <https://pypi.org/project/moin/#history> and check for the latest 2.x version!

Use curl to e.g. download moin release 2.0.0b5 into subfolder `dist`

    curl https://pypi.org/project/moin/2.0.0b5/moin-2.0.0b5-py3-none-any.whl --output-dir ./dist --create-dirs

### Create the Moin2 python package (wheel) from the git sources

    git clone https://github.com/moinwiki/moin.git
    cd moin

    /usr/bin/python3 quickinstall.py .venv
    . activate
    moin create-instance --full

    pip install build
    python -m build .

    deactivate

### Create a container image for Moin2 using docker

Create the docker image

    ./contrib/docker/create_image.sh --docker --wheel moin-2.0.0b5-py3-none-any.whl

Run moin2 with docker using the tcp port 8000

    docker run -it --rm --name moin2 -p 8000:8000 moin2

Make sure moin is working as expected by retrieving the wiki page `Home`

    curl -v http://127.0.0.1:8000/Home

### Create a container image for Moin2 using podman

Create the docker image

    ./contrib/docker/create_image.sh --podman

Run moin2 with podman using the tcp port 8000 and mounting the existing wiki subfolder

    podman run -it --rm --name moin2 -p 8000:8000 --user 1000:1000 -v ./wiki:/app/wiki --userns keep-id:uid=1000,gid=1000 moin2

Interactively run bash inside the moin2 container

    podman exec -it moin2 bash

### Adjusting the default wiki distribution

The main configuration file

    /app/wikiconfig.py

Template overrides

    /app/wiki/custom/

Custom themes

    /app/wiki/themes/

Adjusting the default wiki content

    /app/wiki/data

Log files

    /app/wiki/logs
