FROM node:20-alpine

WORKDIR /app

# Copy package files first to optimize Docker layer caching
COPY package*.json ./
RUN npm install

# Copy the rest of the application files
COPY . .

EXPOSE 3000

CMD ["npm", "start"]
