<img alt="icon" src=".diploi/icon.svg" width="32">

# Odoo Component for Diploi

[![launch with diploi badge](https://diploi.com/launch.svg)](https://diploi.com/component/odoo)
[![component on diploi badge](https://diploi.com/component.svg)](https://diploi.com/component/odoo)
[![latest tag badge](https://badgen.net/github/tag/diploi/component-odoo)](https://diploi.com/component/odoo)

Launch a trial, no registration needed
https://diploi.com/component/odoo

Uses the official [odoo](https://hub.docker.com/_/odoo) Docker image (Odoo 18).

Requires **PostgreSQL**, which is included as a Diploi add-on.

## Operation

### Getting started

1. **Sign up** at `https://console.diploi.com/` using your GitHub account.
2. In your dashboard, click **Create Project +**
3. Under **Pick Components**, choose **Odoo**
   If you want to expand your stack with other tools, like a frontend or API, here you can add them.
4. In **Pick Add-ons**, PostgreSQL is required and selected by default. You can add other databases or tools supported on Diploi.
5. In **Repository**, choose **Create Repository** which will generate a new GitHub repo for you.
6. Click **Launch Stack**

### Login

Log in to Odoo with user `admin`. An initial password is generated for every project (`INITIAL_ADMIN_PASSWORD`). Find it in the Diploi deployment **Options** tab.

The same value is also used as Odoo's master password (`admin_passwd`) for the database manager.

### Initialization

On first start, an init container running the Odoo image:

1. Waits for PostgreSQL, then creates the Odoo database role and database if they do not exist.
2. Writes a default `odoo.conf` into persistent storage if one is not already present.
3. Initializes the Odoo database (`odoo --init=base --stop-after-init`) if it has not been initialized yet.
4. Sets the `admin` user password to `INITIAL_ADMIN_PASSWORD`.

Initialization is recorded in a `diploi_parameters` table, so later restarts skip the first-time setup.

The init script lives in the component helm files (`.diploi/helm/app-init-configmap.yaml`), so it is updated with the component rather than being frozen in the user project.

### Storage

| Path                | Volume              | Description                                                                                             |
| ------------------- | ------------------- | ------------------------------------------------------------------------------------------------------- |
| `/var/lib/odoo`     | `data`              | Odoo filestore and sessions. Persisted in all stages.                                                   |
| `/etc/odoo`         | `data` (`etc-odoo`) | Persistent `odoo.conf`. Mounted from the data volume so config survives pod restarts and image updates. |
| `/mnt/extra-addons` | `extra-addons`      | Custom Odoo modules.                                                                                    |
| `/home/odoo`        | `home`              | Home directory for the `odoo` user.                                                                     |

The default config sets `addons_path = /mnt/extra-addons`, `data_dir = /var/lib/odoo`, `proxy_mode = True`, and the PostgreSQL connection settings.

### Environment variables

| Variable                 | Description                                                                     |
| ------------------------ | ------------------------------------------------------------------------------- |
| `INITIAL_ADMIN_PASSWORD` | Initial `admin` login password and Odoo master password. Generated per project. |
| `DATABASE`               | PostgreSQL database name. Default `odoo`.                                       |
| `USER`                   | PostgreSQL role used by Odoo. Default `odoo`.                                   |
| `PASSWORD`               | Password for the Odoo PostgreSQL role. Generated per project.                   |

PostgreSQL connection details (`HOST`, `PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) come from the PostgreSQL add-on.

### Development

The development container runs as user `odoo` (`1000:1000`). Custom modules can be added under `/mnt/extra-addons`.

The start command can be changed with the `containerCommands.developmentStart` field in `diploi.yaml`.

### Production

Builds a production-ready image from the official Odoo image. When the container starts, it uses the persistent `odoo.conf` created during initialization.

The start command can be changed with the `containerCommands.productionStart` field in `diploi.yaml`.

## Links

- [Adding Odoo to a project](https://docs.diploi.com/building/components/odoo)
- [Odoo documentation](https://www.odoo.com/documentation/18.0/)
