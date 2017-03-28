#!/bin/bash

# Global variables used:
#   PYTHON_VERSION          set in travis.yml
#   USE_QT_API              set in travis.yml
#   TRAVIS_BRANCH           set by travis
#   TRAVIS_PULL_REQUEST     set by travis
#   GH_TOKEN                decrypted secret from travis.yml

# Settings
REPO_PATH=github.com/Ulm-IQO/qudi.git
GENERATED_REPO_PATH=github.com/Ulm-IQO/qudi-generated-docs.git
IMAGE_REPO_PATH=github.com/Ulm-IQO/qudi-docs-images.git
HTML_PATH=${HOME}/docs/html
COMMIT_USER="Qudi Documentation Builder"
COMMIT_EMAIL="qudi@uni-ulm.de"
CHANGESET=$(git rev-parse --verify HEAD)
MY_BUILD_DIR=$(pwd)
DOXYGEN_VERSION="1.8.13"

# Build documentation only for one of the targets
if [[ ${BUILD_DOCS} != "True" ]]; then
    echo "Documentation is built only once."
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
#get images
git clone "https://${IMAGE_REPO_PATH}" ${MY_BUILD_DIR}/documentation/images

# get doxygen
cd $HOME
wget -O doxygen.tar.gz "http://ftp.stack.nl/pub/users/dimitri/doxygen-${DOXYGEN_VERSION}.linux.bin.tar.gz"
tar xzf doxygen.tar.gz
mv "${HOME}/doxygen-${DOXYGEN_VERSION}/bin/doxygen" ${HOME}/bin

if [[ $? -ne 0 ]]; then
    echo "Getting doxygen failed." >&2
    exit 1;
fi;

# Get a clean version of the HTML documentation repo.
rm -rf ${HTML_PATH} > /dev/null
mkdir -p ${HTML_PATH}
git clone "https://${GENERATED_REPO_PATH}" ${HTML_PATH}

if [[ $? -ne 0 ]]; then
    echo "generated docs clone failed!" >&2
    exit 1;
fi;

# rm all the files through git to prevent stale files.
cd ${HTML_PATH}
git rm -rf html-docs > /dev/null
git rm -rf doxygen-errors.txt > /dev/null
cd "${MY_BUILD_DIR}"

# Generate the HTML documentation.
doxygen documentation/doxyfile > /dev/null 2>${HTML_PATH}/doxygen-errors.txt
mv documentation/generated/html ${HTML_PATH}/html-docs

if [[ $? -ne 0 ]]; then
    echo "Documentation not present, something went wrong!" >&2
    exit 1;
fi;

mkdir -p  ${HTML_PATH}/html-docs/images
cp -r ${MY_BUILD_DIR}/documentation/images/* ${HTML_PATH}/html-docs/images/

if [[ $? -ne 0 ]]; then
    echo "Could not copy image folder,  somethign went wrong" >&2
    exit 1;
fi;

# Create and commit the documentation repo.
cd ${HTML_PATH}
git add . > /dev/null 2>&1
git config --global user.name "\"${COMMIT_USER}\""
git config --global user.email "\"${COMMIT_EMAIL}\""
git config --global push.default simple
git commit -m "Automated documentation build for changeset ${CHANGESET}."
# Redirect output to /dev/null here so the GH_TOKEN does not get leaked.
git push "https://${GH_TOKEN}@${GENERATED_REPO_PATH}" master > /dev/null 2>&1
cd "${MY_BUILD_DIR}"

