# Contribution Guidelines

Thank you for deciding to contribute to this project :)
Please follow these guidelines when implementing your code.

[[_TOC_]]

## Coding style

The code is still based on the design of the alpha version.  
A redesign is planned but until then please follow these rules:
* document the usage of functions following [Sphinx format](https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#python-signatures)

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
