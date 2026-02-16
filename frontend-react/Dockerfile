# Build stage
FROM node:20-alpine as build

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy source and build
COPY . .

# Set Node memory limit for large libraries (like plotly.js)
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Run type check and build separately to manage memory
RUN npx tsc -b
RUN npx vite build

# Production stage
FROM nginx:stable-alpine

# Copy build output to nginx public folder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config if needed (optional)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
