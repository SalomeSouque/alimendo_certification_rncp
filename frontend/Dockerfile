# 1. build du bundle
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Variables VITE_* figées dans le bundle au moment du build.
ARG VITE_API_URL=http://localhost:8000
ARG VITE_AUTH_MOCK=false
ENV VITE_API_URL=$VITE_API_URL VITE_AUTH_MOCK=$VITE_AUTH_MOCK
RUN npm run build          
# Vite sort dans /app/dist

# 2. service des fichiers statiques
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]