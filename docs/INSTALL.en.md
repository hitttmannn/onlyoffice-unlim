# Install on your Nextcloud server

[Русский](INSTALL.ru.md) · [Project overview](../README.md)

These instructions use your own addresses and paths. They do not use the old
`nc-mobile-install.py` or retirement scripts: those belong to one historical
server and must not be run on another installation.

## 1. Requirements and backup

- Healthy Nextcloud **35**, enabled ONLYOFFICE connector **10.2.1** and configured
  JWT secret. Configure and test the official connector before this app.
- ONLYOFFICE Docs **10.0.0-169**. Other Docs versions are unverified; the portable
  installer checks Nextcloud/connector versions, not the remote Docs package.
- HTTPS for public Nextcloud and Docs URLs, with certificates trusted by the
  browser and the server. Docs must fetch Nextcloud files/callbacks; Nextcloud
  must reach Docs. WebSockets must pass through your reverse proxy.
- Root access on the host, Git and Python 3. Docker + Compose v2 if using the
  supplied Docs service. UI updates also use the host's PHP CLI for syntax checks.
- A host-visible writable Nextcloud app directory and its runtime owner's numeric
  UID/GID. `custom_apps` must be registered as writable in Nextcloud `apps_paths`.
  Immutable/managed deployments without writable app storage need a separate
  packaging integration; this installer does not cover them.

The optional Docs Compose starts with a 2 GiB memory limit, 3 GiB memory+swap
limit and one CPU. These are configurable starting values, not sizing guarantees.
Allow additional RAM for Nextcloud and other services, image storage, data and backups.
The pinned image is **Linux amd64**; an ARM source/image selection is not provided.

Before changing a running deployment, back up the Nextcloud database, `config`,
custom apps and user files with a consistent, tested method. Back up the existing
Docs configuration, image reference and volumes too. Docker image saving alone
is not a data backup. Do not delete the old Docs container or its volumes.

## 2. Clone and configure

Run on the host that can write the app and plugin paths:

```sh
git clone https://github.com/hitttmannn/onlyoffice-unlim.git
cd onlyoffice-unlim
install -d -m 700 private
cp deployment/mobile.example.json private/mobile.json
chmod 600 private/mobile.json
```

Edit `private/mobile.json` with a text editor. Replace **every example value**:

| Setting | Meaning |
| --- | --- |
| `nextcloud_url` | Public HTTPS base, including `/nextcloud` if installed in a subdirectory. Plugin messages use its origin only. |
| `docs_url` | Public HTTPS Docs base, including its proxy subpath if used. |
| `docs_internal_url` | Docs base reachable by Nextcloud PHP, used for force-save commands. |
| `app_dir` | Host path ending in `onlyoffice_mobile`, inside a writable registered app directory. Must not already exist. |
| `plugin_dir` | New absolute host directory for the rendered plugin. Must not already exist. |
| `occ_command` | JSON argument array, not a shell command. Must execute `occ` as the Nextcloud runtime user. |
| `owner_uid`, `owner_gid` | Numeric owner of app files as seen on this host. Defaults are 33/33; check your system. |
| `allowed_users` | Exact Nextcloud user IDs, e.g. `["alice", "bob"]`. Administrators are allowed automatically. |

Native Nextcloud example:

```json
"occ_command": ["sudo", "-u", "www-data", "php", "/var/www/nextcloud/occ"]
```

Container Nextcloud example (replace the container name and user ID):

```json
"occ_command": ["docker", "exec", "-u", "33", "nextcloud", "php", "/var/www/html/occ"]
```

For a container, `app_dir` must point to the **host side** of a persistent apps
bind mount, e.g. `/srv/nextcloud/custom_apps/onlyoffice_mobile`. That mount must
appear in the container's registered `apps_paths`. Paths inside a container are
not automatically host paths. Rootless Docker/user namespace mappings require
matching host UID/GID; do not assume 33/33. Network names such as `docs` work only
on a shared Docker network. `127.0.0.1` in PHP means the Nextcloud container itself.

```sh
python3 scripts/install-mobile-app.py check-config --config private/mobile.json
sudo python3 scripts/install-mobile-app.py render-plugin --config private/mobile.json
```

`check-config` validates syntax only. It does not check running services.
`render-plugin` writes the plugin for your Nextcloud origin and refuses overwrite.
Do not render it inside a private directory inaccessible to the Docs runtime.

## 3. Mount the plugin into Docs

### Reuse existing Docs (preferred when already configured)

Use the same Docs instance/URLs as your official connector, on the tested version.
Add this **persistent read-only mount** to its existing deployment definition:

```yaml
volumes:
  - /opt/onlyoffice-unlim/mobile-panel:/var/www/onlyoffice/documentserver/sdkjs-plugins/mobile-panel:ro
```

Replace the source with your `plugin_dir`. Preserve all existing mounts, JWT,
network and port settings. Recreate only the Docs service using its existing
Compose/orchestration definition during an agreed interruption. A `docker cp`
into a running container is not persistent across recreation.

### Optional separate Docs

Create `private/docs.env` with mode 600 in a text editor, using the **same JWT
secret/header as the configured Nextcloud connector**. Never paste it into chat
or commit it. Example keys (replace the secret before use):

