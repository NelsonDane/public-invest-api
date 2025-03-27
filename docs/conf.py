import os
import sys

sys.path.insert(0, os.path.abspath("../public_invest_api"))

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "public_invest_api"
copyright = "2025, Nelson Dane"
author = "Nelson Dane"
html_title = "Public Invest API Docs"
html_short_title = "Public API Docs"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
    "sphinx.ext.autosectionlabel",
    "sphinx_new_tab_link",
]
napoleon_google_docstring = True

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"


def hide_non_private(app, what, name, obj, skip, options):
    # if private-members is set, show only private members
    if name == "Public":
        return None
    if (
        "private-members" in options
        and not name.startswith("_")
        and not name.endswith("__")
    ):
        print(f"Skipping {name}")
        # skip public methods
        return True
    else:
        # do not modify skip - private methods will be shown
        print(f"Showing {name}")
        return None


def setup(app):
    app.connect("autodoc-skip-member", hide_non_private)
