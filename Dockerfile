FROM odoo:18.0-20260908

USER root

ARG UID=1000
ARG GID=1000

RUN set -eux; \
    if getent group  ${GID} >/dev/null; then groupdel "$(getent group  ${GID} | cut -d: -f1)"; fi; \
    if getent passwd ${UID} >/dev/null; then userdel  "$(getent passwd ${UID} | cut -d: -f1)"; fi; \
    groupmod -g ${GID} odoo; \
    usermod  -u ${UID} -g ${GID} odoo; \
    chown -R ${UID}:${GID} /var/lib/odoo /etc/odoo /mnt/extra-addons

USER ${UID}:${GID}
