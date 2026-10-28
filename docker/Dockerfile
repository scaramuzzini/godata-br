# Go.Data (WHO) built from source: Angular frontend + LoopBack API
FROM node:16-bullseye AS frontend
WORKDIR /src
COPY vendor/GoDataSource-FrontEnd/package*.json ./
RUN npm ci --legacy-peer-deps
COPY vendor/GoDataSource-FrontEnd/ ./
RUN npm run build

FROM node:18-bullseye
WORKDIR /app
COPY vendor/GoDataSource-API/package*.json ./
RUN npm ci --omit=dev --legacy-peer-deps
COPY vendor/GoDataSource-API/ ./
COPY --from=frontend /src/dist ./client/dist
COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/"host": "127.0.0.1"/"host": "mongo"/; s/"port": 27000/"port": 27017/; s/"user": "root"/"user": ""/' server/datasources.json \
 && chmod +x /entrypoint.sh
EXPOSE 3000
ENTRYPOINT ["/entrypoint.sh"]
