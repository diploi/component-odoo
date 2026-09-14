FROM odoo:18.0-20260908

USER root

ARG UID=1000
ARG GID=1000

RUN set -eux; \
    if getent passwd ${UID} >/dev/null; then \
      existing_user="$(getent passwd ${UID} | cut -d: -f1)"; \
      if [ "${existing_user}" != "odoo" ]; then userdel "${existing_user}"; fi; \
    fi; \
    if getent group ${GID} >/dev/null; then \
      existing_group="$(getent group ${GID} | cut -d: -f1)"; \
      if [ "${existing_group}" != "odoo" ]; then groupdel "${existing_group}"; fi; \
    fi; \
    if [ "$(getent group odoo | cut -d: -f3)" != "${GID}" ]; then groupmod -g ${GID} odoo; fi; \
    if [ "$(id -u odoo)" != "${UID}" ] || [ "$(id -g odoo)" != "${GID}" ]; then usermod -u ${UID} -g ${GID} odoo; fi; \
    chown -R ${UID}:${GID} /var/lib/odoo /etc/odoo /mnt/extra-addons

USER ${UID}:${GID}
