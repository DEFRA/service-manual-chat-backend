#!/bin/bash

repository=$1
REPOSITORY_NAME=$(echo "${repository}" | awk -F'/' '{print $NF}')

find . -name .git -prune -o -name .github -prune -o -type f -exec sed -i "s/cdp-python-backend-template/${REPOSITORY_NAME}/g" {} \;
find . -name .git -prune -o -name .github -prune -o -type f -exec sed -i "s/CDP Python Backend Template/${REPOSITORY_NAME}/g" {} \;
