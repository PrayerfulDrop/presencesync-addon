# Thin wrapper around dadoum/anisette-v3-server.
# We don't add anything — it's reused as-is — but the HA Supervisor needs a
# Dockerfile in the add-on directory so it knows how to build/pull the image.
ARG BUILD_FROM=dadoum/anisette-v3-server:latest
FROM ${BUILD_FROM}

# The upstream image already runs anisette-server on 0.0.0.0:6969 by default.
# No additional CMD/ENTRYPOINT changes needed.
