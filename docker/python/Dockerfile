FROM python:3.8.3-slim as base
#
#  USAGE:
#     cd services/osparc-python-runner
#     docker build -f Dockerfile -t osparc-python-runner:prod --target production ../../
#     docker run osparc-python-runner:prod
#

LABEL maintainer=sanderegg

ENV SC_USER_ID 8004
ENV SC_USER_NAME scu

RUN adduser \
    --uid ${SC_USER_ID} \
    --disabled-password \
    --gecos "" \
    --shell /bin/sh --home /home/${SC_USER_NAME} ${SC_USER_NAME}

RUN apt-get update \
    && apt-get -y install --no-install-recommends \
    jq \
    && rm --recursive --force /var/lib/apt/lists/*

# -------------------------- Build stage -------------------
# Installs build/package management tools and third party dependencies
#
# + /build             WORKDIR
#

FROM base as build

ENV SC_BUILD_TARGET build

WORKDIR /build

# defines the output of the build
RUN mkdir --parents /build/bin

# copy src code
COPY --chown=${SC_USER_NAME}:${SC_USER_NAME} src/osparc_python_runner src/osparc_python_runner

# uncomment and adapt if build steps are necessary
RUN cp -R src/osparc_python_runner/* /build/bin



# --------------------------Production stage -------------------
# Final cleanup up to reduce image size and startup setup
# Runs as ${SC_USER_NAME} (non-root user)
#
#  + /home/${SC_USER_NAME}     $HOME = WORKDIR
#    + osparc_python_runner [${SC_USER_NAME}:${SC_USER_NAME}]
#    + docker [${SC_USER_NAME}:${SC_USER_NAME}]
#    + service.cli [${SC_USER_NAME}:${SC_USER_NAME}]
#
FROM base as production

ENV SC_BUILD_TARGET production
ENV SC_BOOT_MODE production
ENV INPUT_FOLDER="/input" \
    OUTPUT_FOLDER="/output"
ENV PATH="/home/${SC_USER_NAME}/service.cli:${PATH}"

WORKDIR /home/${SC_USER_NAME}

# copy docker bootup scripts
COPY --chown=${SC_USER_NAME}:${SC_USER_NAME} docker/python/*.sh docker/

# copy simcore service cli
COPY --chown=${SC_USER_NAME}:${SC_USER_NAME} service.cli/ service.cli/

# copy binaries from build
COPY --from=build --chown=${SC_USER_NAME}:${SC_USER_NAME} /build/bin osparc_python_runner

RUN pip install -r osparc_python_runner/requirements.txt


ENTRYPOINT [ "/bin/sh", "docker/entrypoint.sh", "/bin/sh", "-c" ]
CMD ["run"]
