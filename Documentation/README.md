# Documentation system for Sparkle

Sparkle uses Sphinx to generate the documentation. The requirements are included in `../Documentation/requirments.txt`. LaTeX is also needed to build the `pdf` version of the documentation and userguide.

To install the requirements use pip (ideally in a virtual or conda environemnet)
```bash
pip install -r requirements.txt
```

To build the html documentation and the userguide (pdf).
```
make all
```

## Build the html documentation

To build the full html documentation
```bash
make html latexpdf
```
The resulting documentation is in `./build/html` with `./build/html/index.html` as the entry point.

The documentation can also be built in other formats, for example, `pdf` with 
```
make latexpdf
```

Consult the [Sphinx documentation](https://www.sphinx-doc.org) on how to use Sphinx.


## Build the pdf User Guide

A user guide is also available in the file `sparkle-userguide.pdf`. To generate the file, use  
```bash
make userguide
```

## Clean 

To clean up the generated files use
```bash
make clean
```
