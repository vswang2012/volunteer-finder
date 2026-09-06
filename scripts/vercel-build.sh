#!/bin/sh
# Assemble the deployable static site into public/.
#
# There is nothing to compile. The Python in this repo is build tooling that
# runs in GitHub Actions once a week; it never runs on the host. All the host
# has to serve is one HTML file and one JSON file.
#
# The layout below is deliberate. Vercel serves outputDirectory as the web
# root, so index.html lands at "/" and the data at "/data/". The page fetches
# "../data/opportunities.json", which resolves to "/data/opportunities.json"
# both here (browsers clamp a leading ".." at the root, per RFC 3986
# remove_dot_segments) and in local dev, where the page is served from
# "/site/". One relative path, two layouts, no build-time rewriting.
set -eu

rm -rf public
mkdir -p public/data
cp site/index.html public/index.html
cp data/opportunities.json public/data/opportunities.json

echo "built public/:"
find public -type f | sort
