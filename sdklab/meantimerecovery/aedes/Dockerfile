FROM mcr.microsoft.com/mirror/docker/library/node:18-bullseye-slim

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 8883

CMD [ "node", "./aedes_server.js" ]
