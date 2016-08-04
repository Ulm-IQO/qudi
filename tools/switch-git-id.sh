#!/bin/bash
#echo $1
#echo $2

git config --global user.name "$1"
git config --global user.email "$2"
git config --global core.autocrlf true
