# Build stage
FROM node:16-alpine as builder

WORKDIR /app

# Copy package.json and install dependencies
COPY package.json .
COPY package-lock.json* .
RUN npm ci

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Final stage
FROM nginx:alpine

# Copy built files from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
