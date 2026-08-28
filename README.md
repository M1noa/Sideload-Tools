# Sideload-Tools

Auto-merged AltStore/ESign app catalog from multiple sources. Updated every 12 hours.

## Direct Links

Plain URLs — paste into your sideload app's "add source" box.

| Catalog | URL |
| --- | --- |
| **Original Links (Recommended ★)** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps-original-links.json` |
| **Original Links — No PAL (Recommended for non-PAL apps)** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps-original-links-no-pal.json` |
| **Merged (cached)** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps.json` |
| **Merged — No PAL** | `https://raw.githubusercontent.com/M1noa/Sideload-Tools/main/merged-apps-no-pal.json` |

## Catalogs

| File | Description |
| --- | --- |
| [merged-apps-original-links.json](./merged-apps-original-links.json) | All original source URLs preserved (Recommended) |
| [merged-apps-original-links-no-pal.json](./merged-apps-original-links-no-pal.json) | Original URLs, AltStore PAL fields stripped (Recommended for non-PAL apps) |
| [merged-apps.json](./merged-apps.json) | Merged catalog with local repo download URLs for cached/archived files |
| [merged-apps-no-pal.json](./merged-apps-no-pal.json) | Like `merged-apps.json` but with AltStore PAL fields stripped (better compatibility) |
| [files/](./files/) | Cached IPA, dylib, and deb files |

## Add to Your Sideload App

All the one-tap "add source" buttons now live on the **[Sideload-Tools Pages site](https://m1noa.github.io/Sideload-Tools/)** — they don't render inline in this README. The site only links the original-source catalogs (`merged-apps-original-links.json` and `merged-apps-original-links-no-pal.json`), since those work in every sideload app.

<!--
### AltStore

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_AltStore-007AFF?style=for-the-badge)](altstore://source?URL=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-007AFF?style=for-the-badge)](altstore://source?URL=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |

### AltStore Classic

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_AltStore_Classic-5856D6?style=for-the-badge)](altstore-classic://source?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-5856D6?style=for-the-badge)](altstore-classic://source?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |

### SideStore

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_SideStore-5856D6?style=for-the-badge)](sidestore://source?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-5856D6?style=for-the-badge)](sidestore://source?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |

### ESign

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_ESign-FF9500?style=for-the-badge)](esign://addsource?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-FF9500?style=for-the-badge)](esign://addsource?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |

### Feather

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_Feather-FF2D55?style=for-the-badge)](feather://source/https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-FF2D55?style=for-the-badge)](feather://source/https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |

### KSign

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_KSign-34C759?style=for-the-badge)](ksign://source/https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-34C759?style=for-the-badge)](ksign://source/https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |

### TrollApps

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_TrollApps-8E8E93?style=for-the-badge)](trollapps://add?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-8E8E93?style=for-the-badge)](trollapps://add?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |

### Scarlet

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_Scarlet-FF3B30?style=for-the-badge)](scarlet://source=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-FF3B30?style=for-the-badge)](scarlet://source=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |

### StikStore

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_StikStore-FF6482?style=for-the-badge)](stikstore://add-source?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-FF6482?style=for-the-badge)](stikstore://add-source?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |

### LiveContainer

| Catalog | Link |
| --- | --- |
| **Merged (cached)** | [![Add](https://img.shields.io/badge/Add_to_LiveContainer-00C7BE?style=for-the-badge)](livecontainer://source?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps.json) |
| **Original Links ★** | [![Add](https://img.shields.io/badge/★_Recommended_Original-00C7BE?style=for-the-badge)](livecontainer://source?url=https%3A%2F%2Fraw.githubusercontent.com%2FM1noa%2FSideload-Tools%2Fmain%2Fmerged-apps-original-links.json) |
-->

## How It Works

1. Fetches JSON from every URL in `repos-sources.txt`
2. Deduplicates by `(name, bundleIdentifier, version)`
3. Downloads all sideloadable files (ipa/dylib/deb) into `files/`
4. Emits four catalogs:
   - `merged-apps.json` — local repo download URLs for cached/archived files
   - `merged-apps-original-links.json` — original source URLs preserved
   - `merged-apps-no-pal.json` / `merged-apps-original-links-no-pal.json` — same, with AltStore PAL fields stripped for non-PAL apps
5. Sorts newest → oldest by version date
6. Tracks download status, hashes, and duplicates in `apps-tracking.json`

Runs via GitHub Action every 12 hours.
