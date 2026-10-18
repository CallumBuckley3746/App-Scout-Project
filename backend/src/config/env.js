import 'dotenv/config'; // Loads variables from .env

export const config = {
  port: process.env.PORT || 3000,
  env: process.env.NODE_ENV || 'development'
};