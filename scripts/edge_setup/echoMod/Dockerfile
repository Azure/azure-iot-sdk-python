FROM mcr.microsoft.com/mirror/docker/library/node:16
env DEBUG=rhea*,azure*
WORKDIR /sdk
COPY . /sdk
RUN npm install
ENTRYPOINT ["/usr/local/bin/node", "/sdk/app.js"]
