FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY server.js ./
COPY src ./src
COPY public ./public
COPY supabase ./supabase
# البيانات متخزنة على Supabase، فمش محتاج Volume
EXPOSE 3000
CMD ["node", "server.js"]
