# A pinned upstream runtime wrapper; NOT a compilation from source.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG SOURCE_URL
LABEL org.opencontainers.image.title="onlyoffice-unlim" \
      org.opencontainers.image.description="Unverified capabilities; upstream runtime preserved" \
      org.opencontainers.image.source="${SOURCE_URL}"
