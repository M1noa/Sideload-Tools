<div align="center">
  <h1><a href="https://m1noa.github.io/Sideload-Tools/">sideload tools</a></h1>
  an auto-merged altstore/esign app catalog from a bunch of sources. updated every 12 hours.

  <img alt="sources" src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fbadge-sources.json">
  <img alt="ipas" src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fbadge-ipas.json">
  <img alt="cached" src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fbadge-cached.json">
</div>

---

## direct links

urls to paste straight into your sideload app's "add source" box.

| catalog | url |
| --- | --- |
| **original links** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps-original-links-no-pal.json` |
| **original links (pal)** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps-original-links.json` |
| **cached** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps-no-pal.json` |
| **cached (pal)** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps.json` |

## two kinds of catalog

**original link catalogs** point right at the source urls. they work in every sideload app and don't depend on this repo's storage. if a source pulls an app, that link dies.

**cached catalogs** re-host the ipa, dylib, and deb files here in `files/`. they keep working even if the source goes offline. only catch: apps over 100mb might not get cached and fall back to the original link.

## normal vs pal

normal catalogs strip the altstore pal fields (`appID`, `marketplaceID`, `permissions`). use these unless you run a pal setup. they're the default and work in ksign, feather, sidestore, esign, and the rest.

**pal** catalogs keep those fields. only grab them if you actually need pal.

## catalog files

| file | description |
| --- | --- |
| [merged-apps-original-links-no-pal.json](./merged-apps-original-links-no-pal.json) | original source urls, no pal fields (recommended) |
| [merged-apps-original-links.json](./merged-apps-original-links.json) | original source urls, pal fields kept |
| [merged-apps-no-pal.json](./merged-apps-no-pal.json) | local repo urls for cached files, no pal fields (recommended) |
| [merged-apps.json](./merged-apps.json) | local repo urls for cached files, pal fields kept |
| [files/](./files/) | cached ipa, dylib, and deb files |

## add to your sideload app

all the one-tap "add source" buttons are on the **[sideload-tools pages site](https://m1noa.github.io/Sideload-Tools/)**. they don't show up in this readme. the site links the original-link catalogs (`merged-apps-original-links-no-pal.json` and `merged-apps-original-links.json`) since those work everywhere.

## how it works

1. grabs json from every url in `repos-sources.txt`
2. dedupes by `(name, bundleIdentifier, version)`
3. downloads all sideloadable files (ipa/dylib/deb) into `files/`
4. spits out four catalogs:
   - `merged-apps-original-links-no-pal.json`: original urls, no pal
   - `merged-apps-original-links.json`: original urls, pal kept
   - `merged-apps-no-pal.json`: local urls for cached files, no pal
   - `merged-apps.json`: local urls for cached files, pal kept
5. sorts newest to oldest by version date
6. tracks download status, hashes, and dupes in `apps-tracking.json`

runs on a github action every 12 hours.
