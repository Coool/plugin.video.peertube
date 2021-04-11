# Contribution Guidelines

Thank you for deciding to contribute to this project :)  
Please follow these guidelines when implementing your code.

[[_TOC_]]

## Change workflow

The `main` branch contains the latest version of the code. This branch must be
stable and working at any time. To ensure this CI pipelines are used.

The workflow is the following:
1. create a branch on the main repository with an explicit name
1. create a merge request from your branch against the `main` branch
1. a pipeline is created each time you push commits in a merge request but it
   will not start automatically: the user may start it. Since a merge request
   cannot be merged until the associated pipeline passed, start the `blocked
   pipeline` associated with the latest commit in your merge request when your
   change is ready.
1. if the pipeline passed, the merge request may be merged by one of the
   maintainers. Note that the preferred option is to squash commits.

Note: more information about the pipeline is available in the
[CI file](.gitlab-ci.yml).

## Coding style

The code is still based on the design of the alpha version so the coding style
is not mature yet.  
A redesign is planned but until then please:
* document the usage of functions following [Sphinx
  format](https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#python-signatures)
* follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) conventions. The
  compliance can be checked with [pylint](https://www.pylint.org/) and the
  following commands:

```python
python3 -m pip install -r misc/python_requirements.txt
python3 -m pylint --rcfile=misc/pylint-rcfile.txt
```

The pylint violations are also checked in the `quality` job.

More details are available in the [CI file](.gitlab-ci.yml).

Note: pylint is run with python3 to have latest features whereas the add-on
only supports Kodi v18 Leia (which uses python2)

## How to release a new version of this add-on

These steps should be followed only by maintainers.

1. Create a release branch whose name follows this format:
   `release/<release_name>`
2. On this branch don't commit any new feature. Only commit changes related to
   the release process like:
    - a bump of the add-on version in `addon.xml` (note that the version
      numbering must follow the [semantic versioning](https://semver.org/))
    - the update of the changelog in the `news` tag in `addon.xml` (using
      Markdown syntax since it will be re-used automatically in the release
      notes)
3. Merge the merge request (maintainers only)
4. A new pipeline with the job `create-release` will be created: run the job
   manually since it should be `blocked` (maintainers only)
5. The new release will be available on the releases page.
