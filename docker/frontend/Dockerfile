# Dev-oriented image: runs the Vite dev server with HMR behind nginx.
# For a real deploy, replace with a build stage (`npm run build`) whose
# static output is served directly by nginx instead of this dev server.
FROM node:22-slim

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
