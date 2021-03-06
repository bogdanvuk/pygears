#!/usr/bin/env bash
shopt -s extglob

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
read -p "Are you sure you want to clear the directory $PWD? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    rm -rf !("docs"|".git")
fi
# remove tracked files
mv ./docs/manual/_build/html/{.,}* ./

rm -rf blog
mkdir blog
mv ./docs/blog/_build/html/{.,}* ./blog

gitignore="tools/
docs/
pygears/
examples/
tests/
deploy/
dist/
*.egg-info/
"
robots="# www.robotstxt.org/

# Allow crawling of all content
User-agent: *
Disallow:
Sitemap: https://www.pygears.org/sitemap.xml
Sitemap: https://www.pygears.org/blog/sitemap.xml
"

printf "$gitignore" > .gitignore
printf "www.pygears.org" > CNAME
printf "$robots" > robots.txt

git add -A
git commit -m "publishing updated docs..."
git push origin gh-pages

# switch back
git checkout master
