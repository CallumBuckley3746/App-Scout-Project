FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# The --host flag ensures Vite accepts incoming connections outside the container
CMD ["npm", "run", "dev", "--", "--host"]
