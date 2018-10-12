#!/usr/bin/env bash

cd ../docs/manual

# build the docs
make clean
make html

cd ../blog
make clean
make html

# switch branches and pull the data we want
git checkout gh-pages

# goto GIT root
cd $(git rev-parse --show-toplevel)
# remove tracked files
git ls-files -z | xargs -0 rm -f
mv ./docs/manual/_build/html/{.,}* ./

rm -rf blog
mkdir blog
mv ./docs/blog/_build/html/{.,}* ./blog

printf "tools/\ndocs/\npygears/\nexamples/\ntests/\ndeploy/\ndist/\n*.egg-info/\n" > .gitignore
printf "www.pygears.org" > CNAME

git add -A
git commit -m "publishing updated docs..."
git push origin gh-pages

# switch back
git checkout develop
