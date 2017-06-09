#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

conda env remove --yes --name qudi
conda env create -f "${DIR}/conda-env-linx64-qt5.yml"
