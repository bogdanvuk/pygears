#!/usr/bin/env bash

# build the docs
make clean
make html

# switch branches and pull the data we want
git checkout gh-pages

# goto GIT root
cd $(git rev-parse --show-toplevel)
echo "docs/\npygears\n" > .gitignore
# remove tracked files
git ls-files -z | xargs -0 rm -f
mv ./docs/manual/_build/html/* ./

git add -A
git commit -m "publishing updated docs..."
git push origin gh-pages

# switch back
git checkout develop