```dotenv
JWT_SECRET='replace-with-the-existing-connector-secret'
JWT_HEADER=Authorization
MOBILE_PLUGIN_DIR=/opt/onlyoffice-unlim/mobile-panel
DOCS_BIND_IP=127.0.0.1
DOCS_PORT=18082
DOCS_MEMORY=2g
DOCS_MEMORY_SWAP=3g
DOCS_CPUS=1.0
```

```sh
chmod 600 private/docs.env
sudo docker compose -f deployment/compose.mobile.yaml --env-file private/docs.env config --quiet
sudo docker compose -f deployment/compose.mobile.yaml --env-file private/docs.env up -d
```

Use the same `-f` and `--env-file` arguments for subsequent Compose commands.
The new service has separate named volumes. The script does not switch the
original connector to it: only the custom app uses `docs_url/docs_internal_url`.
For automatic mobile routing the original connector must already work; desktop
openings remain on its configured Docs. A desktop migration is a separate task.

## 4. Configure your HTTPS proxy

For example, use `https://docs.example.com/` for Docs. Connect your HTTPS proxy
to `127.0.0.1:18082` when it runs on the same host. On other hosts/containers,
use a reachable protected address instead; do not expose the raw service publicly.

**Nginx**, inside your existing TLS `server` for the Docs hostname:

```nginx
location / {
    proxy_pass http://127.0.0.1:18082;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

**Apache**, inside your existing TLS virtual host for Docs, with `proxy`,
`proxy_http`, `headers` and a version supporting `upgrade=websocket`:

```apache
ProxyPreserveHost On
ProxyPass "/" "http://127.0.0.1:18082/" upgrade=websocket timeout=3600
ProxyPassReverse "/" "http://127.0.0.1:18082/"
RequestHeader set X-Forwarded-Proto "https"
```

These are forwarding snippets, not complete TLS/DNS/firewall configurations.
Validate your proxy configuration before reload. Subpath proxies require additional
path/forwarded-host handling; the old nc file is an example for that specific host,
not a portable template. Do not disable TLS verification or all SSRF checks to
work around a network error.

Verify using your **actual** public Docs base:

- `/healthcheck` responds `true`.
- `/web-apps/apps/api/documents/api.js` is JavaScript, not an HTML login/welcome page.
- `/sdkjs-plugins/mobile-panel/config.json` is the rendered plugin config.
- `/sdkjs-plugins/mobile-panel/bridge.html` and `bridge.js` load successfully.

## 5. Install and test the app

```sh
sudo python3 scripts/install-mobile-app.py install-app --config private/mobile.json
```

The script checks Nextcloud/connector state, copies only the custom app, sets its
four app settings and enables it. It does not edit the proxy, stop Docs, change
JWT or the official connector endpoints, or run a global `occ upgrade`. Existing
app directories cause a stop rather than an overwrite. If a run fails after files
were copied, inspect the error/logs and that directory; do not delete it blindly.

Open `<nextcloud_url>/index.php/apps/onlyoffice_mobile/`. Put DOCX/XLSX **copies**
in the root of your Files, test edit/save, close, reopen and download. Test a
multi-sheet workbook, zoom and the actual phone/Android app. Expect a separate web
login in a fresh Android WebView. Confirm unauthorized users cannot use the panel.
Mobile redirects apply only to authorized editable DOCX/XLSX, not public links,
other formats or desktop clients. Original connector permissions still apply.

The UI is currently Russian. Instructions are available in both languages.

## 6. Update, disable and roll back

For UI changes on an installed 0.2.0 app:

```sh
git pull --ff-only
sudo python3 scripts/update-mobile-panel.py --ui-only --config private/mobile.json
```

The old three UI files are saved under `private/mobile-ui-before-*`. Reload the
page. This mode does not change app versions or run `occ upgrade`. To undo it,
restore those files to their corresponding paths in `app_dir` with the original
owner and readable permissions. For code/version updates, read the release diff,
back up the app/settings, and follow version-specific migration instructions;
do not treat `--ui-only` as a full app upgrade.

Use **your configured `occ_command` prefix** followed by one of:

```text
config:app:set onlyoffice_mobile mobile_default --value=no
app:disable onlyoffice_mobile
```

The first disables automatic mobile routing; the second disables the entire app.
Because portable installation leaves the original connector unchanged, disabling
our app returns its original editor flow. Keep backups and any old Docs service.
Do not use `docker compose down -v`, `docker rm -v` or volume pruning for rollback.
Database/file disaster recovery depends on your own verified Nextcloud backup.

## Local development checks

From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/install-mobile-app.py scripts/update-mobile-panel.py
```

`tests/sheet-picker.cjs` uses Playwright and a locally installed Chromium/Brave;
set `PLAYWRIGHT_MODULE`/`BROWSER_PATH` if needed. `tests/mobile-zoom-routing.cjs`
requires the specific disposable local fixture at `127.0.0.1:18782`, `localadmin`
and `mobile-test.xlsx`; credentials come from `NC_TEST_ENV`. It is not a test to
run directly on production or evidence of compatibility with every Android client.
