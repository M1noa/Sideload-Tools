# [Sideload-Tools](https://m1noa.github.io/Sideload-Tools/)

Auto-merged AltStore/ESign app catalog from multiple sources. Updated every 12 hours.

## Direct Links

Plain URLs to paste into your sideload app's "add source" box. The normal catalogs are listed first.

| Catalog | URL |
| --- | --- |
| **Original Links** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps-original-links-no-pal.json` |
| **Original Links (PAL)** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps-original-links.json` |
| **Cached** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps-no-pal.json` |
| **Cached (PAL)** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps.json` |

## Two kinds of catalog

**Original Link catalogs** point straight at the upstream source URLs. They work in every sideload app and never depend on this repo's storage. If an upstream source removes an app, that link stops working.

**Cached catalogs** re-host the IPA, dylib, and deb files inside this repo (the `files/` folder). They keep working even if the original source goes offline. They depend on this repo staying under GitHub's size limits, so very large apps (over 100 MB) may not be cached and will fall back to their original link.

## Normal vs PAL

The normal catalogs strip AltStore PAL fields (`appID`, `marketplaceID`, `permissions`). Use these unless you run an AltStore PAL setup. They are the recommended default and work in KSign, Feather, SideStore, ESign, and every other sideload app.

The **PAL** catalogs keep those fields for AltStore PAL sources. Pick PAL only if you actually need it.

## Catalog Files

| File | Description |
| --- | --- |
| [merged-apps-original-links-no-pal.json](./merged-apps-original-links-no-pal.json) | Original source URLs, PAL fields stripped (recommended) |
| [merged-apps-original-links.json](./merged-apps-original-links.json) | Original source URLs, PAL fields kept |
| [merged-apps-no-pal.json](./merged-apps-no-pal.json) | Local repo download URLs for cached files, PAL fields stripped (recommended) |
| [merged-apps.json](./merged-apps.json) | Local repo download URLs for cached files, PAL fields kept |
| [files/](./files/) | Cached IPA, dylib, and deb files |

## Add to Your Sideload App

All the one-tap "add source" buttons live on the **[Sideload-Tools Pages site](https://m1noa.github.io/Sideload-Tools/)**. They don't render inline in this README. The site links the original-link catalogs (`merged-apps-original-links-no-pal.json` and `merged-apps-original-links.json`), since those work in every sideload app.

## How It Works

1. Fetches JSON from every URL in `repos-sources.txt`
2. Deduplicates by `(name, bundleIdentifier, version)`
3. Downloads all sideloadable files (ipa/dylib/deb) into `files/`
4. Emits four catalogs:
   - `merged-apps-original-links-no-pal.json`: original source URLs, PAL fields stripped
   - `merged-apps-original-links.json`: original source URLs, PAL fields kept
   - `merged-apps-no-pal.json`: local repo download URLs for cached files, PAL fields stripped
   - `merged-apps.json`: local repo download URLs for cached files, PAL fields kept
5. Sorts newest to oldest by version date
6. Tracks download status, hashes, and duplicates in `apps-tracking.json`

Runs via GitHub Action every 12 hours.
