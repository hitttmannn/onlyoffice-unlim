# onlyoffice-unlim — Simple Documents for Nextcloud

[Русский](README.ru.md) · **English** · [Installation guide](docs/INSTALL.en.md)

A small mobile-friendly DOCX/XLSX editor for Nextcloud, using the public
ONLYOFFICE desktop plugin API. It provides a separate **Simple Documents** app
(the current interface is in Russian), rather than the commercial ONLYOFFICE
mobile editor. The repository name does not imply verified unlimited connections.

## Current capabilities

- DOCX: read paragraphs, replace paragraph text and append a paragraph.
- XLSX: select a worksheet, edit cell values, insert/delete rows and columns.
- Document content zoom from 50% to 200%; browser pinch zoom is enabled where supported.
- Explicit save with confirmation from the Nextcloud file revision.
- Mobile DOCX/XLSX openings routed to the custom app for authorized users;
  desktop openings continue to use the normal ONLYOFFICE editor.
- Nextcloud Android Direct Editing routes to the app. A separate web login may
  be required. Android devices/WebViews can differ; validate your client.

## Limits and compatibility

| Component | Tested / required by installer |
| --- | --- |
| Nextcloud | 35; local integration tested on 35.0.2 |
| ONLYOFFICE connector | 10.2.1, enabled and configured with JWT |
| ONLYOFFICE Docs | Official Community 10.0.0-169, pinned Linux amd64 digest |
| Custom app | `onlyoffice_mobile` 0.2.0, experimental |

Installation is configurable for different hosts, paths, domains and `occ`
commands, including a Nextcloud container with host-accessible app storage.
**Other Nextcloud/connector versions are not verified**; the installer rejects
unsupported versions. This is not a universal compatibility claim.

Use copies of important files. Replacing a DOCX paragraph removes its inline
formatting and embedded objects. XLSX displays **A1:H20 of the selected sheet**;
this is not a full spreadsheet interface. The app lists files in the user's root
Files folder. Public links/guests, complex document workflows and full desktop
features are not supported. Restricted copy/download or read-only documents are
rejected. Access defaults to administrators; additional exact user IDs can be allowed.

The upstream Community mobile editor remains view-only. No proprietary mobile
addon is included, no connection-limit removal is claimed, and no project image
has been published to GHCR. Docker uses an official image by digest, not a full
source compilation. See [research](MOBILE-RESEARCH.md), [source audit](SOURCE-AUDIT.md)
and [validation](VALIDATION.md) for the scope of evidence.

## Installation and updates

Use the [English installation guide](docs/INSTALL.en.md) or
[Russian guide](docs/INSTALL.ru.md). Configure your own URLs, paths, ownership
and `occ` command in [mobile.example.json](deployment/mobile.example.json).
The portable installer leaves your original ONLYOFFICE endpoint, proxy and
containers unchanged. Existing Docs can be reused, or a separate pinned Docs
can be deployed with [compose.mobile.yaml](deployment/compose.mobile.yaml).

For UI-only updates on a portable installation:

```sh
git pull --ff-only
sudo python3 scripts/update-mobile-panel.py --ui-only --config private/mobile.json
```

This mode backs up the replaced UI files and does not run the global Nextcloud
upgrade. A full app-version upgrade requires separate review: `occ upgrade` can
also update other pending applications.

## Status, testing and project layout

The owner reports working deployment, mobile editing, saving, zoom and worksheet
selection. Local Docker/browser checks cover actual DOCX/XLSX saves through
Nextcloud, access rejection, CSRF rejection and mobile routing. This is not a
security audit or a guarantee against data loss. Restore on every supported
infrastructure has not been tested.

- `nextcloud-app/onlyoffice_mobile/`: Nextcloud app source.
- `prototype-mobile/plugin/`: plugin bridge source rendered for your origin.
- `scripts/install-mobile-app.py`: portable configuration/plugin/app installer.
- `deployment/compose.mobile.yaml`: optional independent Docs instance.
- `tests/`: installer and browser regression checks; see the installation guides.
- `prototype-mobile/`: earlier standalone test prototype, not the production backend.
- `deployment/NC-MOBILE-INSTALL.md`, `scripts/*nc*`, retirement/restore scripts:
  historical **owner-specific nc deployment**, not generic installation commands.

## License

The custom app/plugin code is AGPL-3.0-only; see [LICENSE](nextcloud-app/onlyoffice_mobile/LICENSE)
and [NOTICE](nextcloud-app/onlyoffice_mobile/NOTICE.md). Dependencies retain their
licenses. Keep notices and make corresponding modified source available as required
by the applicable licenses. The runtime/source correspondence and third-party
redistribution audit remain incomplete; the project does not redistribute a Docs
image. Never commit JWT secrets, passwords, private keys, backups or user documents.
