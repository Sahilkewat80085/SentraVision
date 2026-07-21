# Use specific, lightweight Alpine base image for Node
FROM node:20-alpine

# Set node production or build environments
ENV NODE_ENV=development

WORKDIR /app

# Install dependencies separately to leverage Docker layer caching
COPY package.json package-lock.json* ./
RUN npm install --frozen-lockfile || npm install

# Copy application configuration and components
COPY . .

EXPOSE 5173

# Run the dev server with host exposure
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

