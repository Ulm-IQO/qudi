#!/bin/bash

# Global variables used:
#   PYTHON_VERSION          set in travis.yml
#   USE_QT_API              set in travis.yml
#   TRAVIS_BRANCH           set by travis
#   TRAVIS_PULL_REQUEST     set by travis
#   GH_TOKEN                decrypted secret from travis.yml

# Settings
REPO_PATH=github.com:Ulm-IQO/qudi.git
HTML_PATH=${HOME}/docs/html
COMMIT_USER="Qudi Documentation Builder"
COMMIT_EMAIL="qudi@uni-ulm.de"
CHANGESET=$(git rev-parse --verify HEAD)


# Build documentation only for one of the targets
if [[ ${PYTHON_VERSION} != 3.5 -o ${USE_QT_API} != PyQt5 ]]; then
    echo "Documentation is built only on Python 3.5 and Qt5."
    exit 0;
fi;

if [[ ${TRAVIS_BRANCH} != "master" ]]; then
    echo "Documentation is built only for the master branch."
    exit 0;
fi;

if [[ ${TRAVIS_PULL_REQUEST} != "false" ]]; then
    echo "Documentation is not built for pull requests."
    exit 0;
fi;

# Get a clean version of the HTML documentation repo.
rm -rf ${HTML_PATH}
mkdir -p ${HTML_PATH}
git clone -b gh-pages "${REPO_PATH}" --single-branch ${HTML_PATH}

# rm all the files through git to prevent stale files.
cd ${HTML_PATH}
git rm -rf .
cd -

# Generate the HTML documentation.
doxygen documentation/doxyfile
mv documentation/generated/html ${HTML_PATH}/html-docs

if [[ $? -ne 0 ]]; then
    echo "Documentation not present, something went wrong!" >&2
    exit 0;
fi;

# Create and commit the documentation repo.
cd ${HTML_PATH}
git add .
git config user.name "${COMMIT_USER}"
git config user.email "${COMMIT_EMAIL}"
git config --global push.default simple
git commit -m "Automated documentation build for changeset ${CHANGESET}."
# Redirect output to /dev/null here so the GH_TOKEN does not get leaked.
git push "https://${GH_TOKEN}@${REPO_PATH}" gh-pages > /dev/null 2>&1
cd -

