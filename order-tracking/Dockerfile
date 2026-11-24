FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY server.js ./
COPY src ./src
COPY public ./public
# قاعدة البيانات بتتحفظ هنا — اربطه بـ Volume عشان البيانات ماتضيعش
ENV DB_FILE=/data/orders.db
VOLUME ["/data"]
EXPOSE 3000
CMD ["node", "server.js"]
